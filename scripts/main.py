from itertools import product
from os import getenv
import importlib
import requests
from concurrent.futures import ThreadPoolExecutor
import atexit
import datetime

from event_list import parse_ics
from calendar_image import get_calendar_image
from logger import logger


def download_file(url: str) -> str:
    if url == '':
        return ''
    response = requests.get(url)
    response.raise_for_status()
    return response.text


class FileDisplay:
    width = 800
    height = 400

    def __init__(self, *, shows=True):
        self.shows = shows

    def getbuffer(self, image):
        return image

    def display(self, image_black, image_red):
        Image = importlib.import_module('PIL.Image')
        combined_image = Image.new(
            'RGB', (self.width, self.height,), (255, 255, 255))

        for xy in product(range(self.width), range(self.height)):
            if image_red.getpixel(xy) == 0:
                combined_image.putpixel(xy, (255, 0, 0))
            elif image_black.getpixel(xy) == 0:
                combined_image.putpixel(xy, (0, 0, 0))
        if self.shows:
            combined_image.show()
        return combined_image


def main(is_save_mode=getenv('SAVE', '0') == '1'):
    # 予定一覧と祝日一覧を取得する
    logger.info("fetch event list")
    urls = [
        getenv('CALENDAR_ICS') or '',
        'https://calendar.google.com/calendar/ical/ja.japanese.official%23holiday%40group.v.calendar.google.com/public/basic.ics'
    ]
    with ThreadPoolExecutor() as executor:
        ics_files = [parse_ics(res)
                     for res in list(executor.map(download_file, urls))]
        for file in ics_files:
            file.sort(key=lambda event: event.end_at.timestamp())
        event_list, national_holiday_list = ics_files
        logger.info("finish fetching event list")

    # 画像の出力先を設定 (SAVE=1ならファイルに保存、それ以外ならe-paperに出力する)
    if not is_save_mode:
        epaper = importlib.import_module('epaper')

        logger.info("initialize")
        display = epaper.epaper('epd7in5b_V2').EPD()
        display.init()

        atexit.register(lambda: (logger.info(
            "cleaning up"), display.sleep()))
    else:
        display = FileDisplay()

    # カレンダーを描画する
    image_black, image_red = get_calendar_image(
        display.width, display.height, datetime.datetime.now(),
        event_list, national_holiday_list)

    logger.info("start drawing")
    display.display(display.getbuffer(image_black),
                    display.getbuffer(image_red))


if __name__ == "__main__":
    main()
