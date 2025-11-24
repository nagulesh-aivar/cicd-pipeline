from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional
import json
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd

from etl_service.services.data_transform_service import DataTransformService
from etl_service.utils.logger import get_logger
from etl_service.config import settings

logger = get_logger(__name__)

router = APIRouter()


@router.post("/transform")
async def transform_data(
    file: UploadFile = File(..., description="CSV file to transform"),
    schema: str = Form(..., description="JSON schema for transformation")
):
    """
    Transform CSV data using provided schema
    
    This single endpoint performs:
    1. Automatic preprocessing (duplicates, nulls, types)
    2. Schema-based transformation
    3. Export to desired format
    
    Request:
    - file: CSV file (multipart/form-data)
    - schema: JSON string defining transformation rules
    
    Schema format:
    {
        "table_name": "output_name",
        "output_format": "csv|excel|json|parquet",
        "columns": [
            {
                "source_column": "Original Column",
                "target_column": "new_column",
                "data_type": "string|integer|float|date|boolean",
                "required": true,
                "transformations": ["trim", "uppercase"],
                "date_format": "dd/mm/yyyy",
                "default_value": null
            }
        ],
        "calculated_columns": [
            {
                "target_column": "calculated_field",
                "formula": "col1 * col2",
                "data_type": "float"
            }
        ]
    }
    
    Response:
    {
        "status": "success",
        "output_file": "/path/to/output.csv",
        "summary": {
            "input": {"rows": 1000, "columns": 50},
            "preprocessing": {
                "duplicates_removed": 5,
                "null_values_standardized": 150,
                "type_conversions": 30
            },
            "transformation": {
                "columns_selected": 10,
                "calculated_columns_added": 2,
                "rows_output": 995
            }
        }
    }
    """
    try:
        logger.info(f"Received transformation request for file: {file.filename}")
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are supported"
            )
        
        # Parse schema
        try:
            schema_dict = json.loads(schema)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON schema: {str(e)}"
            )
        
        # Validate schema structure
        if 'columns' not in schema_dict:
            raise HTTPException(
                status_code=400,
                detail="Schema must contain 'columns' field"
            )
        
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file_path = settings.DOWNLOADS_DIR / f"temp_{timestamp}_{file.filename}"
        
        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved uploaded file to: {temp_file_path}")
        
        # Perform transformation
        result = DataTransformService.transform_data(
            csv_file_path=str(temp_file_path),
            schema=schema_dict
        )
        
        # Clean up temp file
        try:
            temp_file_path.unlink()
            logger.info(f"Cleaned up temp file: {temp_file_path}")
        except Exception as e:
            logger.warning(f"Could not delete temp file: {str(e)}")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Transformation failed: {str(e)}"
        )


@router.post("/preprocess")
async def preprocess_data(
    file: UploadFile = File(..., description="CSV file to preprocess")
):
    """
    Preprocess CSV data only (no schema transformation)
    
    This endpoint performs automatic preprocessing:
    1. Remove duplicates
    2. Standardize NULL values (-, "", ' ' → NULL)
    3. Auto-detect and convert data types
    4. Trim whitespace
    5. Remove line endings (^M)
    
    Returns preprocessed CSV with:
    - Clean data
    - Proper data types
    - Report on what was cleaned
    
    Request:
    - file: CSV file (multipart/form-data)
    
    Response:
    {
        "status": "success",
        "preprocessed_file": "/path/to/cleaned.csv",
        "summary": {
            "input_rows": 1000,
            "output_rows": 995,
            "duplicates_removed": 5,
            "null_values_standardized": 150,
            "type_conversions": 30,
            "detected_types": {...}
        }
    }
    """
    try:
        logger.info(f"Received preprocessing request for file: {file.filename}")
        
        # Validate file type
        supported_formats = ['.csv', '.xlsx', '.xls']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported: {', '.join(supported_formats)}"
            )
        
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file_path = settings.DOWNLOADS_DIR / f"temp_{timestamp}_{file.filename}"
        
        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved uploaded file to: {temp_file_path}")
        
        # Perform preprocessing only
        
        
        # Load CSV
        if file_ext == '.csv':
            df = pd.read_csv(temp_file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(temp_file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        original_rows = len(df)
        original_columns = len(df.columns)
        
        logger.info(f"Loaded CSV: {original_rows} rows, {original_columns} columns")
        
        # Preprocess
        
        df_preprocessed, preprocessing_summary = DataTransformService._preprocess(df)
        
        # Export preprocessed data
        output_filename = f"preprocessed_{timestamp}_{file.filename}"
        output_path = settings.DOWNLOADS_DIR / output_filename
        df_preprocessed.to_csv(output_path, index=False)
        
        logger.info(f"Preprocessed file saved: {output_path}")
        
        # Clean up temp file
        try:
            temp_file_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete temp file: {str(e)}")
        
        return {
            "status": "success",
            "preprocessed_file": str(output_path),
            "summary": {
                "input_rows": original_rows,
                "input_columns": original_columns,
                "output_rows": len(df_preprocessed),
                "output_columns": len(df_preprocessed.columns),
                "duplicates_removed": preprocessing_summary.get('duplicates_removed', 0),
                "null_values_standardized": preprocessing_summary.get('null_values_standardized', 0),
                "type_conversions": preprocessing_summary.get('type_conversions', 0),
                "detected_types": preprocessing_summary.get('detected_types', {})
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preprocessing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Preprocessing failed: {str(e)}"
        )