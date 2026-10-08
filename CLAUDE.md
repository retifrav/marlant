# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MarLant is a Sublime Text 4 plugin (build 4205 and newer) for SubRip/SRT subtitles: syntax highlighting, format validation, title management (renumber, insert, split, join, shift timings) and translation helpers (translation file generation and split-view opening, a project dictionary). The code imports `sublime`/`sublime_plugin`, which exist only inside Sublime Text's plugin host, and Sublime Text is not installed in the container, so nothing here can be executed: there is no build and no test suite. Verification is the type check below, then the user trying it in Sublime Text.

## Type checking

```sh
uvx --python 3.14 mypy plugin.py plugins
```

`mypy.ini` declares the target (`python_version = 3.14`), but keep `--python 3.14` on the command too: mypy parses with its own interpreter, so it can only accept syntax new in 3.14 when it runs on 3.14. `mypy.ini` also sets `disallow_untyped_defs`, so every function needs full annotations. It also sets `ignore_missing_imports` and there are no Sublime stubs, so the whole Sublime API is `Any` — mypy says nothing about Sublime API misuse.

## Plugin host: Python 3.14

`.python-version` (`3.14`) selects Sublime Text's 3.14 plugin host, and it must keep shipping. That host exists from build 4205, where it replaced 3.8. Older builds treat `3.14` as an unknown value and run the package on 3.3, where the f-strings don't even parse. So this file is what drops builds below 4205, and the Package Control release range (see Releasing) must say the same. `3.8` would also select 3.14 on 4205+ for backward compatibility, but it is not equivalent, because it would let older builds load newer code. Python 3.9–3.14 features are allowed. The existing code still uses `typing.List`/`Dict`/`Tuple`-style annotations; match that unless the change is a deliberate modernization.

## Architecture

