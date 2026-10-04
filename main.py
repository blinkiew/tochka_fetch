import asyncio
import json
import os.path

import httpx
from dotenv import load_dotenv
from os import getenv

from api.gemini_api import GeminiAPI, GeminiResponseError
from api.tg_api import TelegramAPI
from api.vk_api import VKApi
from models import Post, Schedule

load_dotenv()

VK_TOKEN = getenv("VK_TOKEN")
VK_DOMAIN = getenv("VK_DOMAIN") or getenv("DOMAIN")
TG_TOKEN = getenv("BOT_TOKEN")
CHANNEL_ID = getenv("CHANNEL_ID")
GEMINI_API_KEY = getenv("GEMINI_API_KEY") or getenv("GOOGLE_API_KEY")
DATES_PATH = getenv("DATES_PATH", "dates.json")


def collect_attachments(schedule: Schedule) -> list[bytes]:
    attachments = []
    for url in schedule.attachment_urls:
        try:
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            attachments.append(response.content)
        except httpx.RequestError as e:
            print(f"Skipping attachment, branch: {schedule.branch}, url: {url}; Error: {e}")
            continue
        except httpx.HTTPStatusError as e:
            print(f"Skipping schedule, branch: {schedule.branch}, url: {url}; Error: {e}")
            continue

    return attachments


def load_dates():
    data_dir = os.path.dirname(DATES_PATH)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    if not os.path.exists(DATES_PATH):
        with open(DATES_PATH, "w", encoding="utf-8") as file:
            json.dump({}, file)
        return {}

    with open(DATES_PATH, encoding="utf-8") as file:
        dates = json.load(file)
    if not isinstance(dates, dict):
        raise ValueError(f"{DATES_PATH} must contain a JSON object.")
    return dates


def save_dates(dates: dict):
    data_dir = os.path.dirname(DATES_PATH)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    with open(DATES_PATH, "w", encoding="utf-8") as file:
        json.dump(dates, file)


SLEEP = 90  # 1.5 mins


async def main():
    required_variables = {
        "VK_TOKEN": VK_TOKEN,
        "VK_DOMAIN": VK_DOMAIN,
        "BOT_TOKEN": TG_TOKEN,
        "CHANNEL_ID": CHANNEL_ID,
        "GEMINI_API_KEY (or GOOGLE_API_KEY)": GEMINI_API_KEY,
    }
    missing_variables = [name for name, value in required_variables.items() if not value]
    if missing_variables:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_variables)}")

    try:
        domain = int(VK_DOMAIN)
    except ValueError as error:
        raise ValueError("VK_DOMAIN must be an integer community ID, usually negative.") from error

    latest_dates = load_dates()

    vk_api = VKApi(VK_TOKEN, domain)
    gemini_api = GeminiAPI()
    tg_api = TelegramAPI(TG_TOKEN, CHANNEL_ID)

    while True:
        print("Checking for new posts...")
        await check_posts(latest_dates, vk_api, gemini_api, tg_api)
        print(f"Waiting for {SLEEP} seconds before the next check.")
        await asyncio.sleep(SLEEP)


async def check_posts(
    latest_dates: dict,
    vk_api: VKApi,
    gemini_api: GeminiAPI,
    tg_api: TelegramAPI,
):
    schedules = vk_api.fetch_schedules()
    if not schedules:
        print("No schedules parsed.")
        return

    # check for new schedules
    new_schedules = []
    for schedule in schedules:
        branch_key = str(schedule.branch.value)
        latest_date = latest_dates.get(branch_key, 0)

        if schedule.date.timestamp() <= latest_date:
            continue

        print(f"Found schedule, branch: {schedule.branch}, date: {schedule.date.strftime('%Y-%m-%d')}")
        new_schedules.append(schedule)

    if not new_schedules:
        print("No new posts.")
        return

    for schedule in new_schedules:
        attachments = collect_attachments(schedule)
        if not attachments:
            print(f"No attachments could be downloaded. Branch: {schedule.branch}")
            continue

        try:
            match = gemini_api.find_target_schedule(attachments)
        except GeminiResponseError as error:
            print(f"Could not identify schedule image for branch {schedule.branch}: {error}")
            continue
        print(f"Gemini found match: attachment with index {match.target_image_index} for branch {schedule.branch},"
              f"date: {schedule.date.strftime('%Y-%m-%d')}")

        if not 0 <= match.target_image_index < len(attachments):
            raise ValueError(
                f"Gemini returned invalid image index {match.target_image_index} "
                f"for {len(attachments)} attachments."
            )

        attachment = attachments[match.target_image_index]
        post = Post.from_schedule(schedule, attachment)
        await tg_api.send_schedule(post)
        print(f"Schedule sent successfully. Branch: {schedule.branch}")

        branch_key = str(schedule.branch.value)
        latest_dates[branch_key] = max(
            schedule.date.timestamp(),
            latest_dates.get(branch_key, 0),
        )
        save_dates(latest_dates)


if __name__ == '__main__':
    asyncio.run(main())
