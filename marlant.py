import sublime
import sublime_plugin

import pathlib


def plugin_loaded():
    print("marlant plugin has loaded")


def plugin_unloaded():
    print("marlant plugin has unloaded")


# might be an overkill, it is enough to just check for text.srt selector/scope
def isItAnSRTfile(fileFromView: str) -> bool:
    if fileFromView is not None:
        currentFilePath = pathlib.Path(fileFromView)
        if currentFilePath.suffix.lower() == ".srt":
            return True
    return False


class LanguageInputHandler(sublime_plugin.TextInputHandler):
    def placeholder(self):
        return "language suffix"

    def initial_text(self):
        return "lang"

    def validate(self, text):
        return True if text.strip() else False

    def preview(self, text):
        if text.strip():
            return f"some-file-{text}.srt"
        else:
            return "You need to provide a language suffix."


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
    def run(self, language):
        # there should be no need to check for empty string,
        # because TextInputHandler.validate() takes care of this
        language = language.strip()
        print(f"ololo, language: {language}")

    def input(self, args):
        if "language" not in args:
            return LanguageInputHandler()

    def is_enabled(self):
        # return isItAnSRTfile(self.window.active_view().file_name())
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self):
        # return isItAnSRTfile(self.window.active_view().file_name())
        return self.window.active_view().match_selector(0, "text.srt")


# TODO : Recalculate translation progress on save
