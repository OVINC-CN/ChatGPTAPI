import hashlib
import json
import os.path
import uuid

import httpx
from django.conf import settings
from django.core.cache import cache
from django_redis.client import DefaultClient
from ovinc_client.core.logger import celery_logger

from apps.cel import app
from apps.cos.client import MoonshotClient
from apps.cos.constants import FILE_CONTENT_CACHE_KEY
from entry.settings import FILE_EXTRACT_CACHE_TIMEOUT

cache: DefaultClient


@app.task(bind=True)
def extract_file(self, file_path: str):
    celery_logger.info("[ExtractFile] Start %s", self.request.id)
    key = FILE_CONTENT_CACHE_KEY.format(file_path_sha256=hashlib.sha256(file_path.encode()).hexdigest())
    # create tmp dir
    tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
    try:
        os.mkdir(path=tmp_dir)
    except FileExistsError:
        pass
    try:
        # download file
        with httpx.Client(http2=True) as client:
            file_content = client.get(url=file_path, timeout=settings.LOAD_FILE_TIMEOUT).content
            celery_logger.info("[ExtractFile] %s Download File Success; File => %s", self.request.id, file_path)
        # save to local path
        local_path = os.path.join(tmp_dir, f"{uuid.uuid1().hex}.{file_path.split('.')[-1]}")
        with open(local_path, "wb+") as file:
            file.write(file_content)
            file.flush()
            # extract
            with MoonshotClient() as moonshot_client:
                # upload file
                file_info = moonshot_client.upload_file(file=file)
                celery_logger.info(
                    "[ExtractFile] %s Upload File; Result => %s",
                    self.request.id,
                    json.dumps(file_info, ensure_ascii=False),
                )
                # extract file
                file_content_info = moonshot_client.extract_file(file_id=file_info["id"])
                # save to cache
                cache.set(key=key, value=file_content_info["content"], timeout=FILE_EXTRACT_CACHE_TIMEOUT)
                celery_logger.info(
                    "[ExtractFile] %s Saved to Cache; Key => %s; File => %s", self.request.id, key, file_path
                )
                # delete file
                moonshot_client.delete_file(file_id=file_info["id"])
                celery_logger.info(
                    "[ExtractFile] %s Delete File Success; FileID => %s", self.request.id, file_info["id"]
                )
        # remove local file
        os.remove(local_path)
    except Exception as err:
        celery_logger.exception(
            "[ExtractFile] %s Extract Failed; File => %s; Error => %s", self.request.id, file_path, err
        )
    celery_logger.info("[ExtractFile] End %s", self.request.id)
