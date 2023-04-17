import json
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import openai

with open('settings.json', mode="r", encoding="utf-8") as f:
    settings_dict = json.load(f)

MAX_ATTEMPT = settings_dict["retry"]["max_attempt_number"] # リトライ回数
MIN_SECONDS = settings_dict["retry"]["min_wait_seconds"] # 最小リトライ秒数
MAX_SECONDS = settings_dict["retry"]["max_wait_seconds"] # 最大リトライ秒数

def retry_decorator(func):
    return retry(
        #reraise=True,
        stop=stop_after_attempt(MAX_ATTEMPT),
        wait=wait_exponential(multiplier=1, min=MIN_SECONDS, max=MAX_SECONDS),
        retry=(
            retry_if_exception_type(openai.error.APIError)
            | retry_if_exception_type(openai.error.Timeout)
            | retry_if_exception_type(openai.error.RateLimitError)
            | retry_if_exception_type(openai.error.APIConnectionError)
            | retry_if_exception_type(openai.error.InvalidRequestError)
            | retry_if_exception_type(openai.error.AuthenticationError)
            | retry_if_exception_type(openai.error.ServiceUnavailableError)
        )
    )(func)