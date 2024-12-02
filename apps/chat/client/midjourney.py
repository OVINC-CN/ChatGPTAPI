import asyncio
import time
import uuid

from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from httpx import AsyncClient
from ovinc_client.core.logger import logger
from rest_framework import status

from apps.chat.client.base import BaseClient
from apps.chat.constants import MidjourneyResult
from apps.chat.exceptions import GenerateFailed, LoadImageFailed
from apps.cos.client import COSClient
from apps.cos.utils import TCloudUrlParser


class MidjourneyClient(BaseClient):
    """
    Midjourney Client
    """

    async def chat(self, *args, **kwargs) -> any:
        client = AsyncClient(
            http2=True,
            headers={"Authorization": f"Bearer {settings.MIDJOURNEY_API_KEY}"},
            base_url=settings.MIDJOURNEY_API_BASE_URL,
            proxy=settings.OPENAI_HTTP_PROXY_URL or None,
        )
        # call midjourney api
        try:
            # submit job
            response = await client.post(
                url=settings.MIDJOURNEY_IMAGINE_API_PATH, json={"prompt": self.messages[-1]["content"]}
            )
            result_id = response.json()["result"]
            # wait for result
            start_time = time.time()
            while time.time() - start_time < settings.MIDJOURNEY_IMAGE_JOB_TIMEOUT:
                result = await client.get(url=settings.MIDJOURNEY_TASK_RESULT_API_PATH.format(id=result_id))
                result_data = result.json()
                # if not finished, continue loop
                if result_data["status"] not in [MidjourneyResult.FAILURE, MidjourneyResult.SUCCESS]:
                    yield ""
                    await asyncio.sleep(settings.MIDJOURNEY_IMAGE_JOB_INTERVAL)
                    continue
                # if failed
                if result_data["status"] == MidjourneyResult.FAILURE:
                    yield str(result_data.get("failReason") or GenerateFailed())
                    break
                # record
                await self.record()
                # use first success picture
                message_url = result_data["imageUrl"]
                image_resp = await client.get(message_url)
                if image_resp.status_code != status.HTTP_200_OK:
                    raise LoadImageFailed()
                url = await COSClient().put_object(
                    file=image_resp.content,
                    file_name=f"{uuid.uuid4().hex}.{image_resp.headers['content-type'].split('/')[-1]}",
                )
                yield f"![output]({TCloudUrlParser(url).url})"
                break
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield str(GenerateFailed())
        finally:
            await client.aclose()

    # pylint: disable=W0221,R1710,W0236
    async def record(self) -> None:
        self.log.completion_tokens = 1
        self.log.completion_token_unit_price = self.model_inst.completion_price
        self.log.finished_at = int(timezone.now().timestamp() * 1000)
        await database_sync_to_async(self.log.save)()
