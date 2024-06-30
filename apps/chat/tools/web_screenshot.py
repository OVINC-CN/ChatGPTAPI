import asyncio
import math
import os
import uuid

from django.conf import settings
from django.utils.translation import gettext, gettext_lazy
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from apps.chat.tools.base import Tool
from apps.cos.client import COSClient


class WebScreenshot(Tool):
    """
    Website Screenshot Tool
    """

    name = "WebScreenshot"
    name_alias = gettext_lazy("WebScreenshot")
    desc = (
        "This tool provides comprehensive website screenshot capabilities, "
        "allowing users to capture high-quality images of web pages."
    )
    desc_alias = gettext_lazy(
        "This tool provides comprehensive website screenshot capabilities, "
        "allowing users to capture high-quality images of web pages."
    )

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.max_scroll_times = settings.WEB_SCREENSHOT_MAX_SCROLL_TIMES
        self.service = Service(executable_path=settings.WEB_SCREENSHOT_CHROME_DRIVER_PATH)
        self.options = webdriver.ChromeOptions()
        for arg in ("--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"):
            self.options.add_argument(arg)
        self.window_width = settings.WEB_SCREENSHOT_WINDOW_WIDTH
        self.window_height = settings.WEB_SCREENSHOT_WINDOW_HEIGHT
        self.timeout = settings.WEB_SCREENSHOT_TIMEOUT

    def get_driver(self) -> webdriver.Chrome:
        driver = webdriver.Chrome(service=self.service, options=self.options)
        driver.set_window_size(width=self.window_width, height=self.window_height)
        return driver

    async def _run(self) -> str:
        # init config
        file_id = str(uuid.uuid1().hex)
        # Init Storage
        storage_path = os.path.join(settings.BASE_DIR, f"tmp/{file_id}/")
        os.mkdir(storage_path)
        # Do Screenshot
        screenshots = []
        with self.get_driver() as driver:
            # Open URL
            driver.get(self.url)
            # Wait for loading
            await asyncio.sleep(self.timeout)
            # Set page size
            page_height = driver.execute_script("return document.documentElement.scrollHeight")
            # scroll and screenshot
            scroll_times = (
                math.ceil(page_height / self.window_height) if self.max_scroll_times <= 0 else self.max_scroll_times
            )
            for index in range(scroll_times):
                screenshot_path = os.path.join(storage_path, f"{index + 1}.png")
                driver.save_screenshot(screenshot_path)
                screenshots.append(screenshot_path)
                driver.execute_script(f"window.scrollBy(0, {self.window_height})")
            # crop last image
            if len(screenshots) > 1:
                last_img_height = page_height % self.window_height
                self.crop_image(screenshots[-1], screenshots[-1], last_img_height)
        # concat images
        full_screenshot_path = os.path.join(storage_path, f"{file_id}.png")
        self.vertically_concatenate(screenshots, full_screenshot_path)
        # upload image
        with open(full_screenshot_path, "rb") as f:
            url = await COSClient().put_object(file=f, file_name=f"{file_id}.png")
            return gettext("The screenshot is saved to this url: %s") % f"{url}?{settings.WEB_SCREENSHOT_STYLE}"

    def crop_image(self, input_path: str, output_path: str, new_height: int) -> None:
        image = Image.open(input_path)
        width, height = image.size
        cropped_image = image.crop((0, new_height, width, height))
        cropped_image.save(output_path)

    def vertically_concatenate(self, images, output_path):
        open_images = [Image.open(img_path) for img_path in images]
        widths, heights = zip(*(img.size for img in open_images))
        total_width = max(widths)
        total_height = sum(heights)
        new_image = Image.new("RGB", (total_width, total_height))
        y_offset = 0
        for img in open_images:
            new_image.paste(img, (0, y_offset))
            y_offset += img.size[1]
        new_image.save(output_path)

    @classmethod
    def get_properties(cls) -> dict:
        return {
            "url": {
                "type": "string",
                "description": "The website url which needs screenshot",
            }
        }
