import os
import sys
import time
import json
from typing import Iterable, List, Dict, Optional

import requests


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chirp.settings")
import django

django.setup()

from users.models import User


VERISAFE_URL = os.getenv("VERISAFE_ACCOUNTS_URL", "https://qaverisafe.opencrafts.io/accounts/all")
VERISAFE_API_KEY = os.getenv("VERISAFE_SERVICE_TOKEN", "=")
PAGE_PARAM = os.getenv("VERISAFE_PAGE_PARAM", "page")


def fetch_page(page: int) -> List[Dict]:
    headers = {"X-Api-Key": VERISAFE_API_KEY}
    params = {PAGE_PARAM: page}
    resp = requests.get(VERISAFE_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "results" in data:
        return data.get("results", [])
    if isinstance(data, list):
        return data
    return []


def iter_all_accounts(limit: Optional[int] = None, start_page: int = 1, max_pages: Optional[int] = None) -> Iterable[Dict]:
    page = start_page
    yielded = 0
    pages_processed = 0

    while True:
        items = fetch_page(page)
        if not items:
            break

        for item in items:
            yield item
            yielded += 1
            if limit is not None and yielded >= limit:
                return

        page += 1
        pages_processed += 1

        if max_pages is not None and pages_processed >= max_pages:
            break

        time.sleep(0.05)


def clear_users_table():
    User._default_manager.all().delete()


def upsert_user(item: Dict):
    user_id = item.get("id")
    email = item.get("email")
    name = item.get("name") or ""
    username = item.get("username")
    avatar_url = item.get("avatar_url")
    vibe_points = item.get("vibe_points") or 0

    user_name = username or (name.strip() if name and name.strip() else (email.split("@")[0] if email else "User"))
    full_name = name.strip() if name else None

    User._default_manager.update_or_create(
        user_id=user_id,
        defaults={
            "user_name": user_name,
            "full_name": full_name,
            "email": email,
            "username": username,
            "avatar_url": avatar_url,
            "vibe_points": int(vibe_points) if isinstance(vibe_points, (int, float, str)) and str(vibe_points).isdigit() else 0,
        },
    )


def sync_users(clear_first: bool = True, limit: Optional[int] = None, start_page: int = 1, max_pages: Optional[int] = None) -> int:
    if clear_first:
        clear_users_table()

    count = 0
    for item in iter_all_accounts(limit=limit, start_page=start_page, max_pages=max_pages):
        try:
            upsert_user(item)
            count += 1
        except Exception as exc:
            print(f"Failed to upsert user {item.get('id')}: {exc}", file=sys.stderr)
    return count


if __name__ == "__main__":
    clear = os.getenv("SYNC_CLEAR_FIRST", "true").lower() in ("1", "true", "yes")
    try:
        limit_env = os.getenv("SYNC_LIMIT")
        limit = int(limit_env) if limit_env else None
    except Exception:
        limit = None
    total = sync_users(clear_first=clear, limit=limit)
    print(json.dumps({"synced": total}))


