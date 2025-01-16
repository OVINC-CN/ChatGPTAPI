class PrometheusMetrics:
    WAIT_FOR_PROCESS = "wait_process"
    WAIT_FIRST_LETTER = "first_letter"
    TOKEN_PER_SECOND = "token_per_second"
    WEBSOCKET_CONN = "websocket_conn"
    PROMPT_TOKEN = "prompt_token"
    COMPLETION_TOKEN = "completion_token"


class PrometheusLabels:
    MODEL_NAME = "model_name"
    HOSTNAME = "hostname"
