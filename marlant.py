import sublime
import sublime_plugin

# import functools
import pathlib
import re

import typing

# when user changes settings, they won't be picked up on plugin_loaded(),
# so this here should also call load_settings()
marlantSettings: sublime.Settings = sublime.load_settings(
    "marlant.sublime-settings"
)
maxTitleLineLengthFallback: int = 41
maxTitleLinesFallback = 3
minTitleDurationFallback: int = 500
maxTitleDurationFallback: int = 6000

validationStatusKey: str = "marlant_validation_status"
validationError: typing.Final[str] = "Validation error:"
wrongFormatError: typing.Final[str] = " ".join((
    "The SubRip content seems to have",
    "a wrong format, because"
))
wrongTitleFormatError: typing.Final[str] = " ".join((
    "Current title seems to have",
    "incorrect format, because"
))
titlePlaceholder: typing.Final[str] = "[ ... ]"

regexLanguageCode: typing.Final[typing.Pattern] = re.compile(r"^[A-Za-z]+$")
regexSrtNumber: typing.Final[typing.Pattern] = re.compile(r"^[1-9]{1}\d*$")
# regexSrtTimingString = # r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$"
regexSrtTimingString = r"^(\d{2}:\d{2}:\d{2},\d{3}) (-->) (\d{2}:\d{2}:\d{2},\d{3})$"
regexSrtTiming: typing.Final[typing.Pattern] = re.compile(regexSrtTimingString)
regexSrtTimeCode: typing.Final[typing.Pattern] = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}$"
)


def plugin_loaded() -> None:
    # print("MarLant plugin has loaded")
    # when Sublime Text just started, plugins path is unknown,
    # and so settings need to be loaded after the plugin is loaded
    marlantSettings = sublime.load_settings(
        "marlant.sublime-settings"
    )
    pass


def plugin_unloaded() -> None:
    # print("MarLant plugin has unloaded")
    pass


def scrollToProblematicLine(
    view: sublime.View,
    region: sublime.Region
) -> None:
    lineSelection = view.sel()
    lineSelection.clear()
    lineSelection.add(region)
    view.show(region)


def scrollToProblematicLineNumber(
    view: sublime.View,
    lineNumber: int
) -> None:
    pnt: int = view.text_point(lineNumber, 0)
    lineRegion: sublime.Region = view.line(pnt)
    scrollToProblematicLine(view, lineRegion)

# might be an overkill, it is enough to just check for text.srt selector/scope
# def isItAnSRTfile(fileFromView: str) -> bool:
#     if fileFromView is not None:
#         currentFilePath = pathlib.Path(fileFromView)
#         if currentFilePath.suffix.lower() == ".srt":
#             return True
#     return False


def parseTitleString(
    view: sublime.View,
    titleRegions: typing.List[sublime.Region]
) -> typing.Tuple[int, str, typing.List[sublime.Region]]:
    # for index, region in enumerate(titleRegions):
    #     line = view.substr(region).strip()
    #     print(line)
    if len(titleRegions) < 3:
        raise ValueError(
            " ".join((
                wrongTitleFormatError,
                "it must have at least one line of text",
                "in addition to the ordinal and timing."
            ))
        )
    titleOrdinal = view.substr(titleRegions[0]).strip()
    if regexSrtNumber.fullmatch(titleOrdinal) is None:
        raise ValueError(
            " ".join((
                wrongTitleFormatError,
                "the first line should be a title ordinal."
            ))
        )
    titleTiming = view.substr(titleRegions[1]).strip()
    if regexSrtTiming.fullmatch(titleTiming) is None:
        raise ValueError(
            " ".join((
                wrongTitleFormatError,
                "the second line should be a title timing."
            ))
        )
    return int(titleOrdinal), titleTiming, titleRegions[2:]


def failedValidation(
    view: sublime.View,
    lineNumber: typing.Optional[int],
    errorMsg: str
) -> None:
    view.set_status(validationStatusKey, "SubRip: FAILING")
    if lineNumber is not None:
        scrollToProblematicLineNumber(view, lineNumber)
    sublime.error_message(errorMsg)


def timeCodeToMilliseconds(timeCode: str) -> int:
    if regexSrtTimeCode.fullmatch(timeCode) is None:
        raise ValueError("Timecode has a wrong format.")
    tms = timeCode.split(":")
    hour: int = int(tms[0])
    minute: int = int(tms[1])
    seconds: typing.List[str] = tms[2].split(",")
    second: int = int(seconds[0])
    millisecond: int = int(seconds[1])

    return (
        hour * 60 * 60 * 1000 +
        minute * 60 * 1000 +
        second * 1000 +
        millisecond
    )


