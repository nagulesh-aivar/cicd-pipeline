import logging
from datetime import datetime
from bson import ObjectId

from client_service.api.constants.messages import TransactionLogMessages
from client_service.api.constants.status_codes import StatusCode
from client_service.schemas.base_response import APIResponse
from client_service.schemas.mongo_schemas.transaction_log import TransactionLogModel
from client_service.db.mongo_db import get_db
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class TransactionLogService:
    """Service for managing transaction logs stored in MongoDB"""

    @staticmethod
    async def get_by_id(log_id: str) -> APIResponse:
        """
        Retrieve a specific transaction log by MongoDB ObjectId.
        
        Args:
            log_id: MongoDB ObjectId as string
            
        Returns:
            APIResponse with transaction log data
        """
        try:
            # Validate ObjectId format
            try:
                obj_id = ObjectId(log_id)
            except Exception:
                raise HTTPException(
                    status_code=StatusCode.BAD_REQUEST,
                    detail=f"Invalid log_id format: {log_id}",
                )

            # Get MongoDB database
            db = await get_db()
            collection = db["transactions_logs"]

            # Find log by ID
            log = await collection.find_one({"_id": obj_id})

            if not log:
                raise HTTPException(
                    status_code=StatusCode.NOT_FOUND,
                    detail=TransactionLogMessages.NOT_FOUND.format(id=log_id),
                )

            # Convert ObjectId to string for JSON serialization
            log["_id"] = str(log["_id"])
            
            # Convert datetime to ISO format
            if "timestamp" in log and isinstance(log["timestamp"], datetime):
                log["timestamp"] = log["timestamp"].isoformat()

            logger.info(f"Retrieved transaction log: {log_id}")

            return APIResponse(
                success=True,
                message=TransactionLogMessages.RETRIEVED_SUCCESS.format(id=log_id),
                data=log,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving transaction log: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=TransactionLogMessages.RETRIEVE_ERROR.format(error=str(e)),
            )

    @staticmethod
    async def get_all(
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        """
        Retrieve all transaction logs with pagination.
        
        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            APIResponse with list of transaction logs
        """
        try:
            # Get MongoDB database
            db = await get_db()
            collection_name = TransactionLogModel.Settings.name
            collection = db[collection_name]

            # Get total count
            total_count = await collection.count_documents({})

            # Fetch logs with pagination
            cursor = (
                collection.find({})
                .sort("timestamp", -1)  # Most recent first
                .skip(skip)
                .limit(min(limit, 100))  # Max 100 per request
            )

            logs = await cursor.to_list(length=limit)

            # Process logs for JSON serialization
            for log in logs:
                log["_id"] = str(log["_id"])
                if "timestamp" in log and isinstance(log["timestamp"], datetime):
                    log["timestamp"] = log["timestamp"].isoformat()

            logger.info(
                f"Retrieved {len(logs)} transaction logs (total: {total_count})"
            )

            return APIResponse(
                success=True,
                message=TransactionLogMessages.RETRIEVED_ALL_SUCCESS.format(
                    count=len(logs)
                ),
                data={
                    "logs": logs,
                    "pagination": {
                        "total": total_count,
                        "skip": skip,
                        "limit": limit,
                        "returned": len(logs),
                    },
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving transaction logs: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=StatusCode.INTERNAL_SERVER_ERROR,
                detail=TransactionLogMessages.RETRIEVE_ALL_ERROR.format(error=str(e)),
            )