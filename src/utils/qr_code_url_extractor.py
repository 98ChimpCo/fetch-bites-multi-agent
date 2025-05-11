import os
import re
import logging

from PIL import Image
from pyzbar.pyzbar import decode

logger = logging.getLogger(__name__)

def extract_url_from_qr_image(image_path):
    """
    Attempt to extract a URL from a QR code screenshot using QR code decoding.
    """
    if not os.path.exists(image_path):
        logger.warning(f"QR image file not found: {image_path}")
        return None
    try:
        img = Image.open(image_path)
        decoded_objects = decode(img)

        for obj in decoded_objects:
            if obj.type == 'QRCODE':
                url = obj.data.decode('utf-8')
                logger.info(f"[QR DEBUG] Decoded URL from QR: {url}")
                return url

        logger.warning("[QR DEBUG] No QR code found in image.")
        return None
    except Exception as e:
        logger.error(f"Failed to extract QR code URL: {e}")
        return None