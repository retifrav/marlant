import sublime
import sublime_plugin

import pathlib
import typing

from . import _common as common


# might be an overkill, it is enough to just check for text.srt selector/scope
# def isItAnSRTfile(fileFromView: str) -> bool:
#     if fileFromView is not None:
#         currentFilePath = pathlib.Path(fileFromView)
#         if currentFilePath.suffix.lower() == ".srt":
#             return True
#     return False


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
                print(f"[ERROR] {ex}")
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
        if common.regexLanguageCode.fullmatch(text) is None:
            return False
        else:
            return True

    def preview(self, text: str) -> str:
        if text.strip():
            return sublime.Html(f"some-file-<b>{text}</b>.srt")
        else:
            return sublime.Html(
                "<i>You need to provide a language suffix</i>"
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

        titlePlaceholder = common.marlantSettings.get(
            "title_placeholder",
            common.titlePlaceholderFallback
        )

        placeholdersInsteadOfEmptyLines: bool = common.marlantSettings.get(
            "placeholders_instead_of_empty_lines",
            common.placeholdersInsteadOfEmptyLinesFallback
        )
        whatToReplaceTitlesWith: str = (
            titlePlaceholder if placeholdersInsteadOfEmptyLines
            else ""
        )

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
                                    f"{common.wrongFormatError} the line {index+1}",
                                    "should not be empty."
                                ))
                            )
                            common.scrollToProblematicLineNumber(activeView, index)
                            return
                        else:
                            crntTitleStrNumber = 0
                            hadEmptyLine = True
                            gf.write("\n")
                            continue

                    hadEmptyLine = False
                    crntTitleStrNumber += 1

                    if crntTitleStrNumber == 1:
                        if common.regexSrtNumber.fullmatch(line) is not None:
                            crntTitleCntCandidate = int(line)
                            if crntTitleCntCandidate - crntTitleCnt != 1:
                                sublime.error_message(
                                    " ".join((
                                        f"{common.wrongFormatError} the title number",
                                        f"on the line {index+1}",
                                        f"({crntTitleCntCandidate}) is not",
                                        "a +1 increment of the previous",
                                        f"title number ({crntTitleCnt})."
                                    ))
                                )
                                common.scrollToProblematicLineNumber(activeView, index)
                                return
                            else:
                                crntTitleCnt = crntTitleCntCandidate
                                gf.write(f"{line}\n")
                                continue
                        else:
                            sublime.error_message(
                                " ".join((
                                    f"{common.wrongFormatError} the line {index+1}",
                                    "should contain a title number."
                                ))
                            )
                            common.scrollToProblematicLineNumber(activeView, index)
                            return

                    if crntTitleStrNumber == 2:
                        if common.regexSrtTiming.fullmatch(line) is not None:
                            gf.write(f"{line}\n")
                            continue
                        else:
                            sublime.error_message(
                                " ".join((
                                    f"{common.wrongFormatError} there",
                                    "should be a correct timing string",
                                    f"on the line {index+1}."
                                ))
                            )
                            common.scrollToProblematicLineNumber(activeView, index)
                            return

                    # replace actual titles
                    gf.write(f"{whatToReplaceTitlesWith}\n")

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
            print(f"[ERROR] {ex}")
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
