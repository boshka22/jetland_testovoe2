"""Root pytest configuration."""

import django
from django.conf import settings  # noqa: F401


def pytest_configure() -> None:
    django.setup()
