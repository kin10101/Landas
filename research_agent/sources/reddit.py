import os
from typing import List
from datetime import datetime
from .base import BaseSource
from models import SourceData

try:
    import praw
except ImportError:
    praw = None


class RedditSource(BaseSource):
    """Fetch discussions from Reddit using PRAW"""

    def __init__(self, enabled: bool = True, limit: int = 20):
        super().__init__("Reddit", enabled)
        self.limit = limit
        self.subreddits = [
            "MachineLearning",
            "datascience",
            "learnprogramming",
            "Python",
        ]
        self.reddit = None

    def _init_reddit(self):
        """Initialize PRAW client"""
        if not praw:
            raise ImportError("praw is required for Reddit source")

        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv(
                    "REDDIT_USER_AGENT", "Landas/1.0 (+http://localhost)"
                ),
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Reddit client: {str(e)}")

    async def fetch(self) -> List[SourceData]:
        """Fetch posts from Reddit subreddits"""
        if not self.enabled:
            return []

        try:
            if not self.reddit:
                self._init_reddit()

            for subreddit_name in self.subreddits:
                subreddit = self.reddit.subreddit(subreddit_name)

                for post in subreddit.hot(limit=self.limit):
                    if post.stickied:
                        continue

                    source_data = SourceData(
                        title=post.title,
                        description=post.selftext[:500] if post.selftext else "",
                        url=f"https://reddit.com{post.permalink}",
                        source="Reddit",
                        timestamp=datetime.fromtimestamp(post.created_utc),
                        raw_data={
                            "subreddit": subreddit_name,
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "author": str(post.author),
                        },
                    )
                    self.data.append(source_data)

            print(f"[+] Reddit: Fetched {len(self.data)} posts")
            return self.data

        except Exception as e:
            print(f"[!] Reddit Error: {str(e)}")
            print(
                "  Note: Ensure REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are set in .env"
            )
            return []
