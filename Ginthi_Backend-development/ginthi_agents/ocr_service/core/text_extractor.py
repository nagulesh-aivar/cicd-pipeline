import pytesseract
import time
import logging
from PIL import Image
from typing import Dict, List, Any
from .ocr_helpers import run_with_timeout, get_ocr_configs, calculate_average_confidence
from .data_parser import extract_key_value_pairs_advanced, extract_table_data_advanced, group_words_into_lines

logger = logging.getLogger(__name__)


def extract_plain_text_advanced(processed_image: Image.Image) -> str:
    """Extract plain text using multiple OCR configurations and best result selection"""
    try:
        logger.info("Extracting plain text with advanced OCR methods...")
        
        ocr_configs = get_ocr_configs()
        
        # Test multiple configurations
        configs_to_test = [
            'default',
            'uniform_text',
            'single_block',
            'sparse_text',
            'sparse_text_osd'
        ]
        
        best_text = ""
        max_confidence = 0
        timeout_seconds = 180
        start_time = time.time()
        
        for config_name in configs_to_test:
            if time.time() - start_time > timeout_seconds:
                logger.warning(f"Total processing time exceeded {timeout_seconds} seconds. Stopping OCR tests.")
                break
            try:
                config = ocr_configs[config_name]
                logger.info(f"  Testing config: {config_name}")

                def ocr_task():
                    return pytesseract.image_to_data(processed_image, config=config, output_type=pytesseract.Output.DICT)
            
                data, timed_out = run_with_timeout(ocr_task, timeout_seconds=60)
                
                if timed_out:
                    logger.warning(f"Config {config_name} timed out after 60 seconds")
                    continue
                # Calculate average confidence
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
                    logger.info(f"    Average confidence: {avg_confidence:.2f}%")
                    
                    if avg_confidence > max_confidence:
                        max_confidence = avg_confidence
                        best_text = '\n'.join([t for t in data['text'] if t.strip()])
                        if best_text:
                            logger.info(f"    New best result (confidence: {avg_confidence:.2f}%)")
                            
            except Exception as e:
                logger.warning(f"Config {config_name} failed: {e}")
                continue
        
        # Fallback to basic OCR if no good result
        if not best_text.strip():
            logger.info("Falling back to basic OCR...")
            try:
                def basic_ocr_task():
                    return pytesseract.image_to_string(processed_image)
                
                basic_result, timed_out = run_with_timeout(basic_ocr_task, timeout_seconds=30)
                
                if not timed_out and basic_result:
                    best_text = basic_result
                elif timed_out:
                    logger.warning("Basic OCR also timed out")
                    best_text = "OCR processing timed out - unable to extract text"
                    
            except Exception as e:
                logger.error(f"Basic OCR failed: {e}")
                best_text = "OCR processing failed"
        
        logger.info(f"Plain text extraction completed. Extracted {len(best_text)} characters")
        return best_text.strip()
        
    except Exception as e:
        logger.error(f"Error in advanced plain text extraction: {e}")
        return ""


def extract_text_with_confidence_and_positioning_advanced(processed_image: Image.Image) -> List[Dict[str, Any]]:
    """Extract text with confidence and positioning using advanced preprocessing with timeout"""
    try:
        logger.info("Extracting structured text with advanced methods...")
        
        ocr_configs = get_ocr_configs()
        
        def structured_ocr_task():
            data = pytesseract.image_to_data(
                processed_image, 
                output_type=pytesseract.Output.DICT,
                config=ocr_configs['default']
            )
            
            results = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                confidence = float(data['conf'][i])
                
                if text and confidence > 30:
                    result = {
                        'text': text,
                        'confidence': confidence,
                        'bbox': {
                            'left': int(data['left'][i]),
                            'top': int(data['top'][i]),
                            'width': int(data['width'][i]),
                            'height': int(data['height'][i])
                        },
                        'level': int(data['level'][i]),
                        'block_num': int(data['block_num'][i]),
                        'par_num': int(data['par_num'][i]),
                        'line_num': int(data['line_num'][i]),
                        'word_num': int(data['word_num'][i])
                    }
                    results.append(result)
            
            return results
        
        results, timed_out = run_with_timeout(structured_ocr_task, timeout_seconds=60)
        
        if timed_out:
            logger.warning("Structured text extraction timed out. Returning empty results.")
            results = []
        elif results is None:
            results = []
        
        logger.info(f"Extracted {len(results)} text elements with positioning")
        return results
        
    except Exception as e:
        logger.error(f"Error in advanced structured text extraction: {e}")
        return []


def extract_all_data_advanced(pil_image: Image.Image, processed_image: Image.Image) -> Dict[str, Any]:
    """
    Extract all types of data using advanced preprocessing and methods
    
    Args:
        pil_image: Original PIL Image object
        processed_image: Preprocessed PIL Image object
        
    Returns:
        Dictionary with all extracted data
    """
    try:
        
        
        plain_text = extract_plain_text_advanced(processed_image)
        structured_data = extract_text_with_confidence_and_positioning_advanced(processed_image)
        lines = group_words_into_lines(structured_data)  
        key_value_pairs = extract_key_value_pairs_advanced(lines)  
        tables = extract_table_data_advanced(lines)  
        avg_confidence = calculate_average_confidence(structured_data)

        return {
            "plain_text": plain_text,
            "structured_data": structured_data,
            "key_value_pairs": key_value_pairs,
            "tables": tables,
            "metadata": {
                "total_text_elements": len(structured_data),
                "average_confidence": avg_confidence,
                "tables_found": len(tables),
                "processing_method": "advanced_ocr_with_preprocessing"
            }
        }
    except Exception as e:
        logger.error(f"Error in advanced data extraction: {str(e)}")
        return {
            "plain_text": "",
            "structured_data": [],
            "key_value_pairs": {},
            "tables": [],
            "metadata": {"error": str(e)}
        }