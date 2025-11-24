import threading
import time
import logging
from typing import Dict, List, Any, Tuple, Optional
import pytesseract
import os

logger = logging.getLogger(__name__)

def run_with_timeout(func, args=(), kwargs=None, timeout_seconds=180):
    """Run function with timeout using threading (Windows compatible)"""
    if kwargs is None:
        kwargs = {}
    
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        logger.warning(f"Function timed out after {timeout_seconds} seconds")
        return None, True  # result, timed_out
    
    if exception[0]:
        raise exception[0]
    
    return result[0], False  # result, timed_out


def test_tesseract() -> None:
    """Test if Tesseract is properly configured"""
    try:
        # Set Tesseract path from environment variable
        tesseract_cmd = os.getenv('TESSERACT_CMD')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logger.info(f"Tesseract configured: {tesseract_cmd}")
        
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract OCR version: {version}")
    except Exception as e:
        logger.error(f"Tesseract configuration error: {e}")
        raise Exception(f"Tesseract OCR not properly configured: {str(e)}")


def calculate_average_confidence(structured_data: List[Dict]) -> float:
    """Calculate average confidence score"""
    if not structured_data:
        return 0.0
    
    total_confidence = sum(item['confidence'] for item in structured_data)
    return round(total_confidence / len(structured_data), 2)


def create_error_response(error_message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": error_message,
        "plain_text": "",
        "structured_data": [],
        "key_value_pairs": {},
        "tables": [],
        "original_image_base64": "",
        "metadata": {}
    }


def get_ocr_configs() -> Dict[str, str]:
    """Get OCR configuration options"""
    return {
        'default': '--oem 3 --psm 6',
        'single_line': '--oem 3 --psm 7',
        'sparse_text': '--oem 3 --psm 11',
        'table': '--oem 3 --psm 6',
        'vertical_text': '--oem 3 --psm 5',
        'single_block': '--oem 3 --psm 6',
        'uniform_text': '--oem 3 --psm 4',
        'single_text_line': '--oem 3 --psm 7',
        'single_word': '--oem 3 --psm 8',
        'circle_word': '--oem 3 --psm 9',
        'single_char': '--oem 3 --psm 10',
        'sparse_text_osd': '--oem 3 --psm 12'
    }