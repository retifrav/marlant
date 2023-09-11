# MarLant

Sublime Text plugin for working with SubRip/SRT subtitles. Note that plugin functionality is enabled only when file/tab syntax is set to `SubRip / SRT`.

## Features

- SubRip / SRT syntax highlighting
- SubRip format validation
    + additional checks (*text lines length, titles duration, etc*)
- renumbering titles ordinals
- inserting new titles
- splitting a title in two
- joining two titles into one
- shifting all the timings
- opening a translation file in a split view
- generation of an empty translation file

All the commands are available in the Command Palette (`CTRL/COMMAND + SHIFT + P`), start typing `MarLant:` to see them all.

### Missing syntax highlighting in color schemes

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

## Links

- repository: <https://github.com/retifrav/marlant>
- bugreports / feature requests: <https://github.com/retifrav/marlant/issues>
