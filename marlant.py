import sublime
import sublime_plugin

import pathlib
import re

import typing

# TODO: renumbering subtitles ordinals
# TODO: splitting subtitle in two
# TODO: joining two subtitles into one

wrongFormatError: str = " ".join((
    "The original SRT file seems to have",
    "a wrong format, because"
))
# might want to expose this as argument/setting
ofEncoding: str = "utf-8"

regexSrtNumber: typing.Pattern = re.compile(r"^[1-9]{1}\d*$")
regexSrtTimeCode: typing.Pattern = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$"
)


def plugin_loaded():
    # print("MarLant plugin has loaded")
    pass


def plugin_unloaded():
    # print("MarLant plugin has unloaded")
    pass


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

        # TODO: Check if that file is already opened in other tab/selection
        # print(window.find_open_file(selectedFile))
        # for f in window.views():
        #     print(f.file_name())
        # views = window.views()
        # for v in views:
        #     if v and v.file_name():
        #         print(v.file_name())

        # TODO: If there is already a selection, unselect everything

        try:
            window.open_file(
                selectedFile,
                sublime.ADD_TO_SELECTION
            )
        except Exception as ex:
            print(f"error: {ex}")
            sublime.error_message(
                " ".join((
                    "There was an error trying to open translation file.",
                    "Check console for details."
                ))
            )
            return


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


# ListInputHandler limits the choice, user can't enter custom values
# class LanguageInputHandler(sublime_plugin.ListInputHandler):
#     def placeholder(self):
#         return "language suffix"

#     def initial_text(self):
#         return "lang"

#     def list_items(self):
#         return [
#             ("en", 0),
#             ("ru", 1)
#         ]


class MarlantCreateTranslationFileCommand(sublime_plugin.WindowCommand):
    def run(self, language: str) -> None:
        originalFileValue: str = self.window.active_view().file_name()
        # these checks are likely redundant, because command is enabled
        # only for .srt files
        # if not originalFileValue:
        #     sublime.error_message(f"This is not a existing file")
        #     return
        originalFile: pathlib.Path = pathlib.Path(originalFileValue)
        # if originalFile.suffix != ".srt":
        #     sublime.error_message("This is not an .srt file")
        #     return

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
            # TODO: read lines from current buffer, not from file on disk
            with open(originalFile,
                      "r",
                      encoding=ofEncoding
                      ) as of, \
                open(generatedFile,
                     "w",
                     encoding="utf-8"
                     ) as gf:
                hadEmptyLine: bool = False
                crntTitleStrNumber: int = 0
                crntTitleCnt: int = 0
                for index, line in enumerate(of):
                    line = line.strip()

                    if not line:
                        if hadEmptyLine or index == 0:
                            sublime.error_message(
                                " ".join((
                                    f"{wrongFormatError} the line {index+1}",
                                    "should not be empty"
                                ))
                            )
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
                            return

                    if crntTitleStrNumber == 2:
                        if regexSrtTimeCode.fullmatch(line) is not None:
                            gf.write(f"{line}\n")
                            continue
                        else:
                            sublime.error_message(
                                " ".join((
                                    f"{wrongFormatError} there",
                                    "should have been a time code",
                                    f"on the line {index+1}"
                                ))
                            )
                            return

                    # replace actual titles with empty lines
                    gf.write("\n")

        except UnicodeDecodeError as ex:
            sublime.error_message(
                " ".join((
                    "It looks like the original SRT file is not",
                    "in UTF-8 encoding. Try to re-open it",
                    "with the right encoding and then save it with UTF-8"
                ))
            )
            return
        except Exception as ex:
            print(f"error: {ex}")
            sublime.error_message(
                " ".join((
                    "There was an error writing to the generated file.",
                    "Check console for details."
                ))
            )
            return

        openTranslationFile(self.window, originalFile, str(generatedFile))

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
        originalFile: pathlib.Path = pathlib.Path(
            self.window.active_view().file_name()
        )
        sublime.open_dialog(
            lambda f: openTranslationFile(self.window, originalFile, f),
            [("SubRip / SRT subtitles", ["srt"])],
            str(originalFile.parents[0]),
            False,
            False
        )

    def is_enabled(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")


class FileEventListener(sublime_plugin.ViewEventListener):
    def on_post_save(self):
        # TODO: show translation progress (if in translation mode)
        if self.view.match_selector(0, "text.srt"):
            print("File was saved")
