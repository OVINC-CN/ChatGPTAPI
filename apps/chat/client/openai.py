from httpx import Client

from apps.chat.client.base import OpenAIBaseClient


class OpenAIClient(OpenAIBaseClient):
    """
    OpenAI Client
    """

    @property
    def api_key(self) -> str:
        return self.model_settings.get("api_key")

    @property
    def base_url(self) -> str:
        return self.model_settings.get("base_url")

    @property
    def http_client(self) -> Client | None:
        proxy = self.model_settings.get("proxy")
        if proxy:
            return Client(proxy=proxy)
        return None

    @property
    def timeout(self) -> int:
        return self.model_settings.get("timeout", super().timeout)

    @property
    def api_model(self) -> str:
        return self.model_settings.get("api_model", super().api_model)

    @property
    def extra_headers(self) -> dict[str, str]:
        return self.model_settings.get("extra_headers", super().extra_headers)

    @property
    def extra_query(self) -> dict | None:
        return self.model_settings.get("extra_query", super().extra_query)

    @property
    def extra_body(self) -> dict | None:
        return self.model_settings.get("extra_body", super().extra_body)

    @property
    def extra_chat_params(self) -> dict[str, any]:
        return self.model_settings.get("extra_chat_params", super().extra_chat_params)

    @property
    def use_stream(self) -> bool:
        return self.model_settings.get("use_stream", super().use_stream)

    @property
    def thinking_key(self) -> str:
        return self.model_settings.get("thinking_key", super().thinking_key)
