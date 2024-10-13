import datetime
from datetime import timedelta
from PIL import Image, ImageFont, ImageDraw
from os import path
import math
from event_list import get_monthly_events

picdir = path.join(path.dirname(path.dirname(path.realpath(__file__))), 'pic')
font_path = path.join(picdir, 'font.ttf')

if path.exists(font_path):
    font10 = ImageFont.truetype(font_path, 10)
    font12 = ImageFont.truetype(font_path, 12)
    font14 = ImageFont.truetype(font_path, 14)
    font16 = ImageFont.truetype(font_path, 16)
else:
    font10 = ImageFont.load_default(10)
    font12 = ImageFont.load_default(12)
    font14 = ImageFont.load_default(14)
    font16 = ImageFont.load_default(16)


# 白黒赤の3色の画像
class TriColorImage:
    def __init__(self, width, height):
        self.Black = Image.new('1', (width, height), 255)
        self.Red = Image.new('1', (width, height), 255)
        self.image_black = ImageDraw.Draw(self.Black)
        self.image_red = ImageDraw.Draw(self.Red)

    def draw(self, method_name, *args, color, **kwargs):
        if color == "black":
            method = getattr(self.image_black, method_name)
        elif color == "red":
            method = getattr(self.image_red, method_name)
        method(*args, **kwargs)

    def circle(self, xy, rad, fill=None, outline=None, width=1, color="black"):
        self.pieslice((xy[0]-rad, xy[1]-rad, xy[0]+rad, xy[1] + rad),
                      0, 360, fill=fill, outline=outline,
                      width=width, color=color)


# 各メソッドにcolor引数を追加
for method_name in ['text', 'line', 'rectangle', 'arc', 'pieslice', 'chord', 'rounded_rectangle']:
    def draw(method_name):
        return lambda self, *args, color="black", **kwargs: getattr(
            self.image_black if color == "black" else self.image_red,
            method_name
        )(*args, **kwargs)

    setattr(TriColorImage, method_name, draw(method_name))


def get_calendar_list(today):
    """
    今日から1週間前〜3週間後までの日付をdateのリストで取得する
    """
    last_sunday = today - timedelta(days=7+((today.weekday()+1) % 7))
    return [last_sunday + timedelta(days=i) for i in range(7 * 6)]


def is_same_week(date1, date2):
    first_day_in_week1 = date1 - timedelta(days=(date1.weekday()+1) % 7)
    first_day_in_week2 = date2 - timedelta(days=(date2.weekday()+1) % 7)
    return first_day_in_week1 == first_day_in_week2


fg = 0  # 前景色で塗る
bg = 1  # 背景色(=白)で塗る


def truncate_string(s, maxCount):
    count = 0
    result = []
    for char in s:
        if 'a' <= char <= 'z' or 'A' <= char <= 'Z' or '0' <= char <= '9':
            count += 1
        else:
            count += 2
        if count > maxCount:
            return ''.join(result)
        result.append(char)
    return ''.join(result)


month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
               'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
weekday_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']


