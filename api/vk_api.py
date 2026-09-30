import httpx

from httpx import NetworkError
from models import Schedule


_API_VERSION = "5.131"

class VKApi:
    """ Wrapper around the VK API """
    def __init__(self, token: str, domain: int) -> None:
        self.token = token
        self.domain = domain

    def _fetch_raw(self, count: int = 5) -> list | None:
        url = "https://api.vk.com/method/wall.get"
        params = {
            "access_token": self.token,
            "v": _API_VERSION,
            "domain": self.domain,
            "count": count
        }

        try:
            response = httpx.get(url, params=params).json()

            if "error" in response:
                print(f"VK API Error: {response['error']['error_msg']}")
                return None

            posts: list = response["response"]["items"]
            return posts

        except NetworkError as e:
            print(f"Network error: error: {e}")

    def fetch_schedules(self) -> list[Schedule]:
        raw_posts = self._fetch_raw()
        if not raw_posts:
            return []

        schedules = []
        for raw_post in raw_posts:
            try:
                schedules.append(Schedule.from_json(raw_post))
            except ValueError:
                continue

        return schedules
