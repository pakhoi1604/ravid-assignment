from .base import *  # noqa: F403

DEBUG = env_bool("DEBUG", True)  # noqa: F405
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")  # noqa: F405
