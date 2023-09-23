import sublime
import sublime_plugin

from collections import Counter
import pathlib
import re
import typing

from . import _common as common
from . import timing

validationStatusKey: str = "marlant_validation_status"
validationError: typing.Final[str] = "Validation error:"


def failedValidation(
    view: sublime.View,
    lineNumber: typing.Optional[int],
    errorMsg: str
) -> None:
    view.set_status(validationStatusKey, "SubRip: FAILING")
    if lineNumber is not None:
        common.scrollToProblematicLineNumber(view, lineNumber)
    sublime.error_message(errorMsg)


def checkForUnmatchedHtmlTags(
    openHtmlTags: typing.List[str],
    closeHtmlTags: typing.List[str]
) -> typing.Tuple[typing.List[str], typing.List[str]]:
    unmatchedOpenTags: typing.List[str] = []
    unmatchedCloseTags: typing.List[str] = []
    # print(f"Collected open tags: {openHtmlTags}")
    # print(f"Collected closing tags: {closeHtmlTags}")
    if len(openHtmlTags) > 0:
        unmatchedOpenTags = list(
            Counter(openHtmlTags) - Counter(closeHtmlTags)
        )
        # if len(unmatchedOpenTags.keys()) > 0:
        #     print(f"Unmatched open tags: {','.join(unmatchedOpenTags.keys())}")
    if len(closeHtmlTags) > 0:
        unmatchedCloseTags = list(
            Counter(closeHtmlTags) - Counter(openHtmlTags)
        )
        # if len(unmatchedCloseTags.keys()) > 0:
        #     print(f"Unmatched close tags: {','.join(unmatchedCloseTags.keys())}")
    return (unmatchedOpenTags, unmatchedCloseTags)


