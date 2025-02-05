import time
import uuid

from httpx import Client
from opentelemetry.trace import SpanKind
from ovinc_client.core.logger import logger
from rest_framework import status

from apps.chat.client.base import BaseClient
from apps.chat.constants import MidjourneyResult, SpanType
from apps.chat.exceptions import GenerateFailed, LoadImageFailed
from apps.chat.utils import format_error, format_response
from apps.cos.client import COSClient
from apps.cos.utils import TCloudUrlParser


class MidjourneyClient(BaseClient):
    """
    Midjourney Client
    """

    def _chat(self, *args, **kwargs) -> any:
        client = Client(
            http2=True,
            headers={"Authorization": f"Bearer {self.model_settings.get("api_key")}"},
            base_url=self.model_settings.get("base_url"),
            proxy=self.model_settings.get("proxy"),
            timeout=self.model_settings.get("timeout"),
        )
        # call midjourney api
        try:
            with self.start_span(SpanType.API, SpanKind.CLIENT):
                # submit job
                response = client.post(
                    url=self.model_settings.get("imaging_path"), json={"prompt": self.messages[-1].content}
                )
            result_id = response.json()["result"]
            # wait for result
            start_time = time.time()
            while time.time() - start_time < self.model_settings.get("wait_timeout", 600):
                result = client.get(url=self.model_settings.get("result_path").format(id=result_id))
                result_data = result.json()
                # if not finished, continue loop
                if result_data["status"] not in [MidjourneyResult.FAILURE, MidjourneyResult.SUCCESS]:
                    yield format_response(log_id=self.log.id, data="")
                    time.sleep(self.model_settings.get("no_result_sleep", 5))
                    continue
                # if failed
                if result_data["status"] == MidjourneyResult.FAILURE:
                    yield format_error(log_id=self.log.id, error=GenerateFailed(result_data.get("failReason") or None))
                    self.record()
                    break
                with self.start_span(SpanType.CHUNK, SpanKind.SERVER):
                    # record
                    self.record(completion_tokens=1)
                    # use first success picture
                    message_url = result_data["imageUrl"]
                    image_resp = client.get(message_url)
                    if image_resp.status_code != status.HTTP_200_OK:
                        raise LoadImageFailed()
                    url = COSClient().put_object(
                        file=image_resp.content,
                        file_name=f"{uuid.uuid4().hex}.{image_resp.headers['content-type'].split('/')[-1]}",
                    )
                    yield format_response(log_id=self.log.id, data=f"![output]({TCloudUrlParser(url).url})")
                break
        except Exception as err:  # pylint: disable=W0718
            logger.exception("[GenerateContentFailed] %s", err)
            yield format_error(log_id=self.log.id, error=err)
            self.record()
        finally:
            client.close()
