# MarLant

<!-- MarkdownTOC -->

- [About](#about)
    - [Features](#features)
    - [Demonstration](#demonstration)
- [Installing](#installing)
    - [Requirements](#requirements)
    - [Syntax highlighting in color schemes](#syntax-highlighting-in-color-schemes)
- [Using projects](#using-projects)
- [FAQ](#faq)
    - [No plugin commands available anywhere](#no-plugin-commands-available-anywhere)
    - [Are there keybindings](#are-there-keybindings)
    - [Why the Sublime Text 4 requirement and v4099 as the lowest](#why-the-sublime-text-4-requirement-and-v4099-as-the-lowest)
    - [Why the Python 3.8 plugin host requirement](#why-the-python-38-plugin-host-requirement)
    - [The plugin is licensed under GPLv3, will it infect everything else with GPLv3](#the-plugin-is-licensed-under-gplv3-will-it-infect-everything-else-with-gplv3)
    - [Who killed Laura Palmer](#who-killed-laura-palmer)
- [Credits](#credits)

<!-- /MarkdownTOC -->

## About

[Sublime Text](https://sublimetext.com/) plugin for working with [SubRip/SRT](https://en.wikipedia.org/wiki/SubRip) subtitles.

![Sublime Text plugin MarLant](https://raw.githubusercontent.com/retifrav/marlant/master/misc/MarLant.png "MarLant, context menu")

*UI theme and color scheme used on the screenshot and demonstration videos below: [One Dark](https://github.com/andresmichel/one-dark-theme).*

### Features

- SubRip / SRT syntax highlighting
- various functions for working with subtitles:
    + SubRip format validation and additional checks
        * text lines length
        * titles duration
        * unclosed HTML tags
        * etc
    + titles management
        * renumbering titles ordinals
        * inserting new titles
        * splitting a title in two
        * joining two titles into one
        * shifting all the timings
    + translation
        * opening a translation file in a split view
        * generation of an empty translation file
        * project dictionary

Commands can be called from:

- Command Palette (`CTRL/COMMAND + SHIFT + P`) (*all the commands*)
- tab context menu (*translation file creation/opening*)
- text area context menu (*inserting, splitting and joining titles*)

### Demonstration

Validating the file:

https://user-images.githubusercontent.com/6904927/168665456-589fd743-86a5-4c4d-97b2-56a6ca40435a.mp4

Joining and splitting titles:

https://user-images.githubusercontent.com/6904927/168662707-c775db65-b73e-4347-b8fa-209741ea85b9.mp4

Creating and openning a translation file:

https://user-images.githubusercontent.com/6904927/168663924-b1236762-3207-480e-895e-aa7754f62cf5.mp4

## Installing

- via [Package Control](https://packagecontrol.io/packages/MarLant):
    + `CTRL/COMMAND + SHIFT + P` → `Package Control: Install Package` → `MarLant`
- manually:
    + clone the repository and copy its folder (`marlant`) to `/path/to/Sublime Text/Packages/`
        * the exact path to packages can be opened with `CTRL/COMMAND + SHIFT + P` → `Preferences: Browse Packages`
        * you might want to skip copying resources listed in `.gitattributes` file
            - or just download an archive attached to the latest [tag](https://github.com/retifrav/marlant/tags)

### Requirements

- Sublime Text v4099 or newer
    + Python plugin host v3.8 or newer

### Syntax highlighting in color schemes

If your color scheme lacks syntax highlighting rules for `text.srt` scope, you can add those based on the following rules (*these are meant for a dark color scheme*) via `Settings` → `Customize Color Scheme`:

``` json
{
    "variables":
    {
    },
    "globals":
    {
    },
    "rules":
    [
        {
            "name": "SRT title ordinal",
            "scope": "text.srt variable.function markup.bold",
            "font_style": "bold",
            "foreground": "#efc778"
        },
        {
            "name": "SRT title timecode",
            "scope": "text.srt variable.function markup.italic",
            "font_style": "italic",
            "foreground": "#c56ddf"
        },
        {
            "name": "SRT title timecode divider",
            "scope": "text.srt variable.function",
            "foreground": "#c56ddf"
        },
        {
            "name": "SRT title HTML tags",
            "scope": "text.srt comment.srt markup.bold.srt",
            "foreground": "#5f697a"
        },
        {
            "name": "SRT title text in HTML tags",
            "scope": "text.srt markup.italic.srt",
            "font_style": "italic",
            "foreground": "#abb2bf"
        }
    ]
}
```

To get the scope value of a particular element, place a cursor on it and open `Tools` → `Developer` → `Show Scope Name`.

## Using projects

As you might know, Sublime Text has [projects](https://www.sublimetext.com/docs/projects.html), and the plugin can and does use the project file for storing certain settings.

Here's an example of a project:

``` json
{
    "folders":
    [
        {
            "path": ".",
            "folder_exclude_patterns":
            [
                ".git"
            ]
        }
    ],
    "settings":
    {
        "marlant":
        {
            "dictionary":
            {
                "Sverre": "Сварре",
                "Thorvald": "Турвальд"
            },
            "validation":
            {
                "excluded-titles":
                {
                    "gutta-paa-skauen-s01e01-den-femte-mann.srt":
                    [
                        3,
                        5,
                        38
                    ],
                    "gutta-paa-skauen-s01e02-koppen.srt":
                    [
                        12,
                        25
                    ]
                }
            }
        }
    }
}
```

As you can see, translator/editor added some titles numbers to the list of excluded titles (*per file*), and so now those will be excluded from most of the validation checks.

Another example is the project dictionary. It can help with maintaining the consistency of translation/spelling of certain things, such as characters names, so translator wouldn't need to go back looking for the way he spelled them before.

## FAQ

### No plugin commands available anywhere

Check that the active file/view has the SubRip/SRT syntax/scope, as the plugin functionality is only enabled there.

### Are there keybindings

Not out of the box, but you can certainly [create your own keybinding](https://www.sublimetext.com/docs/key_bindings.html) for any plugin command. To get a command name and its arguments, enable commands logging (`sublime.log_commands(True)`) in Console.

For example, the following adds two keybindings: for inserting a new title before and after the current one:

``` json
{
    "keys": ["super+alt+i", "super+alt+b"],
    "command": "marlant_insert_new_title",
    "args": {"after_current_title": false }
},
{
    "keys": ["super+alt+i", "super+alt+a"],
    "command": "marlant_insert_new_title",
    "args": {"after_current_title": true }
}
```

### Why the Sublime Text 4 requirement and v4099 as the lowest

The version 4 in general is because that's where Python plugin host v3.8 was added. And the v4099 specifically as the minimal one is because it's the one with the latest plugin host v3.8.8. But of course most likely the plugin will also work fine with the very first v4050.

### Why the Python 3.8 plugin host requirement

Mostly because of [f-strings](https://peps.python.org/pep-0498/) that were added only in Python 3.6 and thus are not available with plugin host v3.3.

### The plugin is licensed under GPLv3, will it infect everything else with GPLv3

The intention is that if you'd use this plugin sources to create something else, and/or redistribute it (*as is or modified*), then that would indeed be infected with GPLv3. But for the purpose of simply using the plugin in Sublime Text the GPLv3 terms shouldn't apply any restrictions/requirements.

### Who killed Laura Palmer

One day, my log will have something to say about this.

## Credits

- SubRip / SRT syntax definition is based on [this implementation](https://github.com/SalGnt/Sublime-SRT/blob/master/SRT.tmLanguage), converted to `.sublime-syntax` format with [SublimeSyntaxConvertor tool](https://github.com/aziz/SublimeSyntaxConvertor)
- timecode parsing and composing is based on the code from [srt-shift](https://github.com/adeel/srt-shift/blob/master/srt_shift.py)
- thanks to:
    + [OdatNurd](https://odatnurd.net/) for his [Plugin 101 - How to write Packages for Sublime](https://youtube.com/playlist?list=PLGfKZJVuHW91zln4ADyZA3sxGEmq32Wse) video-course
    + friendly and helpful Sublime Text community for answering my (*sometimes stupid*) questions