def get_calendar_image(width, height, now, event_list, national_holiday_list):
    today = now.date()
    cell_width = width / 7
    cell_height = (height - 15) / 5  # 6周目も日付まで表示したいので、6周目の高さ(10px)を確保する
    drawer = TriColorImage(width, math.trunc(cell_height * 6))

    # あらかじめ先月、今月、来月の予定だけをフィルタリングしておく
    event_list_dic = [None] * 13
    event_list_dic[(today.month+10) % 12 + 1] = get_monthly_events(
        event_list, today.year, today.month-1
    ) if today.month - 1 >= 1 else get_monthly_events(event_list, today.year-1, 12)
    event_list_dic[today.month] = get_monthly_events(
        event_list, today.year, today.month)
    event_list_dic[today.month % 12 + 1] = get_monthly_events(
        event_list, today.year, today.month + 1
    ) if today.month + 1 <= 12 else get_monthly_events(event_list, today.year+1, 1)
    event_list_dic[today.month % 12 + 2] = get_monthly_events(
        event_list, today.year, today.month + 2
    ) if today.month + 2 <= 12 else get_monthly_events(event_list, today.year+1, today.month + 2 - 12)

    # 各日の予定をあらかじめ計算しておく
    calendarList = get_calendar_list(today)
    event_queue = []
    date_event_map = {}
    for i, date in enumerate(calendarList):
        date_datetime = datetime.datetime.combine(
            date, datetime.datetime.min.time()
        ).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

        holidays = [
            holiday for holiday in national_holiday_list
            if holiday.start_at < date_datetime + timedelta(days=1) and
            date_datetime < holiday.end_at]

        # 1. 今日がスタートのものを空いてるとこに積む
        events_started_at_date = [
            event for event in (event_list_dic[date.month]) + holidays
            if date_datetime <= event.start_at < date_datetime + timedelta(days=1)
        ]
        events_started_at_date.sort(
            key=lambda event: (
                event.end_at - event.start_at >= timedelta(days=1),
                (-1 if event.end_at - event.start_at <=
                 timedelta(days=1) else 1) * event.end_at.timestamp()
            ), reverse=True)
        # Noneがある最初の位置を見つけて、その位置に値を挿入、Noneが見つからなければ末尾に値を追加
        for event in events_started_at_date:
            try:
                index = event_queue.index(None)
                event_queue[index] = [event, False]
            except ValueError:
                event_queue.append([event, False])

        # 予定(高さの関係で3件に絞っている)
        if len(event_queue) > 3:
            for i in range(2, len(event_queue) - 1):
                if event_queue[i] is not None:
                    event_queue[i][1] = True

        date_event_map[date] = list(event_queue)
        # 1. 今日が終わりのものを外す
        event_queue = [
            None if event is None or (date_datetime <= event[0].end_at <= date_datetime + timedelta(days=1))
            else event for event in event_queue]
        while event_queue and event_queue[-1] is None:
            event_queue.pop()

    # 日付、枠、予定を描画
    calendarList = get_calendar_list(today)
    for i, date in enumerate(calendarList):
        cell_left = cell_width * (i % 7)
        cell_top = cell_height * math.trunc(i / 7)
        date_datetime = datetime.datetime.combine(
            date, datetime.datetime.min.time()
        ).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        events = date_event_map[date]

        # 月の境界線を描画
        if (date - datetime.timedelta(weeks=1)).month != date.month:
            drawer.line(
                (cell_left - 1, cell_top - 1, cell_left +
                 cell_width - 1, cell_top - 1),
                fill=fg)
        if date.day == 1:
            drawer.line(
                (cell_left - 1, cell_top - 1,
                 cell_left - 1, cell_top + cell_height - 1),
                fill=fg)

        holidays = [
            holiday for holiday in national_holiday_list
            if holiday.start_at < date_datetime + timedelta(days=1) and
            date_datetime < holiday.end_at]
        paid_leave = [event[0] for event in events
                      if event is not None and event[0].title == "有給"]
        is_holiday = date.weekday() == 6 or len(holidays + paid_leave) > 0

        # 日付を描画
        color = "red" if is_holiday else "black"  # 休日は赤色
        # 今日だった場合は丸で囲み、それ以外のときは普通に日付を表示する
        if date == today:
            xy = (cell_left + cell_width / 2, cell_top + 10)
            drawer.circle(xy, 10, fill=fg, color=color)
            drawer.text(xy, str(date.day), font=font14,
                        fill=bg, anchor='mm', color=color)
        else:
            drawer.text(
                (cell_left + cell_width / 2, cell_top + 10),
                str(date.day), font=font14, fill=fg, anchor='mm', color=color)
        # 今週の行に曜日を表示
        if is_same_week(date, today):
            drawer.text(
                (cell_left + cell_width - 20, cell_top + 10),
                weekday_names[(date.weekday()+1) % 7], font=font10, fill=fg,
                anchor='rm', color=color)
        # 1日に月名を表示
        if date.day == 1:
            drawer.text(
                (cell_left + 4, cell_top + 4),
                month_names[date.month-1],
                font=font12, fill=fg, anchor='lt', color=color)

        # 予定を描画(高さの関係で3件に絞っている)
        rect_height = 16
        for i, q in enumerate(events[:3]):
            top = cell_top + 20 + (rect_height + 4) * i

            # 省略された部分
            if i == 2 and len(events) > 3 or q is not None and q[1]:
                drawer.text(
                    (cell_left + 2, top + rect_height / 2),
                    f'他{len([e for e in events[2:] if e is not None])}件',
                    font=font16, fill=fg, anchor='lm')
                continue
            if q is None:
                continue

            event, is_omitted = q
            # 祝日
            if event in holidays or event in paid_leave:
                drawer.text(
                    (cell_left + 2, top + rect_height / 2),
                    truncate_string(event.title, 14),
                    font=font16, fill=fg, anchor='lm', color=color)
                continue
            # 1日で終わるイベント
            if event.end_at - event.start_at < timedelta(days=1):
                drawer.text(
                    (cell_left + 2, top + rect_height / 2),
                    truncate_string(event.title, 14),
                    font=font16, fill=fg, anchor='lm')
                continue

            is_start_date = date_datetime <= event.start_at
            is_end_date = event.end_at <= date_datetime + timedelta(days=1)
            drawer.rounded_rectangle(
                (cell_left + (1 if is_start_date else 0), top,
                 cell_left + cell_width - (1 if is_end_date else 0), top + rect_height),
                2, corners=(is_start_date, is_end_date,
                            is_end_date, is_start_date),
                fill=fg)

            # 予定テキストを描画
            if is_start_date or date.weekday() == 6:
                drawer.text(
                    (cell_left + 2, top + rect_height / 2),
                    truncate_string(event.title, 14),
                    font=font16, fill=bg, anchor='lm')

    margin = 4

    # 画面の更新時刻を表示
    drawer.rectangle(
        (width-cell_width, cell_height*5, width, cell_height*6),
        fill=bg)
    drawer.text((width, height+margin), now.strftime('%H:%M') + '更新',
                font=font12, fill=0, anchor='rb')
    return (drawer.Black.crop((0, margin, width, height+margin)),
            drawer.Red.crop((0, margin, width, height+margin)))
