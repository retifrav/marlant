import sublime
import sublime_plugin

# import functools
import pathlib
import re
import typing

from .plugins import (
    _common as common
)
from .plugins.files import (
    MarlantCreateTranslationFileCommand,
    MarlantOpenTranslationFileCommand
)
from .plugins.titles import (
    MarlantRenumberTitlesCommand,
    MarlantInsertNewTitleCommand,
    MarlantSplitTitleCommand,
    MarlantJoinTitlesCommand
)
from .plugins.timing import (
    MarlantShiftTimingsCommand
)
from .plugins.validation import (
    MarlantValidateAllTitlesCommand,
    MarlantExcludeTitleFromValidationsCommand,
    MarlantClearExcludedTitlesList
)


def plugin_loaded() -> None:
    # print("MarLant plugin has loaded")
    # when Sublime Text just started, plugins path is unknown,
    # and so settings need to be loaded after the plugin is loaded
    common.marlantSettings = sublime.load_settings(
        "marlant.sublime-settings"
    )
    pass


def plugin_unloaded() -> None:
    # print("MarLant plugin has unloaded")
    pass


# class FileEventListener(sublime_plugin.ViewEventListener):
#     def on_post_save_async(self):
#         # TODO: show translation progress (if in translation mode)
#         if self.view.match_selector(0, "text.srt"):
#             print("File was saved")
