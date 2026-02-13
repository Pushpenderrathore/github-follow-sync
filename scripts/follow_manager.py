import os
import time
import random
import argparse
import requests
from typing import List, Set

GITHUB_API = "https://api.github.com"


class GitHubFollowManager:
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        })

    def check_rate_limit(self):
        r = self.session.get(f"{GITHUB_API}/rate_limit")
        data = r.json()
        remaining = data["rate"]["remaining"]
        reset = data["rate"]["reset"]

        print(f"[INFO] API remaining: {remaining}")

        if remaining < 5:
            wait_time = max(reset - int(time.time()), 0)
            print(f"[WARNING] Rate limit low. Sleeping {wait_time} seconds...")
            time.sleep(wait_time)

    def get_paginated(self, url: str) -> Set[str]:
        users = set()
        page = 1

        while True:
            r = self.session.get(url, params={"per_page": 100, "page": page})
            if r.status_code != 200:
                print(f"[ERROR] Failed to fetch: {r.text}")
                break

            data = r.json()
            if not data:
                break

            for user in data:
                users.add(user["login"])

            page += 1

        return users

    def get_followers(self) -> Set[str]:
        print("[INFO] Fetching followers...")
        return self.get_paginated(f"{GITHUB_API}/user/followers")

    def get_following(self) -> Set[str]:
        print("[INFO] Fetching following...")
        return self.get_paginated(f"{GITHUB_API}/user/following")

    def follow_user(self, username: str):
        r = self.session.put(f"{GITHUB_API}/user/following/{username}")
        return r.status_code == 204

    def unfollow_user(self, username: str):
        r = self.session.delete(f"{GITHUB_API}/user/following/{username}")
        return r.status_code == 204


def main():
    parser = argparse.ArgumentParser(description="Safe GitHub Follow Sync")
    parser.add_argument("--mode", choices=["dry-run", "execute"], default="dry-run")
    parser.add_argument("--max-follows", type=int, default=5)
    parser.add_argument("--max-unfollows", type=int, default=5)

    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("[ERROR] GITHUB_TOKEN not set")
        return

    manager = GitHubFollowManager(token)

    manager.check_rate_limit()

    followers = manager.get_followers()
    following = manager.get_following()

    to_follow = list(followers - following)[:args.max_follows]
    to_unfollow = list(following - followers)[:args.max_unfollows]

    print(f"[INFO] Users to follow: {len(to_follow)}")
    print(f"[INFO] Users to unfollow: {len(to_unfollow)}")

    if args.mode == "dry-run":
        print("[DRY RUN] Would follow:", to_follow)
        print("[DRY RUN] Would unfollow:", to_unfollow)
        return

    for user in to_follow:
        print(f"[ACTION] Following {user}")
        if manager.follow_user(user):
            print(f"[SUCCESS] Followed {user}")
        time.sleep(random.uniform(2, 5))

    for user in to_unfollow:
        print(f"[ACTION] Unfollowing {user}")
        if manager.unfollow_user(user):
            print(f"[SUCCESS] Unfollowed {user}")
        time.sleep(random.uniform(2, 5))


if __name__ == "__main__":
    main()
