import sublime
import sublime_plugin

import pathlib
import re
import typing

from . import _common as common
from . import timing


class MarlantRenumberTitlesCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit) -> None:
        # if there is a list of excluded titles, clear it,
        # as it will likely get incorrect/obsolete after renumbering
        clearedExcludedTitles: bool = False
        currentFileName: str = pathlib.Path(
            self.view.window().active_view().file_name()
        ).name
        if self.view.window().project_file_name():
            projectData = self.view.window().project_data()
            if projectData:
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
                    self.view.window().set_project_data(projectData)
                    clearedExcludedTitles = True

        bufferLinesRegions: typing.List[sublime.Region] = (
            self.view.split_by_newlines(
                sublime.Region(0, self.view.size())
            )
        )
        hadEmptyLine: bool = False
        crntTitleStrNumber: int = 0
        crntTitleCnt: int = 1
        replacementBufferAdjustment: int = 0
        for index, region in enumerate(bufferLinesRegions):
            region = sublime.Region(
                region.a - replacementBufferAdjustment,
                region.b - replacementBufferAdjustment
            )
            line = self.view.substr(region).strip()
            if not line:
                if hadEmptyLine or index == 0:
                    sublime.error_message(
                        " ".join((
                            f"{common.wrongFormatError} the line {index+1}",
                            "should not be empty."
                        ))
                    )
                    common.scrollToProblematicLine(self.view, region)
                    return
                else:
                    crntTitleStrNumber = 0
                    hadEmptyLine = True
                    continue

            hadEmptyLine = False
            crntTitleStrNumber += 1

            if crntTitleStrNumber == 1:
                if common.regexSrtNumber.fullmatch(line) is not None:
                    crntTitleCntStr: str = str(crntTitleCnt)
                    self.view.replace(edit, region, crntTitleCntStr)
                    crntTitleCnt += 1
                    replacementBufferAdjustment += (
                        len(line) - len(crntTitleCntStr)
                    )
                    continue
                else:
                    sublime.error_message(
                        " ".join((
                            f"{common.wrongFormatError} the line {index+1}",
                            "should contain a non-zero title number."
                        ))
                    )
                    common.scrollToProblematicLine(self.view, region)
                    return
        if clearedExcludedTitles:
            sublime.message_dialog(
                " ".join((
                    "Note that renumbering the titles caused clearing",
                    "the list of excluded titles.\n\nThis is not an error,",
                    "just letting you know, so you don't forget about it.",
                    "You can find the cleared values in the console."
                ))
            )

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")


class AfterCurrentTitleInputHandler(sublime_plugin.ListInputHandler):
    def placeholder(self) -> str:
        return "direction"

    def initial_text(self) -> str:
        return "after"

    def list_items(self) -> typing.List[typing.Tuple[str, bool]]:
        return [
            ("after", True),
            ("before", False)
        ]


class MarlantInsertNewTitleCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit, after_current_title: bool) -> None:
        titlePlaceholder = common.marlantSettings.get(
            "title_placeholder",
            common.titlePlaceholderFallback
        )

        currentSelection = self.view.sel()
        currentTitlePoint: sublime.Selection = currentSelection[0].b

        if len(
            self.view.substr(
                self.view.line(currentTitlePoint)
            ).strip()
        ) == 0:
            sublime.error_message(
                " ".join((
                    "The cursor is on an empty line,",
                    "can't guess the current title."
                ))
            )
            return

        emptyLineBefore: int = self.view.find_by_class(
            currentTitlePoint,
            False,
            sublime.CLASS_EMPTY_LINE
        )
        emptyLineAfter: int = self.view.find_by_class(
            currentTitlePoint,
            True,
            sublime.CLASS_EMPTY_LINE
        )

        currentTitleRegion: sublime.Region = sublime.Region(
            emptyLineBefore if emptyLineBefore == 0 else emptyLineBefore + 1,
            emptyLineAfter - 1
        )
        # currentSelection.clear()
        # currentSelection.add(currentTitleRegion)

        titleOrdinal: int = 0
        titleTiming: str = ""
        try:
            titleOrdinal, titleTiming = common.parseTitleString(
                self.view,
                self.view.split_by_newlines(currentTitleRegion)
            )[:2]
            # print(f"Title ordinal: {titleOrdinal}, timing: {titleTiming}")
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        newTitleOrdinal: int = (
            titleOrdinal + 1 if after_current_title
            else titleOrdinal - 1
        )
        if newTitleOrdinal == 0:
            newTitleOrdinal = 1

        newTitleTiming: str = "00:00:00,000 --> 00:00:00,000"
        timingMatches = common.regexSrtTiming.match(titleTiming)
        # print(timingMatches.group(0)) # full timing
        # print(timingMatches.group(1)) # start time
        # print(timingMatches.group(2)) # separator
        # print(timingMatches.group(3)) # end time
        if timingMatches is None:
            sublime.error_message("The title timing has a wrong format.")
            return
        timeCodeMS: int = 0
        newTimeCodeMS_start: int = 0
        newTimeCodeMS_end: int = 0
        try:
            timeCodeMS = timing.timeCodeToMilliseconds(
                timingMatches.group(3) if after_current_title
                else timingMatches.group(1)
            )
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        if after_current_title:
            newTimeCodeMS_start = timeCodeMS + 1
            newTimeCodeMS_end = timeCodeMS + 1001
        else:
            if timeCodeMS - 1001 < 0:
                newTimeCodeMS_start = 0
                newTimeCodeMS_end = 1000
            else:
                newTimeCodeMS_start = timeCodeMS - 1001
                newTimeCodeMS_end = timeCodeMS - 1
        newTitleTiming = " ".join((
            f"{timing.millisecondsToTimeCode(newTimeCodeMS_start)}",
            "-->",
            f"{timing.millisecondsToTimeCode(newTimeCodeMS_end)}"
        ))

        lineNewTitleNumber: str = "\n"
        lineNewTitleLast: str = ""
        if not after_current_title:
            lineNewTitleNumber = "\n" if emptyLineBefore != 0 else ""
            lineNewTitleLast = "\n" if emptyLineBefore == 0 else ""

        newTitle: str = "".join((
            lineNewTitleNumber,
            f"{newTitleOrdinal}\n",
            f"{newTitleTiming}\n",
            f"{titlePlaceholder}\n",
            lineNewTitleLast
        ))
        insertedCharsCount: int = self.view.insert(
            edit,
            emptyLineAfter if after_current_title else emptyLineBefore,
            newTitle
        )

        currentSelection.clear()
        currentSelection.add(
            sublime.Region(
                emptyLineAfter + 1 if after_current_title
                else (
                    emptyLineBefore + 1
                    if emptyLineBefore != 0
                    else emptyLineBefore
                ),
                emptyLineAfter + insertedCharsCount - 1
                if after_current_title
                else (
                    emptyLineBefore + insertedCharsCount - 1
                    if emptyLineBefore != 0
                    else emptyLineBefore + insertedCharsCount - 2
                )
            )
        )

        self.view.run_command("marlant_renumber_titles")

    def input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "after_current_title" not in args:
            return AfterCurrentTitleInputHandler()

    def input_description(self) -> str:
        return "Where"

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")


class MarlantSplitTitleCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit) -> None:
        currentSelection = self.view.sel()
        currentTitlePoint: sublime.Selection = currentSelection[0].b

        if len(
            self.view.substr(
                self.view.line(currentTitlePoint)
            ).strip()
        ) == 0:
            sublime.error_message(
                " ".join((
                    "The cursor is on an empty line,",
                    "can't guess the current title."
                ))
            )
            return

        emptyLineBefore: int = self.view.find_by_class(
            currentTitlePoint,
            False,
            sublime.CLASS_EMPTY_LINE
        )
        emptyLineAfter: int = self.view.find_by_class(
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
                    self.view,
                    self.view.split_by_newlines(currentTitleRegion)
                )
            )
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        titleTextFirst: str = ""
        titleTextSecond: str = ""
        firstString = self.view.substr(titleTextRegions[0]).strip()
        if len(titleTextRegions) > 1:
            titleTextFirst = firstString
            titleTexts: typing.List[str] = []
            for rgn in titleTextRegions[1:]:
                titleTexts.append(self.view.substr(rgn).strip())
            titleTextSecond = "\n".join(titleTexts)
            if titleTextSecond.startswith("-"):
                titleTextSecond = re.sub(
                    r"^-\s*",
                    "",
                    titleTextSecond
                )
        else:
            titleTextFirst, titleTextSecond = common.splitStringInTwo(firstString)
        if titleTextFirst.startswith("-"):
            titleTextFirst = re.sub(
                r"^-\s*",
                "",
                titleTextFirst
            )

        titleTimingFirst: str = titleTiming
        titleTimingSecond: str = titleTiming
        try:
            titleTimingFirst, titleTimingSecond = timing.splitTimingInTwo(titleTiming)
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        self.view.replace(
            edit,
            currentTitleRegion,
            "\n".join((
                str(titleOrdinal),
                titleTimingFirst,
                titleTextFirst,
                "",
                str(titleOrdinal),
                titleTimingSecond,
                titleTextSecond
            ))
        )

        self.view.run_command("marlant_renumber_titles")

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")


class MarlantJoinTitlesCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit, after_current_title: bool) -> None:
        currentSelection = self.view.sel()
        currentTitlePoint: sublime.Selection = currentSelection[0].b

        maxTitleLineLength: int = common.marlantSettings.get(
            "maximum_title_text_line_length",
            common.maxTitleLineLengthFallback
        )

        if len(
            self.view.substr(
                self.view.line(currentTitlePoint)
            ).strip()
        ) == 0:
            sublime.error_message(
                " ".join((
                    "The cursor is on an empty line,",
                    "can't guess the current title."
                ))
            )
            return

        emptyLineBefore: int = self.view.find_by_class(
            currentTitlePoint,
            False,
            sublime.CLASS_EMPTY_LINE
        )
        emptyLineAfter: int = self.view.find_by_class(
            currentTitlePoint,
            True,
            sublime.CLASS_EMPTY_LINE
        )

        if emptyLineBefore == 0 and after_current_title is False:
            sublime.error_message(
                " ".join((
                    "This is the first title,",
                    "there is nothing before it to join with."
                ))
            )
            return

        # there might be several empty lines in the end of the file,
        # and as timing string is 30 symbols, there has to be at least
        # that many symbols for a potential title to fit there
        # ---
        # it would be easier if self.view.size() was not counting
        # trailing empty lines in the end of the file
        if (
            emptyLineAfter >= self.view.size() - 30
            and after_current_title is True
        ):
            sublime.error_message(
                " ".join((
                    "This is the last title,",
                    "there is nothing after it to join with."
                ))
            )
            return

        currentTitleRegion: sublime.Region = sublime.Region(
            emptyLineBefore if emptyLineBefore == 0 else emptyLineBefore + 1,
            emptyLineAfter - 1
        )

        firstTitleOrdinal: int = 0
        firstTitleTiming: str = ""
        firstTitleTextRegions: typing.List[sublime.Region] = []
        try:
            firstTitleOrdinal, firstTitleTiming, firstTitleTextRegions = (
                common.parseTitleString(
                    self.view,
                    self.view.split_by_newlines(currentTitleRegion)
                )
            )
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        secondTitleEmptyLine: int = self.view.find_by_class(
            (
                currentTitleRegion.b + 1
                if after_current_title
                else currentTitleRegion.a - 1
            ),
            after_current_title,
            sublime.CLASS_EMPTY_LINE
        )

        secondTitleRegion: sublime.Region = sublime.Region(0, 0)
        if after_current_title:
            secondTitleRegion = sublime.Region(
                currentTitleRegion.b + 2,
                secondTitleEmptyLine if secondTitleEmptyLine == self.view.size()
                else secondTitleEmptyLine - 1
            )
        else:
            secondTitleRegion = sublime.Region(
                secondTitleEmptyLine + 1,
                currentTitleRegion.a - 2
            )

        secondTitleOrdinal: int = 0
        secondTitleTiming: str = ""
        secondTitleTextRegions: typing.List[sublime.Region] = []
        try:
            secondTitleOrdinal, secondTitleTiming, secondTitleTextRegions = (
                common.parseTitleString(
                    self.view,
                    self.view.split_by_newlines(
                        sublime.Region(
                            secondTitleRegion.a - 1, secondTitleRegion.b
                        )
                        if secondTitleEmptyLine == 0 else secondTitleRegion
                    )
                )
            )
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        joinedTitleRegions: typing.List[sublime.Region] = (
            firstTitleTextRegions + secondTitleTextRegions
            if after_current_title
            else secondTitleTextRegions + firstTitleTextRegions
        )
        joinedTitleTexts: typing.List[str] = []
        joinedTitleTextLength: int = 0
        for rgn in joinedTitleRegions:
            joinedTitleTexts.append(self.view.substr(rgn).strip())
            joinedTitleTextLength += rgn.size()
        # if both titles total text length is less than the allowed maximum,
        # join them into one line
        joinedTitleText: str = (
            "\n".join(joinedTitleTexts)
            if joinedTitleTextLength > maxTitleLineLength
            else " ".join(joinedTitleTexts)
        )

        joinedTitleTiming: str = (
            firstTitleTiming if after_current_title
            else secondTitleTiming
        )
        try:
            joinedTitleTiming = timing.joinTimings(firstTitleTiming, secondTitleTiming)
        except ValueError as ex:
            sublime.error_message(str(ex))
            return

        self.view.erase(
            edit,
            (
                sublime.Region(secondTitleRegion.a, secondTitleRegion.b + 2)
                if after_current_title
                else sublime.Region(secondTitleRegion.a, secondTitleRegion.b)
            )
        )

        self.view.replace(
            edit,
            (
                currentTitleRegion if after_current_title
                else sublime.Region(
                    currentTitleRegion.a - secondTitleRegion.size() - 2,
                    currentTitleRegion.b - secondTitleRegion.size()
                )
            ),
            "\n".join((
                str(firstTitleOrdinal),
                joinedTitleTiming,
                joinedTitleText
            ))
        )

        self.view.run_command("marlant_renumber_titles")

    def input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "after_current_title" not in args:
            return AfterCurrentTitleInputHandler()

    def input_description(self) -> str:
        return "With the one"

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")
