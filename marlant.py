import sublime
import sublime_plugin

# import functools
import pathlib
import re

import typing


wrongFormatError: typing.Final[str] = " ".join((
    "The SubRip content seems to have",
    "a wrong format, because"
))
wrongTitleFormatError: typing.Final[str] = " ".join((
    "Current title seems to have",
    "incorrect format, because"
))

titlePlaceholder: typing.Final[str] = "[ ... ]"

regexSrtNumber: typing.Final[typing.Pattern] = re.compile(r"^[1-9]{1}\d*$")
regexSrtTiming: typing.Final[typing.Pattern] = re.compile(
    # r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$"
    r"^(\d{2}:\d{2}:\d{2},\d{3}) (-->) (\d{2}:\d{2}:\d{2},\d{3})$"
)
regexSrtTimeCode: typing.Final[typing.Pattern] = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}$"
)


def plugin_loaded():
    # print("MarLant plugin has loaded")
    pass


def plugin_unloaded():
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
    firstHalf: str = stringToSplit[:len(stringToSplit)//2]
    secondHalf: str = stringToSplit[len(stringToSplit)//2:]
    return firstHalf, secondHalf


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
        return True if text.strip() else False

    def preview(self, text: str) -> str:
        if text.strip():
            return f"some-file-{text}.srt"
        else:
            return sublime.Html(
                "<i>You need to provide a language suffix.</i>"
            )


class MarlantCreateTranslationFileCommand(sublime_plugin.WindowCommand):
    def run(self, language: str):
        activeView = self.window.active_view()
        originalFileValue: str = activeView.file_name()
        if not originalFileValue:
            sublime.error_message(
                "You can run this command only from an existing file"
            )
            return
        originalFile: pathlib.Path = pathlib.Path(originalFileValue)
        if originalFile.suffix != ".srt":
            sublime.error_message("This is not an .srt file")
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
                # TODO: perhaps also scroll to the problematic line on error,
                # like on re-numbering titles ordinals
                for index, region in enumerate(bufferLinesRegions):
                    line = activeView.substr(region).strip()

                    if not line:
                        if hadEmptyLine or index == 0:
                            sublime.error_message(
                                " ".join((
                                    f"{wrongFormatError} the line {index+1}",
                                    "should not be empty"
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
                                        f"title number ({crntTitleCnt})"
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
                                    "should contain a title number"
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
                                    "should be a time code",
                                    f"on the line {index+1}"
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
        #             "with the right encoding and then save it with UTF-8"
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

    def input(self, args):
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
    def run(self):
        originalFileValue: str = self.window.active_view().file_name()
        if not originalFileValue:
            sublime.error_message(
                "You can run this command only from an existing file"
            )
            return
        originalFile: pathlib.Path = pathlib.Path(originalFileValue)
        if originalFile.suffix != ".srt":
            sublime.error_message("This is not an .srt file")
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
    def run(self, edit):
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
                            "should not be empty"
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
                    replacementBufferAdjustment += len(line) - len(crntTitleCntStr)
                    continue
                else:
                    sublime.error_message(
                        " ".join((
                            f"{wrongFormatError} the line {index+1}",
                            "should contain a non-zero title number"
                        ))
                    )
                    scrollToProblematicLine(self.view, region)
                    return

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")


class AfterCurrentTitleInputHandler(sublime_plugin.ListInputHandler):
    def placeholder(self):
        return "direction"

    def initial_text(self):
        return "after"

    def list_items(self):
        return [
            ("after", True),
            ("before", False)
        ]


class MarlantInsertNewTitleCommand(sublime_plugin.TextCommand):
    def run(self, edit, after_current_title: bool):
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
                    "can't guess the current title"
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
        if timingMatches is None:
            sublime.error_message("The title timing has a wrong format.")
            return
        # print(timingMatches.group(0)) # full timing
        # print(timingMatches.group(1)) # start time
        # print(timingMatches.group(2)) # separator
        # print(timingMatches.group(3)) # end time
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

    def input(self, args):
        if "after_current_title" not in args:
            return AfterCurrentTitleInputHandler()

    def input_description(self) -> str:
        return "Where"

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")


class MarlantSplitTitleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
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
                    "can't guess the current title"
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
            # print(
            #     " ".join((
            #         f"Title ordinal: {titleOrdinal},",
            #         f"timing: {titleTiming},",
            #         f"text: {titleTextRegions}"
            #     ))
            # )
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
        print("---")
        print(titleTextFirst if titleTextFirst else titlePlaceholder)
        print(titleTextSecond if titleTextSecond else titlePlaceholder)
        print("---")

        # newTitleTiming: str = "00:00:00,000 --> 00:00:00,000"
        # timingMatches = regexSrtTiming.match(titleTiming)
        # if timingMatches is None:
        #     sublime.error_message("The title timing has a wrong format.")
        #     return
        # # print(timingMatches.group(0)) # full timing
        # # print(timingMatches.group(1)) # start time
        # # print(timingMatches.group(2)) # separator
        # # print(timingMatches.group(3)) # end time
        # timeCodeMS: int = 0
        # newTimeCodeMS_start: int = 0
        # newTimeCodeMS_end: int = 0
        # try:
        #     timeCodeMS = timeCodeToMilliseconds(
        #         timingMatches.group(3) if after_current_title
        #         else timingMatches.group(1)
        #     )
        # except ValueError as ex:
        #     sublime.error_message(str(ex))
        #     return

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")


class FileEventListener(sublime_plugin.ViewEventListener):
    def on_post_save_async(self):
        # TODO: show translation progress (if in translation mode)
        if self.view.match_selector(0, "text.srt"):
            print("File was saved")
