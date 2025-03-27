import logging

logger = logging.getLogger(__name__)

def mock_send_email(to: str, attachment: str):
    logger.info(f"[MOCK EMAIL] Would send '{attachment}' to {to}")