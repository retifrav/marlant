# MarLant

Sublime Text plugin for translating [SubRip/SRT](https://en.wikipedia.org/wiki/SubRip) subtitles. To clarify, it does not translate anything by itself, it just adds some conveniences for those awesome people who translate subtitles to other languages.

## Features

- SubRip / SRT syntax highlighting
- handy commands for working with subtitles:
    + renumbering titles ordinals
    + inserting new titles
    + splitting a title in two
    + joining two titles into one
    + empty translation file generation
- commands can be called from:
    + Command Palette
    + tab context menu
    + text area context menu

## Credits

- SubRip / SRT syntax definition is based on [this implementation](https://github.com/SalGnt/Sublime-SRT/blob/master/SRT.tmLanguage), converted to `.sublime-syntax` format with [SublimeSyntaxConvertor tool](https://github.com/aziz/SublimeSyntaxConvertor)
- timecode parsing and composing is based on the code from [srt-shift](https://github.com/adeel/srt-shift)
