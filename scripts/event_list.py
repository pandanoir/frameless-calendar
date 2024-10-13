from bisect import bisect_left
import re
import datetime


class ICalendarEvent:
    def __init__(self, start_at: datetime, end_at: datetime, title: str):
        self.start_at = start_at
        self.end_at = end_at
        self.title = title


def format_iso8601(iso_str: str) -> str:
    # 正規表現で元の形式の文字列を解析
    match = re.match(
        r'^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})(Z?)$', iso_str)
    if not match:
        raise ValueError("Invalid ISO 8601 format")

    year, month, day, hour, minute, second, z = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:{second}{z}"


def unfold_lines(lines):
    unfolded_lines = []
    buffer = ""

    for line in lines:
        if line.startswith(" "):  # フォールディングされた行
            buffer += line[1:]
            continue
        if buffer:
            unfolded_lines.append(buffer)
        buffer = line

    if buffer:
        unfolded_lines.append(buffer)

    return unfolded_lines


def parse_ics(ics_str: str):
    ics_arr = []
    lines = ics_str.splitlines()
    unfolded_lines = unfold_lines(lines)
    current_event = None

    for line in unfolded_lines:
        if line.startswith("BEGIN:VEVENT"):
            current_event = {}
            continue
        if line.startswith("END:VEVENT"):
            if not current_event:
                continue
            if 'DTSTART' in current_event and 'DTEND' in current_event:
                ics_arr.append(ICalendarEvent(
                    start_at=datetime.datetime.fromisoformat(
                        format_iso8601(current_event['DTSTART'])),
                    end_at=datetime.datetime.fromisoformat(
                        format_iso8601(current_event['DTEND'])),
                    title=current_event.get('SUMMARY', '')
                ))
            elif 'DTSTART;VALUE=DATE' in current_event and 'DTEND;VALUE=DATE' in current_event:
                ics_arr.append(ICalendarEvent(
                    start_at=datetime.datetime.fromisoformat(format_iso8601(
                        f"{current_event['DTSTART;VALUE=DATE']}T000000") + '+09:00'),
                    end_at=datetime.datetime.fromisoformat(format_iso8601(
                        f"{current_event['DTEND;VALUE=DATE']}T000000") + '+09:00'),
                    title=current_event.get('SUMMARY', '')
                ))
            current_event = None
            continue
        if current_event is not None:
            key, value = line.split(":", 1)
            current_event[key] = value

    return ics_arr


def get_monthly_events(event_list, year, month):
    """
    今月にまたがっているイベントだけ抽出する(開始時刻が今月末より前かつ終了時刻が今月頭より後)
    """

    start = datetime.datetime(year, month, 1, 0, 0, 0).timestamp()
    end = datetime.datetime(year, month+1, 1, 0, 0, 0).timestamp(
    ) if month < 12 else datetime.datetime(year+1, 1, 1, 0, 0, 0).timestamp()

    # イベント終了時刻が今月より前のものをフィルタする
    end_at_times = [event.end_at.timestamp() for event in event_list]
    idx = bisect_left(end_at_times, start)
    events_since_this_month = event_list[idx:]

    # イベント開始時刻が今月より後のものをフィルタする
    return [event for event in events_since_this_month if event.start_at.timestamp() < end]