def millisecondsToTimeCode(milliseconds: int) -> str:
    timeComponents: typing.Tuple[int, int, int, int] = (
        milliseconds // (60 * 60 * 1000),
        (milliseconds % (60 * 60 * 1000)) // (60 * 1000),
        (milliseconds % (60 * 1000)) // 1000,
        milliseconds % 1000
    )
    return "%02d:%02d:%02d,%03d" % timeComponents


def splitStringInTwo(stringToSplit: str) -> typing.Tuple[str, str]:
    middlePoint: int = len(stringToSplit) // 2
    while (
        stringToSplit[middlePoint] != " "
        and middlePoint != len(stringToSplit) - 1
    ):
        middlePoint += 1
    firstHalf: str = stringToSplit[:middlePoint]
    secondHalf: str = stringToSplit[middlePoint:]
    if len(secondHalf) == 1:
        firstHalf = stringToSplit
        secondHalf = ""
    return (
        firstHalf if firstHalf else titlePlaceholder,
        secondHalf.strip() if secondHalf else titlePlaceholder
    )


def splitTimingInTwo(timingToSplit: str) -> typing.Tuple[str, str]:
    timingMatches = regexSrtTiming.match(timingToSplit)
    # print(timingMatches.group(0)) # full timing
    # print(timingMatches.group(1)) # start time
    # print(timingMatches.group(2)) # separator
    # print(timingMatches.group(3)) # end time
    if timingMatches is None:
        raise ValueError("The title timing has a wrong format.")
    timingStart: int = timeCodeToMilliseconds(timingMatches.group(1))
    timingEnd: int = timeCodeToMilliseconds(timingMatches.group(3))
    timingHalfLength: int = (timingEnd - timingStart) // 2
    endTimeFirst: str = millisecondsToTimeCode(
        timingStart + timingHalfLength
    )
    startTimeSecond: str = millisecondsToTimeCode(
        timingEnd - timingHalfLength + 1
    )
    return (
        f"{timingMatches.group(1)} {timingMatches.group(2)} {endTimeFirst}",
        f"{startTimeSecond} {timingMatches.group(2)} {timingMatches.group(3)}"
    )


def joinTimings(timingStartStr: str, timingEndStr: str) -> str:
    timingStartMatches = regexSrtTiming.match(timingStartStr)
    timingEndMatches = regexSrtTiming.match(timingEndStr)
    # print(timingStartMatches.group(0)) # full timing
    # print(timingStartMatches.group(1)) # start time
    # print(timingStartMatches.group(2)) # separator
    # print(timingStartMatches.group(3)) # end time
    if timingStartMatches is None or timingEndMatches is None:
        raise ValueError("One of the title timings has a wrong format.")
    timingStart: int = timeCodeToMilliseconds(timingStartMatches.group(1))
    timingEnd: int = timeCodeToMilliseconds(timingEndMatches.group(3))
    # if timingEnd < timingStart:
    #     raise ValueError("Second timing cannot be earlier than the first one.")
    return (
        " ".join((
            timingStartMatches.group(1),
            timingStartMatches.group(2),
            timingEndMatches.group(3)
        )) if timingEnd > timingStart
        else
        " ".join((
            timingEndMatches.group(1),
            timingStartMatches.group(2),
            timingStartMatches.group(3)
        ))
    )


def shiftTiming(timingToShift: str, shiftValue: int) -> str:
    timingMatches = regexSrtTiming.match(timingToShift)
    # print(timingMatches.group(0)) # full timing
    # print(timingMatches.group(1)) # start time
    # print(timingMatches.group(2)) # separator
    # print(timingMatches.group(3)) # end time
    if timingMatches is None:
        raise ValueError("The title timing has a wrong format.")
    timingStart: int = timeCodeToMilliseconds(timingMatches.group(1)) + shiftValue
    timingEnd: int = timeCodeToMilliseconds(timingMatches.group(3)) + shiftValue
    return " ".join((
        millisecondsToTimeCode(timingStart),
        timingMatches.group(2),
        millisecondsToTimeCode(timingEnd)
    ))


