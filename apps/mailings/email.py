"""Заглушка отправки email.

В продакшене заменяется реальным email-бэкендом (SMTP, SendGrid и т.д.).
Сейчас имитирует задержку сети случайным sleep и логирует доставку.
"""

import logging
from random import randint
from time import sleep

logger = logging.getLogger(__name__)


def send_email(
    *,
    user_id: int,
    email: str,
    subject: str,
    message: str,
) -> None:
    """Имитирует отправку письма: ждёт и пишет в лог.

    Args:
        user_id: ID получателя во внешней системе.
        email: Email-адрес получателя.
        subject: Тема письма.
        message: Текст письма.
    """
    sleep(randint(5, 20))
    logger.info(
        "Send EMAIL to=%s user_id=%s subject=%r",
        email,
        user_id,
        subject,
    )
