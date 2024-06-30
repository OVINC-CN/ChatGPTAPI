import json

import httpx
from django.conf import settings
from django.utils.translation import gettext, gettext_lazy

from apps.chat.tools.base import Tool


class GoogleSearch(Tool):
    name = "GoogleSearch"
    name_alias = gettext_lazy("GoogleSearch")
    desc = "This is a search engine powered by the Google Search API, offering robust online search capabilities."
    desc_alias = gettext_lazy(
        "This is a search engine powered by the Google Search API, offering robust online search capabilities."
    )

    def __init__(self, question: str):
        self.question = question
        super().__init__()

    async def _run(self) -> str:
        client = httpx.AsyncClient(
            http2=True,
            proxy=settings.OPENAI_HTTP_PROXY_URL if settings.OPENAI_HTTP_PROXY_URL else None,
        )
        try:
            resp = await client.get(
                f"https://www.googleapis.com/customsearch/v1"
                f"?key={settings.GOOGLE_SEARCH_API_KEY}"
                f"&cx={settings.GOOGLE_SEARCH_API_CX}"
                f"&q={self.question}"
            )
        finally:
            await client.aclose()
        data = resp.json()
        if not data.get("items", []):
            return gettext("No result found")
        return json.dumps(
            [
                {
                    "title": item["title"],
                    "snippet": item["snippet"],
                    "formattedUrl": item["formattedUrl"],
                }
                for item in data.get("items", [])
            ]
        )

    @classmethod
    def get_properties(cls) -> dict:
        return {
            "question": {
                "type": "string",
                "description": "The question to search for",
            },
        }