def openTranslationFile(
    window: sublime.Window,
    originalFile: pathlib.Path,
    # openFiles: typing.List[str],
    selectedFile: str
) -> None:
    if selectedFile:
        if pathlib.Path(selectedFile) == originalFile:
            sublime.error_message(
                " ".join((
                    "You selected the same file",
                    "as the one already opened."
                ))
            )
            return

        # no need, find_open_file() will take care of this
        # if selectedFile in openFiles:
        #     sublime.error_message(
        #         " ".join((
        #             "This file is already",
        #             "opened."
        #         ))
        #     )
        #     return

        crntFileSheet = window.active_sheet()
        crntFileView = window.active_view()
        # print(f"Current sheet: {window.active_sheet()}")
        # print(f"Selected sheets: {window.selected_sheets()}")

        selectedFileSheet = None
        selectedFileView = window.find_open_file(selectedFile)
        if not selectedFileView:  # if this file isn't already open
            try:
                window.open_file(
                    selectedFile
                    # no need, there will be select_sheets() anyway
                    # sublime.ADD_TO_SELECTION
                )
                selectedFileView = window.find_open_file(selectedFile)
            except Exception as ex:
                print(f"error: {ex}")
                sublime.error_message(
                    " ".join((
                        "There was an error trying to open translation file.",
                        "Check console for details."
                    ))
                )
                return
        selectedFileSheet = selectedFileView.sheet()
        # sometimes there could be a transient view between them,
        # sometimes - a sheet, so it's not trivial to have them
        # next to each other (is it view or sheet index you need to use),
        # and so it's easier to just move them both to the end of tabs row
        crntFileSheetGroup, crntFileSheetIndex = window.get_sheet_index(
            crntFileSheet
        )
        window.set_sheet_index(
            crntFileSheet,
            crntFileSheetGroup,
            -1
        )
        # crntFileSheetGroup, crntFileSheetIndex = window.get_view_index(
        #     crntFileSheet
        # )
        window.set_sheet_index(
            selectedFileSheet,
            crntFileSheetGroup,
            -1  # crntFileSheetIndex + 1
        )
        window.select_sheets([crntFileSheet, selectedFileSheet])


class LanguageInputHandler(sublime_plugin.TextInputHandler):
    def name(self) -> str:
        return "language"

    def placeholder(self) -> str:
        return "lang"

    def initial_text(self) -> str:
        return "ru"

    def validate(self, text: str) -> bool:
        if regexLanguageCode.fullmatch(text) is None:
            return False
        else:
            return True

    def preview(self, text: str) -> str:
        if text.strip():
            return sublime.Html(f"some-file-<b>{text}</b>.srt")
        else:
            return sublime.Html(
                "<i>You need to provide a language suffix.</i>"
            )


class MarlantCreateTranslationFileCommand(sublime_plugin.WindowCommand):
    def run(self, language: str) -> None:
        activeView = self.window.active_view()
        originalFileValue: str = activeView.file_name()
        if not originalFileValue:
            sublime.error_message(
                "You can run this command only from an existing file."
            )
            return
        originalFile: pathlib.Path = pathlib.Path(originalFileValue)
        if originalFile.suffix != ".srt":
            sublime.error_message("This is not an .srt file.")
            return

        # there should be no need to check for empty string,
        # because TextInputHandler.validate() takes care of this
        language = language.strip()

        generatedFile: pathlib.Path = pathlib.Path(
            originalFile.parents[0],
            f"{originalFile.stem}-{language}{originalFile.suffix}"
        )

        if generatedFile.is_file():
            userAnswer: bool = sublime.ok_cancel_dialog(
                " ".join((
                    f"The file {generatedFile} already exists.",
                    "Do you want to overwrite it?"
                )),
                "Yes"
            )
            if not userAnswer:
                return

        try:
            with open(
                generatedFile,
                "w",
                encoding="utf-8"
            ) as gf:
                hadEmptyLine: bool = False
                crntTitleStrNumber: int = 0
                crntTitleCnt: int = 0
                bufferLinesRegions: typing.List[sublime.Region] = (
                    activeView.split_by_newlines(
                        sublime.Region(0, activeView.size())
                    )
                )
                for index, region in enumerate(bufferLinesRegions):
                    line = activeView.substr(region).strip()

                    if not line:
                        if hadEmptyLine or index == 0:
                            sublime.error_message(
                                " ".join((
                                    f"{wrongFormatError} the line {index+1}",
                                    "should not be empty."
                                ))
                            )
                            scrollToProblematicLineNumber(activeView, index)
                            return
                        else:
                            crntTitleStrNumber = 0
                            hadEmptyLine = True
                            gf.write("\n")
                            continue

                    hadEmptyLine = False
                    crntTitleStrNumber += 1

                    if crntTitleStrNumber == 1:
                        if regexSrtNumber.fullmatch(line) is not None:
                            crntTitleCntCandidate = int(line)
                            if crntTitleCntCandidate - crntTitleCnt != 1:
                                sublime.error_message(
                                    " ".join((
                                        f"{wrongFormatError} the title number",
                                        f"on the line {index+1}",
                                        f"({crntTitleCntCandidate}) is not",
                                        "a +1 increment of the previous",
                                        f"title number ({crntTitleCnt})."
                                    ))
                                )
                                scrollToProblematicLineNumber(activeView, index)
                                return
                            else:
                                crntTitleCnt = crntTitleCntCandidate
                                gf.write(f"{line}\n")
                                continue
                        else:
                            sublime.error_message(
                                " ".join((
                                    f"{wrongFormatError} the line {index+1}",
                                    "should contain a title number."
                                ))
                            )
                            scrollToProblematicLineNumber(activeView, index)
                            return

                    if crntTitleStrNumber == 2:
                        if regexSrtTiming.fullmatch(line) is not None:
                            gf.write(f"{line}\n")
                            continue
                        else:
                            sublime.error_message(
                                " ".join((
                                    f"{wrongFormatError} there",
                                    "should be a correct timing string",
                                    f"on the line {index+1}."
                                ))
                            )
                            scrollToProblematicLineNumber(activeView, index)
                            return

                    # replace actual titles with empty lines
                    gf.write("\n")

        # except UnicodeDecodeError as ex:
        #     sublime.error_message(
        #         " ".join((
        #             "It looks like the original SRT file is not",
        #             "in UTF-8 encoding. Try to re-open it",
        #             "with the right encoding and then save it with UTF-8."
        #         ))
        #     )
        #     return
        except Exception as ex:
            print(f"error: {ex}")
            sublime.error_message(
                " ".join((
                    "There was an error writing to the generated file.",
                    "Check console for details."
                ))
            )
            return

        openTranslationFile(
            self.window,
            originalFile,
            # [],
            str(generatedFile)
        )

    def input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "language" not in args:
            return LanguageInputHandler()

    def input_description(self) -> str:
        return "Language suffix"

    def is_enabled(self) -> bool:
        # return isItAnSRTfile(self.window.active_view().file_name())
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        # return isItAnSRTfile(self.window.active_view().file_name())
        return self.window.active_view().match_selector(0, "text.srt")


class MarlantOpenTranslationFileCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        originalFileValue: str = self.window.active_view().file_name()
        if not originalFileValue:
            sublime.error_message(
                "You can run this command only from an existing file."
            )
            return
        originalFile: pathlib.Path = pathlib.Path(originalFileValue)
        if originalFile.suffix != ".srt":
            sublime.error_message("This is not an .srt file.")
            return

        # openFiles = []
        # for v in self.window.views():
        #     openFiles.append(v.file_name())

        sublime.open_dialog(
            lambda f: sublime.set_timeout(
                lambda: openTranslationFile(
                    self.window,
                    originalFile,
                    # openFiles,
                    f
                )
            ),
            [("SubRip / SRT subtitles", ["srt"])],
            str(originalFile.parents[0]),
            False,
            False
        )

    def is_enabled(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")


class MarlantRenumberTitlesCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit) -> None:
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
                            f"{wrongFormatError} the line {index+1}",
                            "should not be empty."
                        ))
                    )
                    scrollToProblematicLine(self.view, region)
                    return
                else:
                    crntTitleStrNumber = 0
                    hadEmptyLine = True
                    continue

            hadEmptyLine = False
            crntTitleStrNumber += 1

            if crntTitleStrNumber == 1:
                if regexSrtNumber.fullmatch(line) is not None:
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
                            f"{wrongFormatError} the line {index+1}",
                            "should contain a non-zero title number."
                        ))
                    )
                    scrollToProblematicLine(self.view, region)
                    return

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
            titleOrdinal, titleTiming = parseTitleString(
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
        timingMatches = regexSrtTiming.match(titleTiming)
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
            timeCodeMS = timeCodeToMilliseconds(
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
            f"{millisecondsToTimeCode(newTimeCodeMS_start)}",
            "-->",
            f"{millisecondsToTimeCode(newTimeCodeMS_end)}"
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
            titleOrdinal, titleTiming, titleTextRegions = parseTitleString(
                self.view,
                self.view.split_by_newlines(currentTitleRegion)
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
            titleTextFirst, titleTextSecond = splitStringInTwo(firstString)
        if titleTextFirst.startswith("-"):
            titleTextFirst = re.sub(
                r"^-\s*",
                "",
                titleTextFirst
            )

        titleTimingFirst: str = titleTiming
        titleTimingSecond: str = titleTiming
        try:
            titleTimingFirst, titleTimingSecond = splitTimingInTwo(titleTiming)
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

        maxTitleLineLength: int = marlantSettings.get(
            "maximum_title_text_line_length",
            maxTitleLineLengthFallback
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
                parseTitleString(
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
                parseTitleString(
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
            joinedTitleTiming = joinTimings(firstTitleTiming, secondTitleTiming)
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


class MillisecondsInputHandler(sublime_plugin.TextInputHandler):
    def name(self) -> str:
        return "milliseconds"

    def placeholder(self) -> str:
        return "positive/negative integer"

    def initial_text(self) -> str:
        return "1000"

    def validate(self, text: str) -> bool:
        try:
            int(text)
            return True
        except ValueError:
            return False

    def preview(self, text: str) -> str:
        try:
            text = text.strip()
            milliseconds: int = int(text)
            shiftDirection: str = "forward"
            shiftCountEnding: str = "" if abs(milliseconds) == 1 else "s"
            if milliseconds > 0:
                text = re.sub(r"^\+\s*", "", text)
            else:
                text = re.sub(r"^-\s*", "", text)
                shiftDirection = "back"
            return sublime.Html(
                " ".join((
                    f"Shift all timings <b>{text}</b>",
                    f"millisecond{shiftCountEnding} <b>{shiftDirection}</b>"
                ))
            )
        except ValueError:
            return sublime.Html(
                "<i>That needs to be an integer.</i>"
            )


class MarlantShiftTimingsCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit, milliseconds: int) -> None:
        milliseconds = int(milliseconds)
        if milliseconds == 0:
            return
        if abs(milliseconds) > 3600000:
            sublime.error_message(
                " ".join((
                    "Surely you don't need to shift",
                    "the timings for more than 1 hour."
                ))
            )
            return

        timingsRegions: typing.List[sublime.Region] = (
            self.view.find_all(regexSrtTimingString)
        )
        if len(timingsRegions) < 1:
            sublime.error_message("Didn't find any timings in the file.")
            return

        # first title timing cannot go below 0
        firstTitleTimecodeMatches = regexSrtTiming.match(
            self.view.substr(timingsRegions[0])
        )
        # to keep mypy happy
        if firstTitleTimecodeMatches is None:
            sublime.error_message("The first title timing has a wrong format.")
            return
        firstTitleTimecodeStart: str = firstTitleTimecodeMatches.group(1)
        if (
            milliseconds < 0
            and timeCodeToMilliseconds(
                firstTitleTimecodeStart) < abs(milliseconds
            )
        ):
            sublime.error_message(
                "The shift value goes below 00:00:00,000 for the first title."
            )
            return

        # just in case, start from the last region,
        # to prevent theoretical regions drift
        for rgn in reversed(timingsRegions):
            self.view.replace(
                edit,
                rgn,
                shiftTiming(
                    self.view.substr(rgn),
                    milliseconds
                )
            )

    def input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "milliseconds" not in args:
            return MillisecondsInputHandler()

    def input_description(self) -> str:
        return "Timings shift"

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")


class MarlantValidateSubtitlesCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        activeView = self.window.active_view()
        activeView.erase_status(validationStatusKey)

        maxTitleLineLength: int = marlantSettings.get(
            "maximum_title_text_line_length",
            maxTitleLineLengthFallback
        )
        maxTitleLines: int = marlantSettings.get(
            "maximum_title_text_lines",
            maxTitleLinesFallback
        )
        minTitleDuration: int = marlantSettings.get(
            "minimum_title_duration",
            minTitleDurationFallback
        )
        maxTitleDuration: int = marlantSettings.get(
            "maximum_title_duration",
            maxTitleDurationFallback
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
                    else:
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
                if regexSrtNumber.fullmatch(line) is not None:
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

            # --- timing line

            if crntTitleStrNumber == 2:
                if regexSrtTiming.fullmatch(line) is not None:
                    timingMatches = regexSrtTiming.match(line)
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
                    timeStart: int = timeCodeToMilliseconds(
                        timingMatches.group(1)
                    )
                    timeEnd: int = timeCodeToMilliseconds(
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
            if (len(line) > maxTitleLineLength):
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
            if regexSrtTiming.fullmatch(line) is not None:
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

        # finished iterating through the lines, one last check
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
        else:
            activeView.set_status(validationStatusKey, "SubRip: OK")
            sublime.message_dialog(
                "All good! No problems found."
                # "checked {crntTitleCnt} titles."
            )

    def is_enabled(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")


# class FileEventListener(sublime_plugin.ViewEventListener):
#     def on_post_save_async(self):
#         # TODO: show translation progress (if in translation mode)
#         if self.view.match_selector(0, "text.srt"):
#             print("File was saved")
