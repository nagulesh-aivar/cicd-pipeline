import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json

from etl_service.utils.type_detector import TypeDetector
from etl_service.utils.data_cleaner import DataCleaner
from etl_service.utils.formula_parser import FormulaParser
from etl_service.utils.logger import get_logger
from etl_service.config import settings

logger = get_logger(__name__)


class DataTransformService:
    """
    Dynamic data transformation service
    
    Performs:
    1. Automatic preprocessing (duplicate removal, null handling, type detection)
    2. Schema-based transformation (column selection, renaming, type conversion)
    3. Calculated columns
    4. Data export
    """

    @staticmethod
    def transform_data(csv_file_path: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main transformation method
        
        Args:
            csv_file_path: Path to input CSV file
            schema: JSON schema defining transformation rules
        
        Returns:
            Dictionary with output file path and summary
        """
        try:
            logger.info(f"Starting transformation for: {csv_file_path}")
            logger.info(f"Schema: {json.dumps(schema, indent=2)}")
            
            # STEP 1: Load CSV
            df = DataTransformService._load_csv(csv_file_path)
            original_rows = len(df)
            original_columns = len(df.columns)
            logger.info(f"Loaded CSV: {original_rows} rows, {original_columns} columns")
            
            # STEP 2: Preprocess (automatic)
            df_preprocessed, preprocessing_summary = DataTransformService._preprocess(df)
            logger.info(f"Preprocessing complete: {preprocessing_summary}")
            
            # STEP 3: Apply schema transformation
            df_transformed, transformation_summary = DataTransformService._apply_schema(
                df_preprocessed, schema
            )
            logger.info(f"Schema transformation complete: {transformation_summary}")
            
            # STEP 4: Export result
            output_file = DataTransformService._export_result(
                df_transformed, 
                schema.get('table_name', 'output'),
                schema.get('output_format', 'csv')
            )
            logger.info(f"Export complete: {output_file}")
            
            return {
                "status": "success",
                "output_file": output_file,
                "summary": {
                    "input": {
                        "rows": original_rows,
                        "columns": original_columns
                    },
                    "preprocessing": preprocessing_summary,
                    "transformation": transformation_summary,
                    "output": {
                        "rows": len(df_transformed),
                        "columns": len(df_transformed.columns)
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"Transformation failed: {str(e)}")
            raise

    @staticmethod
    def _load_csv(file_path: str) -> pd.DataFrame:
        """Load CSV file with proper encoding handling"""
        try:
            # Try UTF-8 first
            df = pd.read_csv(file_path, encoding='utf-8')
            return df
        except UnicodeDecodeError:
            # Fallback to latin-1
            logger.warning("UTF-8 decode failed, trying latin-1")
            df = pd.read_csv(file_path, encoding='latin-1')
            return df
        except Exception as e:
            logger.error(f"Failed to load CSV: {str(e)}")
            raise

    @staticmethod
    def _preprocess(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Automatic preprocessing
        
        Steps:
        1. Remove line endings (^M, etc.)
        2. Trim whitespace
        3. Handle NULL values
        4. Remove duplicates
        5. Auto-detect and convert types
        """
        summary = {}
        
        # 1. Remove line endings
        df = DataCleaner.remove_line_endings(df)
        logger.info("Removed line endings")
        
        # 2. Trim whitespace from all string columns
        df = DataCleaner.trim_strings(df)
        logger.info("Trimmed whitespace")
        
        # 3. Handle NULL values
        null_count_before = df.isna().sum().sum()
        df = DataCleaner.clean_null_values(df)
        null_count_after = df.isna().sum().sum()
        summary['null_values_standardized'] = int(null_count_after)
        logger.info(f"Standardized NULL values: {null_count_after}")
        
        # 4. Remove duplicates
        df, duplicates_removed = DataCleaner.remove_duplicates(df)
        summary['duplicates_removed'] = duplicates_removed
        logger.info(f"Removed duplicates: {duplicates_removed}")
        
        # 5. Auto-detect and convert types
        type_conversions = 0
        detected_types = {}
        
        for col in df.columns:
            detected_type = TypeDetector.detect_column_type(df[col])
            detected_types[col] = detected_type
            
            # Convert to detected type
            try:
                if detected_type == 'integer':
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('Int64')
                    type_conversions += 1
                elif detected_type == 'float':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    type_conversions += 1
                elif detected_type == 'date':
                    date_format = TypeDetector.detect_date_format(df[col])
                    df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
                    type_conversions += 1
                elif detected_type == 'boolean':
                    df[col] = df[col].map({
                        'true': True, 'True': True, 'TRUE': True, '1': True, 'yes': True, 'Yes': True,
                        'false': False, 'False': False, 'FALSE': False, '0': False, 'no': False, 'No': False
                    })
                    type_conversions += 1
            except Exception as e:
                logger.warning(f"Could not convert column {col} to {detected_type}: {str(e)}")
        
        summary['type_conversions'] = type_conversions
        summary['detected_types'] = detected_types
        logger.info(f"Type conversions completed: {type_conversions}")
        
        return df, summary

    @staticmethod
    def _apply_schema(df: pd.DataFrame, schema: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply schema-based transformation
        
        Schema format:
        {
            "table_name": "output_table",
            "columns": [
                {
                    "source_column": "Original Name",
                    "target_column": "new_name",
                    "data_type": "string|integer|float|date|boolean",
                    "required": true/false,
                    "transformations": ["trim", "uppercase", etc.],
                    "date_format": "dd/mm/yyyy",
                    "default_value": null
                }
            ],
            "calculated_columns": [
                {
                    "target_column": "calc_field",
                    "formula": "col1 + col2",
                    "data_type": "float"
                }
            ]
        }
        """
        summary = {
            'columns_selected': 0,
            'columns_renamed': 0,
            'type_conversions': 0,
            'transformations_applied': 0,
            'calculated_columns_added': 0,
            'rows_skipped': 0
        }
        
        result_df = pd.DataFrame()
        
        # Process each column in schema
        if 'columns' in schema:
            for col_config in schema['columns']:
                source_col = col_config.get('source_column')
                target_col = col_config.get('target_column', source_col)
                
                # Check if source column exists
                if source_col not in df.columns:
                    logger.warning(f"Column '{source_col}' not found in CSV. Skipping.")
                    continue
                
                summary['columns_selected'] += 1
                
                # Get column data
                col_data = df[source_col].copy()
                
                # Apply transformations
                if 'transformations' in col_config:
                    col_data = DataTransformService._apply_transformations(
                        col_data, col_config['transformations']
                    )
                    summary['transformations_applied'] += len(col_config['transformations'])
                
                # Convert to target type
                if 'data_type' in col_config:
                    col_data = DataTransformService._convert_to_type(
                        col_data, 
                        col_config['data_type'],
                        col_config
                    )
                    summary['type_conversions'] += 1
                
                # Handle default values
                if 'default_value' in col_config and col_config['default_value'] is not None:
                    col_data = col_data.fillna(col_config['default_value'])
                
                # Add to result
                result_df[target_col] = col_data
                
                if target_col != source_col:
                    summary['columns_renamed'] += 1
        
        # Add calculated columns
        if 'calculated_columns' in schema:
            for calc_col in schema['calculated_columns']:
                target_col = calc_col.get('target_column')
                formula = calc_col.get('formula')
                
                if not target_col or not formula:
                    logger.warning(f"Invalid calculated column config: {calc_col}")
                    continue
                
                try:
                    # Evaluate formula
                    result_df[target_col] = FormulaParser.evaluate_formula(result_df, formula)
                    
                    # Convert to specified type if provided
                    if 'data_type' in calc_col:
                        result_df[target_col] = DataTransformService._convert_to_type(
                            result_df[target_col],
                            calc_col['data_type'],
                            {}
                        )
                    
                    summary['calculated_columns_added'] += 1
                    logger.info(f"Added calculated column: {target_col}")
                
                except Exception as e:
                    logger.error(f"Failed to calculate column '{target_col}': {str(e)}")
        
        # Filter rows with required fields
        original_row_count = len(result_df)
        
        if 'columns' in schema:
            for col_config in schema['columns']:
                if col_config.get('required', False):
                    target_col = col_config.get('target_column', col_config.get('source_column'))
                    if target_col in result_df.columns:
                        result_df = result_df.dropna(subset=[target_col])
        
        summary['rows_skipped'] = original_row_count - len(result_df)
        
        logger.info(f"Schema transformation summary: {summary}")
        return result_df, summary

    @staticmethod
    def _convert_to_type(series: pd.Series, data_type: str, config: Dict[str, Any]) -> pd.Series:
        """Convert series to specified data type"""
        try:
            if data_type == 'string':
                return series.astype(str).replace('nan', '')
            
            elif data_type == 'integer':
                return pd.to_numeric(series, errors='coerce').fillna(0).astype('Int64')
            
            elif data_type == 'float':
                return pd.to_numeric(series, errors='coerce')
            
            elif data_type == 'date' or data_type == 'datetime':
                date_format = config.get('date_format', '%d/%m/%Y')
                return pd.to_datetime(series, format=date_format, errors='coerce')
            
            elif data_type == 'boolean':
                return series.map({
                    'true': True, 'True': True, 'TRUE': True, '1': True, 1: True, 'yes': True,
                    'false': False, 'False': False, 'FALSE': False, '0': False, 0: False, 'no': False
                })
            
            return series
        
        except Exception as e:
            logger.warning(f"Type conversion to {data_type} failed: {str(e)}")
            return series

    @staticmethod
    def _apply_transformations(series: pd.Series, transformations: List[str]) -> pd.Series:
        """Apply list of transformations to a series"""
        for transform in transformations:
            if transform == 'trim':
                series = series.apply(lambda x: x.strip() if isinstance(x, str) else x)
            elif transform == 'uppercase':
                series = series.apply(lambda x: x.upper() if isinstance(x, str) else x)
            elif transform == 'lowercase':
                series = series.apply(lambda x: x.lower() if isinstance(x, str) else x)
            elif transform == 'title_case':
                series = series.apply(lambda x: x.title() if isinstance(x, str) else x)
            elif transform == 'remove_special_chars':
                series = series.apply(lambda x: DataCleaner.remove_special_characters(x) if isinstance(x, str) else x)
            elif transform == 'remove_extra_spaces':
                series = series.apply(lambda x: DataCleaner.remove_extra_spaces(x) if isinstance(x, str) else x)
        
        return series

    @staticmethod
    def _export_result(df: pd.DataFrame, table_name: str, output_format: str = 'csv') -> str:
        """Export transformed dataframe to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == 'csv':
            output_path = settings.DOWNLOADS_DIR / f"{table_name}_{timestamp}.csv"
            df.to_csv(output_path, index=False)
        
        elif output_format == 'excel':
            output_path = settings.DOWNLOADS_DIR / f"{table_name}_{timestamp}.xlsx"
            df.to_excel(output_path, index=False, engine='openpyxl')
        
        elif output_format == 'json':
            output_path = settings.DOWNLOADS_DIR / f"{table_name}_{timestamp}.json"
            df.to_json(output_path, orient='records', indent=2)
        
        elif output_format == 'parquet':
            output_path = settings.DOWNLOADS_DIR / f"{table_name}_{timestamp}.parquet"
            df.to_parquet(output_path, index=False)
        
        else:
            # Default to CSV
            output_path = settings.DOWNLOADS_DIR / f"{table_name}_{timestamp}.csv"
            df.to_csv(output_path, index=False)
        
        logger.info(f"Exported to: {output_path}")
        return str(output_path)