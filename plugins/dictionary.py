import sublime
import sublime_plugin

import typing

from . import _common as common


class DictionaryEntryOriginalInputHandler(sublime_plugin.TextInputHandler):
    def __init__(self, view: sublime.View) -> None:
        self.view = view

    def name(self) -> str:
        return "original"

    def placeholder(self) -> str:
        return "Windom Earle"

    def description(self, text: str) -> str:
        return "ENTRY"

    def initial_text(self) -> str:
        if len(self.view.sel()) == 1:
            return self.view.substr(self.view.sel()[0])
        else:
            return ""

    def validate(self, text: str) -> bool:
        text = text.strip()
        if not text or len(text) < 2 or len(text) > 40:
            return False
        else:
            return True

    def preview(self, text: str) -> str:
        text = text.strip()
        if not text or len(text) < 2:
            return sublime.Html(
                " ".join((
                    "<i>Cannot add this to the project dictionary,",
                    "entry is too short</i>"
                ))
            )
        elif len(text) > 40:
            return sublime.Html(
                " ".join((
                    "<i>Cannot add this to the project dictionary,",
                    "entry is too long</i>"
                ))
            )
        else:
            return sublime.Html(
                f"Add <b>{text}</b> to the project dictionary"
            )

    def next_input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "translation" not in args:
            return DictionaryEntryTranslationInputHandler()


class DictionaryEntryTranslationInputHandler(sublime_plugin.TextInputHandler):
    def name(self) -> str:
        return "translation"

    def placeholder(self) -> str:
        return "Уиндом Эрл"

    # def description(self, text) -> str:
    #     return "TRANSLATION"

    def validate(self, text: str) -> bool:
        text = text.strip()
        if not text or len(text) < 2 or len(text) > 40:
            return False
        else:
            return True

    def preview(self, text: str) -> str:
        text = text.strip()
        if not text or len(text) < 2:
            return sublime.Html(
                " ".join((
                    "<i>Cannot add this to the project dictionary,",
                    "entry is too short</i>"
                ))
            )
        elif len(text) > 40:
            return sublime.Html(
                " ".join((
                    "<i>Cannot add this to the project dictionary,",
                    "entry is too long</i>"
                ))
            )
        else:
            return sublime.Html(
                f"Add <b>{text}</b> translation to the project dictionary"
            )


class MarlantAddToDictionary(sublime_plugin.WindowCommand):
    def run(self, original: str, translation: str) -> None:
        if not self.window.project_file_name():
            sublime.error_message(
                " ".join((
                    "You need to have a Sublime Text project file",
                    "for this functionality to work."
                ))
            )
            return

        activeView = self.window.active_view()

        # TODO: move this to a generalized common functions
        # ensure that settings tree structure is in place
        projectData = self.window.project_data()
        if projectData:
            if not projectData.get("settings"):
                projectData["settings"] = {}
            if not projectData["settings"].get("marlant"):
                projectData["settings"]["marlant"] = {}
            if not projectData["settings"]["marlant"].get("dictionary"):
                projectData["settings"]["marlant"]["dictionary"] = {}
        else:
            sublime.error_message(
                " ".join((
                    "Couldn't get project data, check if you have",
                    "any content in your current Sublime Text project file."
                ))
            )
            return

        if original in projectData["settings"]["marlant"][
            "dictionary"
        ]:
            userAnswer: bool = sublime.ok_cancel_dialog(
                " ".join((
                    "The project dictionary already has this entry.",
                    "Do you want to update it?"
                )),
                "Yes"
            )
            if not userAnswer:
                return

        projectData["settings"]["marlant"]["dictionary"][
            original
        ] = translation
        self.window.set_project_data(projectData)

    def input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "original" not in args:
            return DictionaryEntryOriginalInputHandler(
                self.window.active_view()
            )
        if "translation" not in args:
            return DictionaryEntryTranslationInputHandler()

    def input_description(self) -> str:
        return "Add to dictionary"

    def is_enabled(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.window.active_view().match_selector(0, "text.srt")


class DictionaryEntryInputHandler(sublime_plugin.ListInputHandler):
    def __init__(self, view: sublime.View) -> None:
        self.view = view

    def name(self) -> str:
        return "original"

    def placeholder(self) -> str:
        return "Windom Earle"

    # def description(self, text) -> str:
    #     return "ENTRY"

    def initial_text(self) -> str:
        if len(self.view.sel()) == 1:
            return self.view.substr(self.view.sel()[0])
        else:
            return ""

    def list_items(self) -> typing.ItemsView[str, str]:
        dictionary: typing.Dict[str, str] = {}
        projectSettings: sublime.Value = None
        if self.view.window().project_file_name():
            projectSettings = self.view.window().project_data().get("settings")
        if projectSettings:
            dictionary = projectSettings.get(
                "marlant", {}
            ).get(
                "dictionary", {}
            )
        return dictionary.items()

    def preview(self, text: str) -> str:
        if not text:
            return sublime.Html("<i>No such entry in the dictionary</i>")
        else:
            return sublime.Html(f"Translation for this entry: <b>{text}</b>")


class MarlantFindInDictionary(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit, original: str) -> None:
        if not self.view.window().project_file_name():
            sublime.error_message(
                " ".join((
                    "You need to have a Sublime Text project file",
                    "for this functionality to work."
                ))
            )
            return

        for region in self.view.sel():
            self.view.replace(
                edit,
                region,
                original
            )

    def input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "original" not in args:
            return DictionaryEntryInputHandler(
                self.view.window().active_view()
            )

    def input_description(self) -> str:
        return "Find in dictionary"

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")
