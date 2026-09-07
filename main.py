import asyncio
import json
import os.path
import time

import httpx
import img_ocr

from dotenv import load_dotenv
from io import BytesIO
from os import getenv
from PIL import Image

from channel_bot import TelegramBot
from models import Branch, Schedule, TelegramPost

load_dotenv()

TOKEN = getenv("VK_TOKEN")
DOMAIN = int(getenv("DOMAIN") or 0)
API_VERSION = "5.131"

dates_path = 'dates.json'
latest_dates = {}

bot = TelegramBot()


def fetch_raw_posts(count: int = 5) -> list | None:
    url = "https://api.vk.com/method/wall.get"
    params = {
        "access_token": TOKEN,
        "v": API_VERSION,
        "domain": DOMAIN,
        "count": count
    }

    try:
        response = httpx.get(url, params=params).json()

        if "error" in response:
            print(f"VK API Error: {response['error']['error_msg']}")
            return None

        posts: list = response["response"]["items"]
        return posts

    except Exception as e:
        print(f"Request error: {e}")


def fetch_schedules(raw_posts) -> list[Schedule] | None:
    if not raw_posts:
        return None

    schedules = []
    for raw_post in raw_posts:
        try:
            schedules.append(Schedule.from_json(raw_post))
        except ValueError:
            continue

    return schedules


def check_new(schedules: list[Schedule]) -> list[Schedule]:
    global latest_dates
    new_schedules = []

    for schedule in schedules:
        latest_date = latest_dates.get(str(schedule.branch.value))
        if latest_date and schedule.date.timestamp() <= latest_date:
            continue

        # find target attachment
        found_target = False
        for url in schedule.attachment_urls:
            try:
                # download image
                response = httpx.get(url)
                response.raise_for_status()

                image_bytes = BytesIO(response.content)
                img = Image.open(image_bytes)

                # ocr image
                img_text = img_ocr.ocr(img)
                is_valid = img_ocr.is_target(img_text, schedule.branch)
                if not is_valid:
                    continue

                # save image
                img.save(f"{schedule.branch.value}.png")

                latest_dates[str(schedule.branch.value)] = schedule.date.timestamp()
                save_dates()

                new_schedules.append(schedule)
                found_target = True

            except KeyError, httpx.HTTPStatusError, httpx.ConnectTimeout:
                continue

        if not found_target:
            # TODO: send me an update that post is found but attachment is not recognized
            print(f"Target post attachment is not recognized. Caption: {schedule.caption}, Branch: {schedule.branch}")

    save_dates()
    return new_schedules


def load_dates():
    global latest_dates
    if not os.path.exists(dates_path):
        with open(dates_path, 'w') as file:
            file.write('{}')
            file.close()
        latest_dates = {}
        return

    with open(dates_path, encoding="utf-8") as file:
        latest_dates = json.load(file)

def save_dates():
    with open(dates_path, 'w', encoding="utf-8") as file:
        json.dump(latest_dates, file)


SLEEP = 90  # 1.5 mins

async def main():
    load_dates()

    while True:
        await check_posts()
        print(f"Waiting {SLEEP} seconds for the next check.")
        time.sleep(SLEEP)


async def check_posts():
    # fetch raw posts using vk api
    posts_raw = fetch_raw_posts()
    if not posts_raw:
        print("No posts fetched. Unexpected.")
        return

    schedules = fetch_schedules(posts_raw)
    if not schedules:
        print("No schedules parsed.")
        return

    # process raw posts and check for new schedule
    new_schedules = check_new(schedules)
    if not new_schedules:
        print(f"No new posts.")
        return

    # post new schedule(s) to telegram
    for schedule in new_schedules:
        post = TelegramPost.from_schedule(schedule)

        await bot.send_schedule(
            f"{schedule.branch.value}.png",
            post
        )

        print(f"Schedule sent successfully. Branch: {schedule.branch}")


if __name__ == '__main__':
    asyncio.run(main())
