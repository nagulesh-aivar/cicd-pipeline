"""
Constants file for all OCR API response messages.
"""


class OCRMessages:
    """Messages for OCR operations"""
    
    # Success messages
    PROCESS_SUCCESS = "Document processed successfully"
    PROCESS_SUCCESS_WITH_DATA = "Document processed successfully: {text_length} characters extracted"
    HEALTH_CHECK_SUCCESS = "OCR service is healthy"
    SERVICE_INFO_SUCCESS = "OCR Service API information retrieved"
    VERIFY_HANDWRITTEN_SUCCESS = "Handwritten text verification completed successfully"
    
    # Error messages
    INVALID_URL = "Invalid document URL provided: {url}"
    URL_NOT_ACCESSIBLE = "Document URL is not accessible: {url}"
    UNSUPPORTED_FORMAT = "Unsupported document format. Supported formats: {supported_formats}"
    PROCESSING_ERROR = "Error processing document: {error}"
    DOCUMENT_TOO_LARGE = "Document size exceeds maximum allowed limit: {size}MB"
    OCR_ENGINE_ERROR = "OCR engine error: {error}"
    INVALID_REQUEST = "Invalid request data: {error}"
    SERVICE_UNAVAILABLE = "OCR service is temporarily unavailable"
    TIMEOUT_ERROR = "Document processing timeout: {timeout}s"
    NO_TEXT_EXTRACTED = "No text could be extracted from the document"


class DocumentMessages:
    """Messages for Document operations"""
    
    # Success messages
    VALIDATION_SUCCESS = "Document validation successful"
    PREPROCESSING_SUCCESS = "Document preprocessing completed"
    TEXT_EXTRACTION_SUCCESS = "Text extraction completed: {character_count} characters"
    
    # Error messages
    VALIDATION_ERROR = "Document validation failed: {error}"
    PREPROCESSING_ERROR = "Document preprocessing failed: {error}"
    TEXT_EXTRACTION_ERROR = "Text extraction failed: {error}"
    CORRUPTED_DOCUMENT = "Document appears to be corrupted or unreadable"
    PASSWORD_PROTECTED = "Document is password protected and cannot be processed"
    SCANNING_ERROR = "Document scanning failed: {error}"


class APIMessages:
    """General API messages"""
    
    # Success messages
    API_HEALTHY = "OCR Service API is running"
    DOCS_RETRIEVED = "API documentation retrieved successfully"
    
    # Error messages
    INTERNAL_ERROR = "Internal server error"
    INVALID_ENDPOINT = "Invalid API endpoint"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later"
    MAINTENANCE_MODE = "Service is currently under maintenance"

