import logging
import os
from urllib.parse import urlparse
from PIL import Image
import cv2
from typing import Dict, Any

from ocr_service.core.ocr_helpers import test_tesseract, create_error_response
from ocr_service.core.image_processor import (
    download_image_from_url, 
    download_pdf_from_url, 
    preprocess_image_advanced, 
    image_to_base64,
    process_pdf_pages
)
from ocr_service.core.text_extractor import extract_all_data_advanced

logger = logging.getLogger(__name__)


class OCRService:
    """
    Advanced OCR service using proven preprocessing and extraction methods.
    Designed to work with LLM service for intelligent field mapping.
    """
    
    def __init__(self):
        """Initialize OCR service with advanced configurations"""
        # Test Tesseract installation
        test_tesseract()
        logger.info("Advanced OCR Service initialized successfully")
    
    async def process_document_from_url(self, url: str) -> Dict[str, Any]:
        """
        Main method to process document from URL with advanced analysis
        
        Args:
            url: Document URL (image or PDF)
            
        Returns:
            Dictionary with extracted data and original image
        """
        try:
            # Determine file type
            parsed_url = urlparse(url)
            file_extension = os.path.splitext(parsed_url.path)[1].lower()
            
            if file_extension == '.pdf':
                return await self._process_pdf_from_url(url)
            else:
                return await self._process_image_from_url(url)
                
        except Exception as e:
            logger.error(f"Error processing document from URL {url}: {str(e)}")
            return create_error_response(f"Error processing document: {str(e)}")
    
    async def _process_image_from_url(self, url: str) -> Dict[str, Any]:
        """
        Process single image document from URL with advanced preprocessing
        
        Args:
            url: Image URL
            
        Returns:
            Dictionary with extracted data
        """
        try:
            # Download original image
            original_image = download_image_from_url(url)
            pil_image = Image.fromarray(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))
            original_image_b64 = image_to_base64(pil_image)
            processed_image = preprocess_image_advanced(pil_image)
            extraction_result = extract_all_data_advanced(pil_image, processed_image)
            
            result = {
                "source_url": url,
                "file_type": "image",
                "plain_text": extraction_result["plain_text"],
                "structured_data": extraction_result["structured_data"],
                "key_value_pairs": extraction_result["key_value_pairs"],
                "tables": extraction_result["tables"],
                "original_image_base64": original_image_b64,
                "metadata": {
                    "image_dimensions": {
                        "width": pil_image.width,
                        "height": pil_image.height
                    },
                    "processing_info": extraction_result["metadata"]
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image from URL {url}: {str(e)}")
            return create_error_response(f"Error processing image: {str(e)}")
    
    async def _process_pdf_from_url(self, url: str) -> Dict[str, Any]:
        """
        Process PDF document from URL with advanced analysis
        
        Args:
            url: PDF URL
            
        Returns:
            Dictionary with extracted data from all pages
        """
        try:
            # Download PDF
            pdf_content = download_pdf_from_url(url)
            
            # Process PDF pages
            pages_data_raw = process_pdf_pages(pdf_content)
            
            all_pages_data = []
            combined_text = ""
            combined_tables = []
            combined_kv_pairs = {}
            combined_structured_data = []
            first_page_image_b64 = None
            all_page_images = []  # Store all page images
            
            for page_data in pages_data_raw:
                page_num = page_data['page_number']
                pil_image = page_data['pil_image']
                
                # Convert current page to base64
                page_image_b64 = image_to_base64(pil_image)
                
                # Store first page image for backward compatibility
                if page_num == 1:
                    first_page_image_b64 = page_image_b64
                
                # Store all page images with page numbers
                all_page_images.append({
                    "page_number": page_num,
                    "image_base64": page_image_b64
                })
                
                # Preprocess image
                processed_image = preprocess_image_advanced(pil_image)
                
                # Process page with advanced methods
                page_extraction = extract_all_data_advanced(pil_image, processed_image)
                
                # Add page info to structured data
                for item in page_extraction["structured_data"]:
                    item["page_number"] = page_num
                
                # Combine results
                page_result = {
                    "page_number": page_num,
                    "plain_text": page_extraction["plain_text"],
                    "structured_data": page_extraction["structured_data"],
                    "key_value_pairs": page_extraction["key_value_pairs"],
                    "tables": page_extraction["tables"],
                    "page_image_base64": page_image_b64  # Include page image in each page data
                }
                all_pages_data.append(page_result)
                
                # Combine for overall document
                combined_text += f"\n--- Page {page_num} ---\n" + page_extraction["plain_text"]
                combined_tables.extend(page_extraction["tables"])
                combined_kv_pairs.update(page_extraction["key_value_pairs"])
                combined_structured_data.extend(page_extraction["structured_data"])
            
            # Prepare final response
            result = {
                "source_url": url,
                "file_type": "pdf",
                "plain_text": combined_text.strip(),
                "structured_data": combined_structured_data,
                "key_value_pairs": combined_kv_pairs,
                "tables": combined_tables,
                "original_image_base64": first_page_image_b64,  
                "all_page_images": all_page_images, 
                "pages_data": all_pages_data,
                "metadata": {
                    "total_pages": len(pages_data_raw),
                    "processing_info": {
                        "resolution_multiplier": 2.0,
                        "pages_processed": len(all_pages_data),
                        "all_page_images_stored": len(all_page_images)
                    }
                }
            }
            
            return result
                
        except Exception as e:
            logger.error(f"Error processing PDF from URL {url}: {str(e)}")
            return create_error_response(f"Error processing PDF: {str(e)}")


# Create service instance
ocr_service = OCRService()