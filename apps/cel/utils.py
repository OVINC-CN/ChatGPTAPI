import time
from functools import wraps

from django.core.cache import cache
from ovinc_client.core.logger import logger

from apps.cel.constants import CELERY_RETRY_SLEEP


class LockKey:
    """
    Lock Key
    """

    _key_prefix = "task-lock"
    timeout = 24 * 60 * 60

    def __init__(self, func: callable, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @property
    def _key(self):
        """
        cache key
        """

        return self.func.__name__

    @property
    def key(self):
        """
        cache key
        """

        return f"{self._key_prefix}:{self._key}"


class TaskLock:
    def __init__(self, func: callable, lock_key: LockKey.__class__ = LockKey, retry: bool = False, *args, **kwargs):
        self.func = func
        self.lock_key = lock_key(func, *args, **kwargs)
        self.retry = retry
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        """
        run task or skip
        """

        # check status
        if not self.set_status():
            logger.warning("[TaskLockExecuteTask] Duplicate => %s", self.func)
            if self.retry:
                self.retry_task()
            return

        # run task
        try:
            logger.debug(
                "[TaskLockExecuteTask] Task => %s; LockKey => %s; Args => %s; Kwargs => %s",
                self.func,
                self.lock_key,
                self.args,
                self.kwargs,
            )
            return self.func(*self.args, **self.kwargs)
        except Exception as err:
            raise err
        # clean status
        finally:
            self.clean_status()

    def retry_task(self):
        result = self.args[0].delay(*self.args[1:], **self.kwargs)
        time.sleep(CELERY_RETRY_SLEEP)
        logger.info("[TaskLockExecuteTask] Retry => %s; Result => %s", self.func, result)

    @property
    def cache_key(self) -> str:
        """
        lock key and timeout
        """

        return self.lock_key.key

    @property
    def cache_timeout(self) -> int:
        """
        lick timeout
        """

        return self.lock_key.timeout

    def set_status(self) -> bool:
        """
        set running
        """

        return cache.set(self.cache_key, True, timeout=self.cache_timeout, nx=True)

    def clean_status(self) -> None:
        """
        set running finished
        """

        cache.delete(self.cache_key)


def task_lock(func: callable = None, lock_key: LockKey.__class__ = LockKey, retry: bool = False):
    """
    wait task finished
    """

    @wraps(func)
    def wrapper(task: callable):
        @wraps(task)
        def warp_func(*args, **kwargs):
            TaskLock(task, lock_key, retry, *args, **kwargs)()

        return warp_func

    if callable(func):
        return wrapper(func)
    else:
        return wrapper
