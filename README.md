# MarLant

Sublime Text plugin for working with [SubRip/SRT](https://en.wikipedia.org/wiki/SubRip) subtitles.

<!-- MarkdownTOC -->

- [Features](#features)
- [Installing](#installing)
- [Credits](#credits)

<!-- /MarkdownTOC -->

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

## Credits

- SubRip / SRT syntax definition is based on [this implementation](https://github.com/SalGnt/Sublime-SRT/blob/master/SRT.tmLanguage), converted to `.sublime-syntax` format with [SublimeSyntaxConvertor tool](https://github.com/aziz/SublimeSyntaxConvertor)
- timecode parsing and composing is based on the code from [srt-shift](https://github.com/adeel/srt-shift)
- thanks to friendly and helpful Sublime Text community for answering my (*sometimes stupid*) questions
