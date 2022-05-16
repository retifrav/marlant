# MarLant

Sublime Text plugin for working with [SubRip/SRT](https://en.wikipedia.org/wiki/SubRip) subtitles.

<!-- MarkdownTOC -->

- [Features](#features)
- [Installing](#installing)
- [Requirements](#requirements)
- [FAQ](#faq)
    - [No plugin commands available anywhere](#no-plugin-commands-available-anywhere)
    - [Why the Sublime Text 4 requirement and v4099 as the lowest](#why-the-sublime-text-4-requirement-and-v4099-as-the-lowest)
    - [Why the Python 3.8 plugin host requirement](#why-the-python-38-plugin-host-requirement)
    - [The plugin is licensed under GPLv3, will it infect everything else with GPLv3](#the-plugin-is-licensed-under-gplv3-will-it-infect-everything-else-with-gplv3)
    - [Who killed Laura Palmer](#who-killed-laura-palmer)
- [Credits](#credits)

<!-- /MarkdownTOC -->

![Sublime Text plugin MarLant](https://raw.githubusercontent.com/retifrav/marlant/master/misc/MarLant.png "MarLant, context menu")

## Features

- SubRip / SRT syntax highlighting
- various functions for working with subtitles:
    + SubRip format validation
        * additional checks (*text lines length, titles duration, etc*)
    + renumbering titles ordinals
    + inserting new titles
    + splitting a title in two
    + joining two titles into one
    + shifting all the timings
    + opening a translation file in a split view
    + generation of an empty translation file

Commands can be called from:

- Command Palette (`CTRL/COMMAND + SHIFT + P`)
- tab context menu
- text area context menu

## Installing

- via [Package Control](https://packagecontrol.io/):
    + `CTRL/COMMAND + SHIFT + P` → `Package Control: Install Package` → `MarLant`
- manually:
    + clone repository and copy its folder (`marlant`) to `/path/to/Sublime Text/Packages/`
        * the exact path to packages can be opened with `CTRL/COMMAND + SHIFT + P` → `Preferences: Browse Packages`
        * you might want to skip copying resources listed in `.gitattributes` file

## Requirements

- Sublime Text v4099 or newer
    + Python plugin host v3.8 or newer

## FAQ

### No plugin commands available anywhere

Check that the active file/view has the SubRip/SRT syntax/scope, as the plugin functionality is only enabled there.

### Why the Sublime Text 4 requirement and v4099 as the lowest

The version 4 in general is because that's there Python plugin host v3.8 was added. The v4099 as the minimal one is because it's the one with the latest Python 3.8.8 plugin host. But of course most likely the plugin will also work fine with the very first v4050.

### Why the Python 3.8 plugin host requirement

Mostly because of [f-strings](https://peps.python.org/pep-0498/) that were added in Python 3.6 and so are not available with v3.3 plugin host.

### The plugin is licensed under GPLv3, will it infect everything else with GPLv3

The intention is that if you'd use this plugin sources to create something else, and/or redistribute it (*as is or modified*), then that would indeed be infected with GPLv3. But for the purpose of simply using the plugin in Sublime Text the GPLv3 terms shouldn't apply any restrictions/requirements.

### Who killed Laura Palmer

One day, my log will have something to say about this.

## Credits

- SubRip / SRT syntax definition is based on [this implementation](https://github.com/SalGnt/Sublime-SRT/blob/master/SRT.tmLanguage), converted to `.sublime-syntax` format with [SublimeSyntaxConvertor tool](https://github.com/aziz/SublimeSyntaxConvertor)
- timecode parsing and composing is based on the code from [srt-shift](https://github.com/adeel/srt-shift/blob/master/srt_shift.py)
- thanks to:
    + [OdatNerd](https://odatnurd.net/) for his [Plugin 101 - How to write Packages for Sublime](https://youtube.com/playlist?list=PLGfKZJVuHW91zln4ADyZA3sxGEmq32Wse) video-course
    + friendly and helpful Sublime Text community for answering my (*sometimes stupid*) questions
