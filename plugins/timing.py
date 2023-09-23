import sublime
import sublime_plugin

import re
import typing

from . import _common as common


def timeCodeToMilliseconds(timeCode: str) -> int:
    if common.regexSrtTimeCode.fullmatch(timeCode) is None:
        raise ValueError("Timecode has a wrong format.")
    tms = timeCode.split(":")
    hour: int = int(tms[0])
    minute: int = int(tms[1])
    seconds: typing.List[str] = tms[2].split(",")
    second: int = int(seconds[0])
    millisecond: int = int(seconds[1])

    return (
        hour * 60 * 60 * 1000 +
        minute * 60 * 1000 +
        second * 1000 +
        millisecond
    )


def millisecondsToTimeCode(milliseconds: int) -> str:
    timeComponents: typing.Tuple[int, int, int, int] = (
        milliseconds // (60 * 60 * 1000),
        (milliseconds % (60 * 60 * 1000)) // (60 * 1000),
        (milliseconds % (60 * 1000)) // 1000,
        milliseconds % 1000
    )
    return "%02d:%02d:%02d,%03d" % timeComponents


def splitTimingInTwo(timingToSplit: str) -> typing.Tuple[str, str]:
    timingMatches = common.regexSrtTiming.match(timingToSplit)
    # print(timingMatches.group(0)) # full timing
    # print(timingMatches.group(1)) # start time
    # print(timingMatches.group(2)) # separator
    # print(timingMatches.group(3)) # end time
    if timingMatches is None:
        raise ValueError("The title timing has a wrong format.")
    timingStart: int = timeCodeToMilliseconds(timingMatches.group(1))
    timingEnd: int = timeCodeToMilliseconds(timingMatches.group(3))
    timingHalfLength: int = (timingEnd - timingStart) // 2
    endTimeFirst: str = millisecondsToTimeCode(
        timingStart + timingHalfLength
    )
    startTimeSecond: str = millisecondsToTimeCode(
        timingEnd - timingHalfLength + 1
    )
    return (
        f"{timingMatches.group(1)} {timingMatches.group(2)} {endTimeFirst}",
        f"{startTimeSecond} {timingMatches.group(2)} {timingMatches.group(3)}"
    )


def joinTimings(timingStartStr: str, timingEndStr: str) -> str:
    timingStartMatches = common.regexSrtTiming.match(timingStartStr)
    timingEndMatches = common.regexSrtTiming.match(timingEndStr)
    # print(timingStartMatches.group(0)) # full timing
    # print(timingStartMatches.group(1)) # start time
    # print(timingStartMatches.group(2)) # separator
    # print(timingStartMatches.group(3)) # end time
    if timingStartMatches is None or timingEndMatches is None:
        raise ValueError("One of the title timings has a wrong format.")
    timingStart: int = timeCodeToMilliseconds(timingStartMatches.group(1))
    timingEnd: int = timeCodeToMilliseconds(timingEndMatches.group(3))
    # if timingEnd < timingStart:
    #     raise ValueError("Second timing cannot be earlier than the first one.")
    return (
        " ".join((
            timingStartMatches.group(1),
            timingStartMatches.group(2),
            timingEndMatches.group(3)
        )) if timingEnd > timingStart
        else
        " ".join((
            timingEndMatches.group(1),
            timingStartMatches.group(2),
            timingStartMatches.group(3)
        ))
    )


def shiftTiming(timingToShift: str, shiftValue: int) -> str:
    timingMatches = common.regexSrtTiming.match(timingToShift)
    # print(timingMatches.group(0)) # full timing
    # print(timingMatches.group(1)) # start time
    # print(timingMatches.group(2)) # separator
    # print(timingMatches.group(3)) # end time
    if timingMatches is None:
        raise ValueError("The title timing has a wrong format.")
    timingStart: int = timeCodeToMilliseconds(timingMatches.group(1)) + shiftValue
    timingEnd: int = timeCodeToMilliseconds(timingMatches.group(3)) + shiftValue
    return " ".join((
        millisecondsToTimeCode(timingStart),
        timingMatches.group(2),
        millisecondsToTimeCode(timingEnd)
    ))


class MillisecondsInputHandler(sublime_plugin.TextInputHandler):
    def name(self) -> str:
        return "milliseconds"

    def placeholder(self) -> str:
        return "positive/negative integer"

    def initial_text(self) -> str:
        return "1000"

    def validate(self, text: str) -> bool:
        try:
            int(text)
            return True
        except ValueError:
            return False

    def preview(self, text: str) -> str:
        try:
            text = text.strip()
            milliseconds: int = int(text)
            shiftDirection: str = "forward"
            shiftCountEnding: str = "" if abs(milliseconds) == 1 else "s"
            if milliseconds > 0:
                text = re.sub(r"^\+\s*", "", text)
            else:
                text = re.sub(r"^-\s*", "", text)
                shiftDirection = "back"
            return sublime.Html(
                " ".join((
                    f"Shift all timings <b>{text}</b>",
                    f"millisecond{shiftCountEnding} <b>{shiftDirection}</b>"
                ))
            )
        except ValueError:
            return sublime.Html(
                "<i>That needs to be an integer</i>"
            )


class MarlantShiftTimingsCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit, milliseconds: int) -> None:
        # CHECK: is it redundant to cast in this case?
        milliseconds = int(milliseconds)
        if milliseconds == 0:
            return
        if abs(milliseconds) > 3600000:
            sublime.error_message(
                " ".join((
                    "Surely you don't need to shift",
                    "the timings for more than 1 hour."
                ))
            )
            return

        timingsRegions: typing.List[sublime.Region] = (
            self.view.find_all(common.regexSrtTimingString)
        )
        if len(timingsRegions) < 1:
            sublime.error_message("Didn't find any timings in the file.")
            return

        # first title timing cannot go below 0
        firstTitleTimecodeMatches = common.regexSrtTiming.match(
            self.view.substr(timingsRegions[0])
        )
        # to keep mypy happy
        if firstTitleTimecodeMatches is None:
            sublime.error_message("The first title timing has a wrong format.")
            return
        firstTitleTimecodeStart: str = firstTitleTimecodeMatches.group(1)
        if (
            milliseconds < 0
            and timeCodeToMilliseconds(
                firstTitleTimecodeStart) < abs(milliseconds
            )
        ):
            sublime.error_message(
                "The shift value goes below 00:00:00,000 for the first title."
            )
            return

        # just in case, start from the last region,
        # to prevent theoretical regions drift
        for rgn in reversed(timingsRegions):
            self.view.replace(
                edit,
                rgn,
                shiftTiming(
                    self.view.substr(rgn),
                    milliseconds
                )
            )

    def input(self, args: dict) -> sublime_plugin.TextInputHandler:
        if "milliseconds" not in args:
            return MillisecondsInputHandler()

    def input_description(self) -> str:
        return "Timings shift"

    def is_enabled(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")

    def is_visible(self) -> bool:
        return self.view.window().active_view().match_selector(0, "text.srt")