- **Only `plugin.py` is loaded by Sublime Text** (it loads top-level `.py` files of a package). `plugins/` is a subpackage, and its command classes are registered solely because `plugin.py` imports them. A new command needs that import plus an entry in `marlant.sublime-commands`, and optionally in `Context.sublime-menu` (text area) / `Tab Context.sublime-menu` (tab). The command name is derived from the class name: an optional `Command` suffix is stripped and CamelCase becomes snake_case, so `MarlantClearExcludedTitlesList` is `marlant_clear_excluded_titles_list` (three classes omit the suffix, and adding it would not change their names). **No runs of capitals in command or input-handler class names** (`Html`, not `HTML`): build 4206 rewrote this conversion, so `MarlantHTMLTagsCommand` is `marlant_hTMLTags` on 4205 but `marlant_html_tags` on 4206+. Either keep names single-capital-per-word or override `name()`.
- **Settings are read through the module attribute, never imported by name.** `_common.marlantSettings` is an empty placeholder that `plugin_loaded()` in `plugin.py` replaces, because settings cannot be loaded at import time. Always write `common.marlantSettings.get("key", common.<name>Fallback)`. `from ._common import marlantSettings` binds the placeholder forever, which is the same bug class fixed in v0.6.1. A new setting needs both its commented default in `marlant.sublime-settings` and a matching `*Fallback` constant in `_common.py`.
- `_common.py` also holds the shared regexes (ordinal, timing, timecode), the error-message prefixes, the scroll-to-line helpers and `parseTitleString`. `timing.py` holds timecode ↔ milliseconds conversion and timing split/join/shift, and `titles.py` and `validation.py` both use it.
- **Locating the title under the cursor** is the same idiom in insert, split, join and exclude: `find_by_class(point, ±, CLASS_EMPTY_LINE)` both ways → region (no `+1` when it is the first title at offset 0) → `split_by_newlines` → `common.parseTitleString`, which returns `(ordinal, timing, textRegions)` or raises `ValueError`. Join also guesses "last title" with a `view.size() - 30` heuristic because trailing empty lines count towards the size.
- **Three whole-buffer walkers re-implement the same line state machine**: translation file generation (`files.py`), renumbering (`titles.py`) and validation (`validation.py`). They all use `hadEmptyLine`/`crntTitleStrNumber`: an empty line ends a title, line 1 is the ordinal (must be a +1 increment), line 2 is the timing, and the rest is text. A change to what counts as valid SRT has to land in all three.
- **Insert, split and join all finish with `run_command("marlant_renumber_titles")`, and renumbering clears the current file's excluded-titles list**, because ordinals change. So any of those edits resets exclusions; the cleared values are printed to the console.
- **Multi-region edits must not drift**: regions computed before editing go stale as the buffer changes. Renumbering compensates with `replacementBufferAdjustment`, and timing shift iterates `reversed(...)`. Keep one of those patterns.
- Validation stops at the first problem: `failedValidation` sets the `marlant_validation_status` status-bar key, scrolls to the line and shows a dialog. For titles in the excluded list, everything after the ordinal and whitespace checks is skipped (timing, durations, overlap, line length/count, HTML tags).
- **Project data** (requires a `.sublime-project`; commands check `window.project_file_name()` first) lives under `settings.marlant`: `dictionary` maps original → translation, and `validation.excluded-titles` maps a file's *basename* to a list of ordinals. Writers rebuild the nested dicts if missing and then call `set_project_data`; that rebuild is duplicated, with a TODO, in `dictionary.py` and `validation.py`. The README section "Using projects" documents this schema for users, so keep it in sync.
- Every command gates `is_enabled`/`is_visible` on `match_selector(0, "text.srt")`, and new ones must too. The `text.srt` scope and its sub-scopes come from `subrip.sublime-syntax`. Their names are also quoted in the color-scheme snippets in both `README.md` and `messages/install.md`, so renaming a scope breaks users' customizations, and both snippets need updating.
- Arguments come from input handlers when a command is run from the Command Palette without args, and directly from menus (e.g. `after_current_title`). A handler's `name()` must equal the `run()` keyword. In `MarlantFindInDictionary` the `original` keyword actually receives the *translation*: list items are `(original, translation)` pairs, the palette shows and filters on the first half, and the second half is what gets passed. That is the intended behaviour (the selection is replaced by the translation), so don't swap the pair; only the name is misleading.

## Conventions

- camelCase for functions and variables (not PEP 8) and full `typing.` annotations. Long user-facing messages are built as `" ".join(("…", "…"))`. Helpers raise `ValueError`, and commands catch it and show it with `sublime.error_message(str(ex))`, printing extra detail to the console.
- Commit messages: `For #N: …` (progress on issue N), `Closed #N: …`, `README: …`, `Version X.Y.Z`. The only branch is `master`, and the remote is named `GitHub`, not `origin`.

## Releasing

- The supported Sublime Text range is not declared in this repo but in the Package Control channel: the `MarLant` entry in `repository/m.json` of `sublimehq/package_control_channel` (formerly `wbond/…`), changed by pull request there. Its `releases` items pair a `sublime_text` range with a tag prefix (`"tags": "v"` picks the highest `v*` tag). Any range change has to be merged before the first tag that needs it is pushed. Otherwise Package Control offers that release to builds that cannot load it.
- A release is a `vX.Y.Z` tag plus `messages/vX.Y.Z.md`, and that file must also be registered in `messages.json` (forgetting this needed a follow-up commit for 0.7.0). `messages/install.md` is shown on install and keeps its own feature list.
- `.gitattributes` `export-ignore` decides what is left out of release archives. Dev-only files, this one and `/.claude/` included, belong there.
- The README table of contents between the `<!-- MarkdownTOC -->` markers is generated by the MarkdownTOC package; update it when adding or renaming headings.
- Test a manual install as `Packages/MarLant`, with that exact case: the `edit_settings` entries reference `${packages}/MarLant/…`.
