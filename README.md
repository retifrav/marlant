# MarLant

Sublime Text plugin for working with [SubRip/SRT](https://en.wikipedia.org/wiki/SubRip) subtitles.

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

## Credits

- SubRip / SRT syntax definition is based on [this implementation](https://github.com/SalGnt/Sublime-SRT/blob/master/SRT.tmLanguage), converted to `.sublime-syntax` format with [SublimeSyntaxConvertor tool](https://github.com/aziz/SublimeSyntaxConvertor)
- timecode parsing and composing is based on the code from [srt-shift](https://github.com/adeel/srt-shift)
