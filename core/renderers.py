import json

from rest_framework.renderers import BaseRenderer
from rest_framework.settings import api_settings
from rest_framework.utils import encoders


class APIRenderer(BaseRenderer):
    """
    Return Restful Body
    """

    media_type = "application/json"
    format = "json"
    encoder_class = encoders.JSONEncoder
    ensure_ascii = not api_settings.UNICODE_JSON

    def render(self, data, accepted_media_type=None, renderer_context=None) -> str:
        request = renderer_context.get("request")
        response = {
            "message": "success",
            "data": None,
            "trace": getattr(request, "otel_trace_id"),
        }
        if isinstance(data, dict):
            if "message" in data:
                response["message"] = data.pop("message")
            if "data" in data:
                response["data"] = data["data"]
            else:
                response["data"] = data
        else:
            response["data"] = data
        return json.dumps(response, ensure_ascii=self.ensure_ascii)
