import json
import os.path
import uuid

import httpx
from django.conf import settings
from ovinc_client.core.logger import celery_logger
from rest_framework import status

from apps.cel import app
from apps.cos.client import MoonshotClient
from apps.cos.exceptions import ExtractFailed
from apps.cos.models import FileExtractInfo
from apps.cos.utils import TCloudUrlParser


@app.task(bind=True)
def extract_file(self, key: str):
    celery_logger.info("[ExtractFile] Start %s", self.request.id)
    # load file
    try:
        file_extract_info = FileExtractInfo.objects.get(key=key)
    except FileExtractInfo.DoesNotExist:  # pylint: disable=E1101
        celery_logger.exception("[ExtractFile] %s Extract Failed; File Not Found => %s", self.request.id, key)
        return
    # check finished
    if file_extract_info.is_finished:
        celery_logger.info("[ExtractFile] %s Skipped %s", self.request.id, key)
        return
    # sign file path
    file_path = TCloudUrlParser(file_extract_info.file_path).url
    # extract file
    try:
        # download file
        with httpx.Client(http2=True) as client:
            resp = client.get(url=file_path, timeout=settings.LOAD_FILE_TIMEOUT)
            if resp.status_code == status.HTTP_200_OK:
                file_content = resp.content
                celery_logger.info("[ExtractFile] %s Download Success; File => %s", self.request.id, key)
            else:
                raise httpx.HTTPError(message=f"Invalid Request With Code: {resp.status_code}; Content: {resp.content}")
        # save to local path
        tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
        local_path = os.path.join(tmp_dir, f"{uuid.uuid1().hex}.{file_extract_info.file_path.split('.')[-1]}")
        with open(local_path, "wb+") as file:
            file.write(file_content)
            file.flush()
            # extract
            with MoonshotClient() as moonshot_client:
                # upload file
                file_info = moonshot_client.upload_file(file=file)
                if "id" not in file_info:
                    raise ExtractFailed(detail=json.dumps(file_info, ensure_ascii=False))
                file_extract_info.upload_info = file_info
                celery_logger.info("[ExtractFile] %s Upload Finished; File => %s", self.request.id, key)
                # extract file
                extract_info = moonshot_client.extract_file(file_id=file_info["id"])
                if "content" not in extract_info:
                    raise ExtractFailed(detail=json.dumps(extract_info, ensure_ascii=False))
                file_extract_info.extract_info = extract_info
                file_extract_info.is_success = True
                file_extract_info.is_finished = True
                celery_logger.info("[ExtractFile] %s Extract Finished; File => %s", self.request.id, key)
                # delete file
                moonshot_client.delete_file(file_id=file_info["id"])
                celery_logger.info("[ExtractFile] %s Delete Success; FileID => %s", self.request.id, file_info["id"])
        # remove local file
        os.remove(local_path)
        celery_logger.info("[ExtractFile] %s Delete Local Success; File => %s", self.request.id, key)
    except Exception as err:  # pylint: disable=W0718
        celery_logger.exception("[ExtractFile] %s Extract Failed; File => %s; Error => %s", self.request.id, key, err)
        # only update when not finished
        if not file_extract_info.is_finished:
            file_extract_info.is_success = False
            file_extract_info.is_finished = True
    finally:
        file_extract_info.save()
    celery_logger.info("[ExtractFile] End %s", self.request.id)
