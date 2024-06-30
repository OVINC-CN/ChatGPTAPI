from typing import Dict, Type

from apps.chat.tools.base import Tool
from apps.chat.tools.google_search import GoogleSearch
from apps.chat.tools.web_screenshot import WebScreenshot

TOOLS: Dict[str, Type[Tool]] = {
    GoogleSearch.name: GoogleSearch,
    WebScreenshot.name: WebScreenshot,
}