# some more about SubRip validation: https://ale5000.altervista.org/subtitles.htm
class MarlantValidateAllTitlesCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        activeView = self.window.active_view()
        activeView.erase_status(validationStatusKey)

        # try to get project settings
        projectSettings: sublime.Value = None
        currentFileName: str = pathlib.Path(activeView.file_name()).name
        excludedTitles: typing.List[int] = []
        if self.window.project_file_name():
            projectSettings = self.window.project_data().get("settings")
        if projectSettings:
            excludedTitles = projectSettings.get(
                "marlant", {}
            ).get(
                "validation", {}
            ).get(
                "excluded-titles", {}
            ).get(
                currentFileName, []
            )

        maxTitleLineLength: int = common.marlantSettings.get(
            "maximum_title_text_line_length",
            common.maxTitleLineLengthFallback
        )
        maxTitleLines: int = common.marlantSettings.get(
            "maximum_title_text_lines",
            common.maxTitleLinesFallback
        )
        minTitleDuration: int = common.marlantSettings.get(
            "minimum_title_duration",
            common.minTitleDurationFallback
        )
        maxTitleDuration: int = common.marlantSettings.get(
            "maximum_title_duration",
            common.maxTitleDurationFallback
        )
        htmlTagsToWatchFor: typing.List[str] = common.marlantSettings.get(
            "html_tags_to_watch_for",
            common.htmlTagsToWatchForFallback
        )
        try:
            if not isinstance(htmlTagsToWatchFor, list):
                raise TypeError("Tags need to be a list of strings")
            htmlTagsToWatchForJoined = "|".join(htmlTagsToWatchFor)
        except TypeError as ex:
            print(f"MarLant | ERROR | Wrong tags format: {ex}")
            sublime.error_message(
                " ".join((
                    "Looks like you've set the list of tags incorrectly,",
                    "check your plugin settings. If you have just installed",
                    "the plugin, then restarting Sublime Text might help."
                ))
            )
            return

        # this regular expression is very naive, as it will also find
        # <underestimated>, <incredibly>, <beautiful>, <fontange> tags,
        # not just <u>, <i>, <b>, <font>
        regexHTMLtagOpen: typing.Final[typing.Pattern] = re.compile(
            f"(<({htmlTagsToWatchForJoined})[^>]*>)"
        )
        # this one is quite okay though
        regexHTMLtagClose: typing.Final[typing.Pattern] = re.compile(
            f"(<\\/({htmlTagsToWatchForJoined})>)"
        )

        bufferLinesRegions: typing.List[sublime.Region] = (
            activeView.split_by_newlines(
                sublime.Region(0, activeView.size())
            )
        )
        # there must be at least 3 lines: ordinal, timing and a line of text
        if len(bufferLinesRegions) < 3:
            failedValidation(
                activeView,
                None,
                " ".join((
                    f"{validationError} there are no SubRip titles. At least",
                    "there should be an ordinal, timing and a line of text."
                ))
            )
            return
        if activeView.substr(activeView.size()-1) != "\n":
            failedValidation(
                activeView,
                None,
                " ".join((
                    f"{validationError} there should",
                    "be an empty line in the end of file."
                ))
            )
            return
        if len(activeView.substr(bufferLinesRegions[-1])) == 0:
            failedValidation(
                activeView,
                len(bufferLinesRegions),
                " ".join((
                    f"{validationError} there is a redundant",
                    "empty line in the end of file."
                ))
            )
            return

        hadEmptyLine: bool = False
        crntTitleStrNumber: int = 0
        crntTitleCnt: int = 0
        previousTitleTimeEnd: int = 0
        openHtmlTags: typing.List[str] = []
        closeHtmlTags: typing.List[str] = []
        for index, region in enumerate(bufferLinesRegions):
            line = activeView.substr(region)
            if not line:
                if hadEmptyLine or index == 0:
                    failedValidation(
                        activeView,
                        index,
                        " ".join((
                            f"{validationError} the line {index+1}",
                            "should not be empty."
                        ))
                    )
                    return
                else:
                    if crntTitleStrNumber == 2:
                        failedValidation(
                            activeView,
                            index,
                            " ".join((
                                f"{validationError} the line {index+1}",
                                "should not be empty."
                            ))
                        )
                        return
                    else:  # new title starts
                        # check if there are problems with HTML tags collected
                        # in the previous title
                        uot, uct = checkForUnmatchedHtmlTags(openHtmlTags, closeHtmlTags)
                        if len(uot) > 0:
                            failedValidation(
                                activeView,
                                index - 1,
                                " ".join((
                                    f"{validationError} this title has",
                                    "unmatched open HTML tags:",
                                    f"{', '.join(uot)}."
                                ))
                            )
                            return
                        if len(uct) > 0:
                            failedValidation(
                                activeView,
                                index - 1,
                                " ".join((
                                    f"{validationError} this title has",
                                    "unmatched closing HTML tags:",
                                    f"{', '.join(uct)}."
                                ))
                            )
                            return

                        # reset everything
                        openHtmlTags = []
                        closeHtmlTags = []
                        crntTitleStrNumber = 0
                        hadEmptyLine = True
                        continue

            hadEmptyLine = False
            crntTitleStrNumber += 1

            if line.endswith(" "):
                failedValidation(
                    activeView,
                    index,
                    " ".join((
                        f"{validationError} there is a trailing whitespace",
                        f"on the line {index+1}."
                    ))
                )
                return
            if line.startswith(" "):
                failedValidation(
                    activeView,
                    index,
                    " ".join((
                        f"{validationError} the line {index+1}",
                        "starts with a whitespace."
                    ))
                )
                return

            # --- ordinal line

            if crntTitleStrNumber == 1:
                if common.regexSrtNumber.fullmatch(line) is not None:
                    crntTitleCntCandidate = int(line)
                    if crntTitleCntCandidate - crntTitleCnt != 1:
                        failedValidation(
                            activeView,
                            index,
                            " ".join((
                                f"{validationError} the title number",
                                f"on the line {index+1}",
                                f"({crntTitleCntCandidate}) is not",
                                "a +1 increment of the previous",
                                f"title number ({crntTitleCnt})."
                            ))
                        )
                        return
                    else:
                        crntTitleCnt = crntTitleCntCandidate
                        continue
                else:
                    failedValidation(
                        activeView,
                        index,
                        " ".join((
                            f"{validationError} the line {index+1}",
                            "should contain a title number."
                        ))
                    )
                    return

            # --- checking for excluded titles

            # validation checks after this point are ignorable (more or less),
            # so they can be skipped, if translator/editor wants to exclude them
            if crntTitleCnt in excludedTitles:
                if crntTitleStrNumber == 2:  # don't repeat the warning
                    print(
                        " ".join((
                            f"[WARNING] Title #{crntTitleCnt}",
                            "is in the ignore list, so it will not",
                            "go through all the checks"
                        ))
                    )
                continue

            # --- timing line

            if crntTitleStrNumber == 2:
                if common.regexSrtTiming.fullmatch(line) is not None:
                    timingMatches = common.regexSrtTiming.match(line)
                    # print(timingMatches.group(0)) # full timing
                    # print(timingMatches.group(1)) # start time
                    # print(timingMatches.group(2)) # separator
                    # print(timingMatches.group(3)) # end time
                    if timingMatches is None:
                        failedValidation(
                            activeView,
                            index,
                            " ".join((
                                f"{validationError} the title timing",
                                f"on the line {index+1} has a wrong format."
                            ))
                        )
                        return
                    timeStart: int = timing.timeCodeToMilliseconds(
                        timingMatches.group(1)
                    )
                    timeEnd: int = timing.timeCodeToMilliseconds(
                        timingMatches.group(3)
                    )
                    # start timecode should not be "later" than end timecode
                    if timeStart > timeEnd:
                        failedValidation(
                            activeView,
                            index,
                            " ".join((
                                f"{validationError} the start time",
                                f"of the title on the line {index+1}",
                                "is bigger than its end time."
                            ))
                        )
                        return
                    # title time duration should not be too short
                    if timeEnd - timeStart < minTitleDuration:
                        failedValidation(
                            activeView,
                            index,
                            " ".join((
                                f"{validationError} duration of the title",
                                f"on the line {index+1} is too short",
                                f"(less than {minTitleDuration} milliseconds)."
                            ))
                        )
                        return
                    # title time duration should not be too long
                    if timeEnd - timeStart > maxTitleDuration:
                        failedValidation(
                            activeView,
                            index,
                            " ".join((
                                f"{validationError} duration of the title",
                                f"on the line {index+1} is too long",
                                f"(more than {maxTitleDuration} milliseconds)."
                            ))
                        )
                        return
                    # timing should not overlap with the previous one
                    if crntTitleCnt > 1 and timeStart <= previousTitleTimeEnd:
                        failedValidation(
                            activeView,
                            index,
                            " ".join((
                                f"{validationError} the title",
                                f"on the line {index+1} starts before",
                                f"the previous one ends."
                            ))
                        )
                        return
                    # timing is good
                    previousTitleTimeEnd = timeEnd
                    continue
                else:
                    failedValidation(
                        activeView,
                        index,
                        " ".join((
                            f"{validationError} there",
                            "should be a correct timing string",
                            f"on the line {index+1}."
                        ))
                    )
                    return

            # --- title text lines

            # possible HTML tags
            thisLineTagsLength = 0
            openTagsMatches = regexHTMLtagOpen.findall(line)
            closeTagsMatches = regexHTMLtagClose.findall(line)
            if len(openTagsMatches) > 0:
                for m in openTagsMatches:
                    thisLineTagsLength += len(m[0])
                    openHtmlTags.append(f"<{m[1]}>")
                    # print(f"Found open tag: {m[1]}, full length: {len(m[0])}")
            if len(closeTagsMatches) > 0:
                for m in closeTagsMatches:
                    thisLineTagsLength += len(m[0])
                    closeHtmlTags.append(f"<{m[1]}>")
                    # print(f"Found closing tag: {m[1]}, full length: {len(m[0])}")

            if crntTitleStrNumber > 2 + maxTitleLines:
                failedValidation(
                    activeView,
                    index,
                    " ".join((
                        f"{validationError} this title has too many",
                        f"text lines (more than {maxTitleLines}).",
                        "It may be obstructing the view."
                    ))
                )
                return
            if (len(line) - thisLineTagsLength > maxTitleLineLength):
                failedValidation(
                    activeView,
                    index,
                    " ".join((
                        f"{validationError} the line {index+1}",
                        f"is longer than {maxTitleLineLength} characters.",
                        f"Longer lines are harder to read."
                    ))
                )
                return
            if common.regexSrtTiming.fullmatch(line) is not None:
                failedValidation(
                    activeView,
                    index,
                    " ".join((
                        f"{validationError} there is a timing string",
                        f"on the line {index+1}. Most likely there is",
                        f"a missing empty line on one of the previous lines."
                    ))
                )
                return

        # --- done iterating through the title text lines

        if crntTitleStrNumber < 3:
            failedValidation(
                activeView,
                len(bufferLinesRegions),
                " ".join((
                    f"{validationError} the last title",
                    f"doesn't have any text lines."
                ))
            )
            return

        # check if there are problems with HTML tags collected
        # in the last title. Sadly, this needs to be done here too,
        # as doing that only at the new title beginning will miss
        # the last title
        uot, uct = checkForUnmatchedHtmlTags(openHtmlTags, closeHtmlTags)
        if len(uot) > 0:
            failedValidation(
                activeView,
                len(bufferLinesRegions) - 1,
                " ".join((
                    f"{validationError} last title has",
                    f"unmatched open HTML tags: {', '.join(uot)}."
                ))
            )
            return
        if len(uct) > 0:
            failedValidation(
                activeView,
                len(bufferLinesRegions) - 1,
                " ".join((
                    f"{validationError} last title has",
                    f"unmatched closing HTML tags: {', '.join(uct)}."
                ))
            )
            return

        activeView.set_status(validationStatusKey, "SubRip: OK")
        validationSuccess = "".join((
            "All good! No problems found."  # ...found, ",
            # "checked {crntTitleCnt} titles."
        ))
        if any(excludedTitles):
            validationSuccess += " ".join((
                f"\n\nBut do remember that you have {len(excludedTitles)}",
                "excluded titles in project preferences."
            ))
        sublime.message_dialog(validationSuccess)

    def is_enabled(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")


class MarlantExcludeTitleFromValidationsCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        if not self.window.project_file_name():
            sublime.error_message(
                " ".join((
                    "You need to have a Sublime Text project file",
                    "for this functionality to work."
                ))
            )
            return

        activeView = self.window.active_view()
        currentFileName: str = pathlib.Path(activeView.file_name()).name

        # TODO: move this to a generalized common functions
        # ensure that settings tree structure is in place
        projectData = self.window.project_data()
        if projectData:
            if not projectData.get("settings"):
                projectData["settings"] = {}
            if not projectData["settings"].get("marlant"):
                projectData["settings"]["marlant"] = {}
            if not projectData["settings"]["marlant"].get("validation"):
                projectData["settings"]["marlant"]["validation"] = {}
            if not projectData["settings"]["marlant"]["validation"].get(
                "excluded-titles"
            ):
                projectData["settings"]["marlant"]["validation"][
                    "excluded-titles"
                ] = {}
            if not projectData["settings"]["marlant"]["validation"][
                "excluded-titles"
            ].get(
                currentFileName
            ):
                projectData["settings"]["marlant"]["validation"][
                    "excluded-titles"
                ][currentFileName] = []
        else:
            sublime.error_message(
                " ".join((
                    "Couldn't get project data, check if you have",
                    "any content in your current Sublime Text project file."
                ))
            )
            return

        currentSelection = activeView.sel()
        currentTitlePoint: sublime.Selection = currentSelection[0].b

        if len(
            activeView.substr(
                activeView.line(currentTitlePoint)
            ).strip()
        ) == 0:
            sublime.error_message(
                " ".join((
                    "The cursor is on an empty line,",
                    "can't guess the current title."
                ))
            )
            return

        emptyLineBefore: int = activeView.find_by_class(
            currentTitlePoint,
            False,
            sublime.CLASS_EMPTY_LINE
        )
        emptyLineAfter: int = activeView.find_by_class(
            currentTitlePoint,
            True,
            sublime.CLASS_EMPTY_LINE
        )

        currentTitleRegion: sublime.Region = sublime.Region(
            emptyLineBefore if emptyLineBefore == 0 else emptyLineBefore + 1,
            emptyLineAfter - 1
        )

        titleOrdinal: int = 0
        titleTiming: str = ""
        titleTextRegions: typing.List[sublime.Region] = []
        try:
            titleOrdinal, titleTiming, titleTextRegions = (
                common.parseTitleString(
                    activeView,
                    activeView.split_by_newlines(currentTitleRegion)
                )
            )
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        excludedTitles: typing.List[int] = projectData.get(
            "settings", {}
        ).get(
            "marlant", {}
        ).get(
            "validation", {}
        ).get(
            "excluded-titles", {}
        ).get(
            currentFileName, []
        )
        if titleOrdinal not in excludedTitles:
            excludedTitles.append(titleOrdinal)
            projectData["settings"][
                "marlant"
            ][
                "validation"
            ]["excluded-titles"][currentFileName] = excludedTitles
            self.window.set_project_data(projectData)
        else:
            print(
                " ".join((
                    f"The title #{titleOrdinal} has been",
                    "already excluded earlier"
                ))
            )

    def is_enabled(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")


class MarlantClearExcludedTitlesList(sublime_plugin.WindowCommand):
    def run(self) -> None:
        if not self.window.project_file_name():
            sublime.error_message(
                " ".join((
                    "You need to have a Sublime Text project file",
                    "for this functionality to work."
                ))
            )
            return

        activeView = self.window.active_view()
        currentFileName: str = pathlib.Path(activeView.file_name()).name

        projectData = self.window.project_data()
        if not projectData:
            sublime.error_message(
                " ".join((
                    "Couldn't get project data, check if you have",
                    "any content in your current Sublime Text project file."
                ))
            )
            return

        msg: str = ""

        excludedTitles: typing.List[int] = projectData.get(
            "settings", {}
        ).get(
            "marlant", {}
        ).get(
            "validation", {}
        ).get(
            "excluded-titles", {}
        ).get(
            currentFileName, []
        )
        if any(excludedTitles):
            print(
                " ".join((
                    "The list of excluded titles before clearing:",
                    f"{excludedTitles}"
                ))
            )
            projectData["settings"][
                "marlant"
            ][
                "validation"
            ]["excluded-titles"][currentFileName] = []
            self.window.set_project_data(projectData)
            msg = "The list of excluded tiles has been cleared."
        else:
            msg = " ".join((
                "The list of excluded tiles is already empty,",
                "nothing to clear."
            ))

        sublime.message_dialog(msg)

    def is_enabled(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")
