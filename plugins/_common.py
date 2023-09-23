import sublime

import re
import typing

# will be read on plugin_loaded()
marlantSettings: sublime.Settings = {}
# fallback values
maxTitleLineLengthFallback: int = 41
maxTitleLinesFallback: int = 3
minTitleDurationFallback: int = 500
maxTitleDurationFallback: int = 6000
htmlTagsToWatchForFallback: typing.List[str] = ["b", "i", "u", "font"]

placeholdersInsteadOfEmptyLinesFallback: bool = True
titlePlaceholderFallback: typing.Final[str] = "[ ... ]"

regexLanguageCode: typing.Final[typing.Pattern] = re.compile(r"^[A-Za-z]+$")
regexSrtNumber: typing.Final[typing.Pattern] = re.compile(r"^[1-9]{1}\d*$")
# regexSrtTimingString = # r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$"
regexSrtTimingString = r"^(\d{2}:\d{2}:\d{2},\d{3}) (-->) (\d{2}:\d{2}:\d{2},\d{3})$"
regexSrtTiming: typing.Final[typing.Pattern] = re.compile(regexSrtTimingString)
regexSrtTimeCode: typing.Final[typing.Pattern] = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}$")

wrongFormatError: typing.Final[str] = " ".join((
    "The SubRip content seems to have",
    "a wrong format, because"
))
wrongTitleFormatError: typing.Final[str] = " ".join((
    "Current title seems to have",
    "incorrect format, because"
))


def scrollToProblematicLine(
    view: sublime.View,
    region: sublime.Region
) -> None:
    lineSelection = view.sel()
    lineSelection.clear()
    lineSelection.add(region)
    view.show(region)


def scrollToProblematicLineNumber(
    view: sublime.View,
    lineNumber: int
) -> None:
    pnt: int = view.text_point(lineNumber, 0)
    lineRegion: sublime.Region = view.line(pnt)
    scrollToProblematicLine(view, lineRegion)


def parseTitleString(
    view: sublime.View,
    titleRegions: typing.List[sublime.Region]
) -> typing.Tuple[int, str, typing.List[sublime.Region]]:
    # for index, region in enumerate(titleRegions):
    #     line = view.substr(region).strip()
    #     print(line)
    if len(titleRegions) < 3:
        raise ValueError(
            " ".join((
                wrongTitleFormatError,
                "it must have at least one line of text",
                "in addition to the ordinal and timing."
            ))
        )
    titleOrdinal = view.substr(titleRegions[0]).strip()
    if regexSrtNumber.fullmatch(titleOrdinal) is None:
        raise ValueError(
            " ".join((
                wrongTitleFormatError,
                "the first line should be a title ordinal."
            ))
        )
    titleTiming = view.substr(titleRegions[1]).strip()
    if regexSrtTiming.fullmatch(titleTiming) is None:
        raise ValueError(
            " ".join((
                wrongTitleFormatError,
                "the second line should be a title timing."
            ))
        )
    return int(titleOrdinal), titleTiming, titleRegions[2:]


def splitStringInTwo(stringToSplit: str) -> typing.Tuple[str, str]:
    titlePlaceholder = marlantSettings.get(
        "title_placeholder",
        titlePlaceholderFallback
    )
    middlePoint: int = len(stringToSplit) // 2
    while (
        stringToSplit[middlePoint] != " "
        and middlePoint != len(stringToSplit) - 1
    ):
        middlePoint += 1
    firstHalf: str = stringToSplit[:middlePoint]
    secondHalf: str = stringToSplit[middlePoint:]
    if len(secondHalf) == 1:
        firstHalf = stringToSplit
        secondHalf = ""
    return (
        firstHalf if firstHalf else titlePlaceholder,
        secondHalf.strip() if secondHalf else titlePlaceholder
    )
