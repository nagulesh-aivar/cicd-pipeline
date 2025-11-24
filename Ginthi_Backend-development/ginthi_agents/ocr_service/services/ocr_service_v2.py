import io
import base64
import pytesseract
import requests
import numpy as np
import cv2
from PIL import Image
from pypdf import PdfReader
import fitz  # PyMuPDF
import logging
from typing import Dict, Any, Tuple
from ocr_service.core.image_processor import preprocess_image, detect_handwriting_texture

logger = logging.getLogger(__name__)


class OCRService:
    # ----------------------------
    # Utility
    # ----------------------------
    @staticmethod
    def download_file_from_url(url: str) -> bytes:
        """Download file (image or PDF) from URL."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {e}")
            raise

    @staticmethod
    def is_pdf_url(url: str) -> bool:
        return url.lower().endswith(".pdf")

    @staticmethod
    def image_to_base64(image: np.ndarray) -> str:
        """Convert numpy image to Base64 string."""
        _, buffer = cv2.imencode(".png", image)
        return base64.b64encode(buffer).decode("utf-8")

    # ----------------------------
    # Advanced Handwriting Features
    # ----------------------------
    @staticmethod
    def analyze_contour_irregularity(image: np.ndarray) -> float:
        """
        Measure irregularity of contours — handwritten text
        often has more jagged, inconsistent contours.
        Returns irregularity score (0–1 range).
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        irregularities = []
        for c in contours:
            perimeter = cv2.arcLength(c, True)
            area = cv2.contourArea(c)
            if area > 10:  # ignore noise
                circularity = (4 * np.pi * area) / (perimeter ** 2 + 1e-6)
                irregularities.append(abs(1 - circularity))

        return float(np.mean(irregularities)) if irregularities else 0.0

    @staticmethod
    def enhanced_handwritten_ocr(image: np.ndarray) -> Tuple[str, float]:
        """
        Secondary OCR pass optimized for handwriting.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.convertScaleAbs(gray, alpha=1.8, beta=35)
            gray = cv2.bilateralFilter(gray, 7, 50, 50)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            text = pytesseract.image_to_string(
                binary,
                lang="eng",
                config="--psm 6 --oem 3"
            ).strip()

            data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)
            confs = [int(conf) for conf in data["conf"] if str(conf).isdigit() and int(conf) > 0]
            avg_conf = np.mean(confs) if confs else 0.0

            return text, avg_conf

        except Exception as e:
            logger.error(f"Enhanced handwritten OCR failed: {e}")
            return "", 0.0

    # ----------------------------
    # PDF Extraction
    # ----------------------------
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, float, str]:
        """
        Extract text dynamically from PDFs.
        """
        try:
            text = ""
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                logger.info(f"Extracted text from page: {page_text[:100]}")  # Log first 100 characters
                text += page_text

            if len(text.strip()) > 50:
                logger.info("✅ Text-based PDF (PyPDF).")
                return text.strip(), 95.0, "text_pdf"

            # OCR for scanned PDFs
            doc = fitz.open("pdf", pdf_bytes)
            all_text, confidences = [], []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
                np_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                processed = preprocess_image(np_img)

                data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
                page_text = pytesseract.image_to_string(processed)
                all_text.append(page_text)

                page_conf = [int(conf) for conf in data["conf"] if str(conf).isdigit() and int(conf) > 0]
                if page_conf:
                    confidences.append(np.mean(page_conf))

            text = "\n".join(all_text).strip()
            avg_conf = np.mean(confidences) if confidences else 0.0

            # Texture + contour analysis
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            np_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            texture_detected = detect_handwriting_texture(np_img)
            contour_score = OCRService.analyze_contour_irregularity(np_img)

            # Enhanced OCR refinement
            if texture_detected or avg_conf < 60 or contour_score > 0.3:
                logger.info("⚙️ Running enhanced handwritten OCR refinement...")
                extra_text, extra_conf = OCRService.enhanced_handwritten_ocr(np_img)
                if extra_text:
                    text += "\n" + extra_text
                    avg_conf = (avg_conf + extra_conf) / 2

            # Hybrid classification
            if avg_conf >= 80:
                pdf_type = "image_pdf"
            elif 60 <= avg_conf < 80:
                pdf_type = "image_pdf" if not (texture_detected or contour_score > 0.3) else "mixed_image_pdf"
            elif 40 <= avg_conf < 60:
                pdf_type = "low_quality_image_pdf" if (texture_detected or contour_score > 0.3) else "low_quality_printed_pdf"
            else:
                pdf_type = "handwritten_pdf"

            return text, avg_conf, pdf_type

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return "(Error extracting text)", 0.0, "error_pdf"

    # ----------------------------
    # Image Extraction
    # ----------------------------
    @staticmethod
    def extract_text_from_image(image: np.ndarray) -> Tuple[str, float, str]:
        """Extract text + confidence + classify image type."""
        processed = preprocess_image(image)
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(processed).strip()

        confidences = [int(conf) for conf in data["conf"] if str(conf).isdigit() and int(conf) > 0]
        avg_conf = np.mean(confidences) if confidences else 0.0

        texture_detected = detect_handwriting_texture(image)
        contour_score =  OCRService.analyze_contour_irregularity(image)

        # Enhanced OCR if confidence < 60
        if avg_conf < 60 or texture_detected:
            extra_text, extra_conf = OCRService.enhanced_handwritten_ocr(image)
            if extra_text:
                text += "\n" + extra_text
                avg_conf = (avg_conf + extra_conf) / 2

        # Smarter classification
        if avg_conf >= 80:
            img_type = "printed_image"
        elif 60 <= avg_conf < 80:
            img_type = "printed_image" if not (texture_detected or contour_score > 0.3) else "image_pdf"
        elif 40 <= avg_conf < 60:
            img_type = "low_quality_image_" if (texture_detected or contour_score > 0.3) else "low_quality_image"
        else:
            img_type = "handwritten_image"

        logger.info(
            f"OCR={avg_conf:.2f}, texture={texture_detected}, contour={contour_score:.2f}, classified={img_type}"
        )
        return text, avg_conf, img_type

    # ----------------------------
    # End-to-End URL Processor
    # ----------------------------
    @staticmethod
    def process_from_url(url: str) -> Dict[str, Any]:
        """Full OCR pipeline: download, detect, extract, classify."""
        try:
            logger.info(f"Processing OCR for URL: {url}")
            file_content = OCRService.download_file_from_url(url)

            # PDF
            if OCRService.is_pdf_url(url):
                text, confidence, pdf_type = OCRService.extract_text_from_pdf(file_content)
                return {
                    "url": url,
                    "file_type": pdf_type,
                    "confidence": round(confidence, 2),
                    "is_handwritten": pdf_type in ["handwritten_pdf", "image_pdf"],
                    "extracted_text": text if text else "(No text found)"
                }

            # Image
            np_arr = np.frombuffer(file_content, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Could not decode image from URL content")

            text, confidence, img_type = OCRService.extract_text_from_image(image)
            return {
                "url": url,
                "file_type": img_type,
                "confidence": round(confidence, 2),
                "is_handwritten": img_type in ["handwritten_image", "mixed_handwritten_image"],
                "extracted_text": text if text else "(No text found)"
            }

        except Exception as e:
            logger.error(f"OCR processing error for {url}: {e}")
            return {"error": str(e)}
