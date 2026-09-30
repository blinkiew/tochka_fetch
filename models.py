import keyword
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class Branch(Enum):
    TATISHEVA = 0
    KRUPSKOY = 1

@dataclass
class Schedule:
    branch: Branch
    caption: str
    date: datetime
    attachment_urls: list[str]

    @classmethod
    def from_json(cls, post_json) -> 'Schedule':
        date = datetime.fromtimestamp(post_json.get('date'))

        # detect post branch
        text: str = post_json.get('text')
        if not text:
            raise ValueError("Post doesn't have a caption.")

        if 'татищева' in text.lower():
            branch = Branch.TATISHEVA
        elif any(match in text.lower() for match in ['крупской', 'крупская']):
            branch = Branch.KRUPSKOY
        else:
            raise ValueError(f"Couldn't determine post's branch from caption: {text}.")

        # collect all photo urls
        urls = []
        for attachment in post_json.get('attachments'):
            try:
                urls.append(attachment["photo"]["orig_photo"]["url"])
            except KeyError:
                continue

        if not urls:
            raise ValueError("Post doesn't contain any photo attachments to parse.")

        return cls(
            branch,
            text,
            date,
            urls
        )

@dataclass
class Post:
    caption: str
    photo: bytes

    @classmethod
    def from_schedule(cls, schedule: Schedule, photo_bytes: bytes):
        branch_name = 'Татищева' if schedule.branch == Branch.TATISHEVA else 'Крупской'
        hashtag = '#татищева' if schedule.branch == Branch.TATISHEVA else '#крупской'

        try:
            schedule_date = datetime.strptime(schedule.caption.split()[0], '%d.%m')
        except ValueError:
            schedule_date = schedule.date + timedelta(days=1)

        caption = f"{schedule_date.strftime('%d.%m')} – {branch_name}\n{hashtag}"
        return cls(caption, photo_bytes)
