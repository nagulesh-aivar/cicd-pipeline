from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging
import numpy as np
import cv2
from ocr_service.services import ocr_service_v2, ocr_service
from ocr_service.schemas.base_response import APIResponse
from ocr_service.api.constants.status_codes import StatusCode
from ocr_service.api.constants.messages import OCRMessages

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentRequest(BaseModel):
    url: str


@router.post(
    "/process",
    response_model=APIResponse,
    summary="Process Document with OCR",
    description="Process a document (image or PDF) from URL using advanced OCR technology to extract text content."
)
def process_document(request: DocumentRequest):  
    """
    Process a document (image or PDF) from URL using advanced OCR
    
    This endpoint accepts a document URL and returns extracted text content
    along with metadata about the processing results.
    """
    try:
        logger.info(f"Processing document from URL: {request.url}")
        
        result = ocr_service.OCRService.process_document_from_url(request.url)
        
        # Check if there's an error in the result
        if result.get("error"):
            raise HTTPException(
                status_code=StatusCode.UNPROCESSABLE_ENTITY, 
                detail=f"OCR processing failed: {result.get('error')}"
            )
        
        # Extract text length for success message
        extracted_text = result.get("plain_text", "")
        text_length = len(extracted_text) if extracted_text else 0
        
        return APIResponse(
            success=True,
            message=OCRMessages.PROCESS_SUCCESS_WITH_DATA.format(text_length=text_length),
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process_document endpoint: {str(e)}")
        raise HTTPException(
            status_code=StatusCode.INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during OCR processing: {str(e)}"
        )


@router.get(
    "/verify-handwritten",
    response_model=APIResponse,
    summary="Verify if document is handwritten",
    description="Verify whether the given document (PDF or Image) is handwritten or printed."
)
def verify_handwritten(
    url: str = Query(..., description="Public URL of the image or PDF")
):
    """
    Verify whether the given document (PDF or Image) is handwritten or printed.
    The service:
      - Detects file type (PDF or Image)
      - For PDF → uses PyPDF or fitz-based OCR
      - For Image → uses pytesseract OCR
      - Computes confidence and determines if handwritten
    """
    try:
        logger.info(f"🔍 Verifying handwritten document from URL: {url}")
        file_content = ocr_service_v2.OCRService.download_file_from_url(url)

        # --- Case 1: PDF ---
        if ocr_service_v2.OCRService.is_pdf_url(url):
            text, confidence, pdf_type = ocr_service_v2.OCRService.extract_text_from_pdf(file_content)

            # Determine handwriting based on confidence or missing text
            is_handwritten = pdf_type in ["handwritten_pdf"] or confidence < 40

            response = {
                "url": url,
                "file_type": pdf_type,
                "is_handwritten": bool(is_handwritten),
                "confidence": round(confidence, 2),
                "method": "PyPDF" if pdf_type == "text_pdf" else "fitz + Tesseract OCR",
                "summary": (
                    "Detected handwritten PDF (low OCR confidence)"
                    if is_handwritten
                    else "Detected printed/text PDF"
                ),
            }
            return APIResponse(
                success=True,
                message="Handwritten verification completed successfully.",
                data=response
            )

        # --- Case 2: Image ---
        np_arr = np.frombuffer(file_content, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Could not decode image from URL content")

        # Detect using pytesseract OCR
        text, confidence, img_type = ocr_service_v2.OCRService.extract_text_from_image(image)
        is_handwritten = img_type == "handwritten_image" or confidence < 40

        response = {
            "url": url,
            "file_type": img_type,
            "is_handwritten": bool(is_handwritten),
            "confidence": round(confidence, 2),
            "method": "Tesseract OCR (image-based)",
            "summary": (
                "Detected handwritten content (low confidence)"
                if is_handwritten
                else "Detected printed text image"
            ),
        }

        return APIResponse(
            success=True,
            message="Handwritten verification completed successfully.",
            data=response
        )

    except Exception as e:
        logger.error(f"Error verifying handwritten document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/extract-data",
    response_model=APIResponse,
    summary="Extract text from document",
    description="Extract text and confidence dynamically from a public URL."
)
def extract_data(
    url: str = Query(..., description="Public URL of the image or PDF file"),
):
    """
    Extract text and confidence dynamically from a public URL.
    Automatically detects file type (PDF, image, handwritten, etc.).
    """
    try:
        logger.info(f"📄 Extracting data from document at URL: {url}")

        # Process the document using the OCR service
        result = ocr_service_v2.OCRService.process_from_url(url)

        # Check if there's an error in the result
        if "error" in result:
            raise HTTPException(
                status_code=StatusCode.UNPROCESSABLE_ENTITY,
                detail=f"Data extraction failed: {result.get('error')}",
            )

        # Extract text length for success message
        extracted_text = result.get("extracted_text", "")
        text_length = len(extracted_text) if extracted_text else 0

        return APIResponse(
            success=True,
            message=OCRMessages.PROCESS_SUCCESS_WITH_DATA.format(text_length=text_length),
            data=result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting data from document: {e}")
        raise HTTPException(
            status_code=StatusCode.INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during data extraction: {str(e)}",
        )