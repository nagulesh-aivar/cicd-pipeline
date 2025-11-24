from fastapi import APIRouter, status
from client_service.schemas.base_response import APIResponse
from client_service.services.transaction_log_service import TransactionLogService

router = APIRouter()


@router.get(
    "/transaction-logs/{log_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_transaction_log",
    summary="Get transaction log by ID",
    description=(
        "Retrieves a specific transaction log entry by its MongoDB ObjectId. "
        "Returns complete log data including timestamp, service, method, path, IP, "
        "status code, duration, headers, and request body. "
        "Call: GET /transaction-logs/{log_id} where log_id is 24-char ObjectId."
    ),
)
async def get_transaction_log(log_id: str):
    """
    Get a single transaction log by MongoDB ObjectId.

    Args:
        log_id: MongoDB ObjectId as string

    Returns:
        APIResponse with transaction log data
    """
    return await TransactionLogService.get_by_id(log_id=log_id)


@router.get(
    "/transaction-logs",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_transaction_logs",
    summary="List all transaction logs",
    description=(
        "Lists all transaction logs with pagination. Returns array of logs with timestamp, "
        "service name, HTTP method, path, IP address, status code, duration, headers, and request body. "
        "Call: GET /transaction-logs?skip=0&limit=100. Default: skip=0, limit=100 (max)."
    ),
)
async def list_transaction_logs(
    skip: int = 0,
    limit: int = 100,
):
    """
    Get all transaction logs with pagination.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (max 100)

    Returns:
        APIResponse with list of transaction logs
    """
    return await TransactionLogService.get_all(
        skip=skip,
        limit=limit,
    )