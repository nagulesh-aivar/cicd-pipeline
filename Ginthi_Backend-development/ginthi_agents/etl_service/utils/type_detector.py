import pandas as pd
import numpy as np
from datetime import datetime
from typing import Any, List


class TypeDetector:
    """
    Utility class to automatically detect data types of columns
    """

    @staticmethod
    def is_integer(value: Any) -> bool:
        """Check if value can be converted to integer"""
        if pd.isna(value) or value in [None, '', '-', ' ']:
            return True  # NULLs are acceptable
        try:
            float_val = float(str(value).strip())
            return float_val == int(float_val)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_float(value: Any) -> bool:
        """Check if value can be converted to float"""
        if pd.isna(value) or value in [None, '', '-', ' ']:
            return True  # NULLs are acceptable
        try:
            float(str(value).strip())
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_date(value: Any) -> bool:
        """Check if value can be converted to date"""
        if pd.isna(value) or value in [None, '', '-', ' ']:
            return True  # NULLs are acceptable
        
        value_str = str(value).strip()
        
        # Common date formats
        date_formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%d.%m.%Y',
            '%d %b %Y',
            '%d %B %Y'
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(value_str, fmt)
                return True
            except (ValueError, TypeError):
                continue
        return False

    @staticmethod
    def is_boolean(value: Any) -> bool:
        """Check if value is boolean"""
        if pd.isna(value) or value in [None, '', '-', ' ']:
            return True
        
        value_str = str(value).strip().lower()
        return value_str in ['true', 'false', '0', '1', 'yes', 'no', 't', 'f', 'y', 'n']

    @staticmethod
    def detect_column_type(series: pd.Series) -> str:
        """
        Detect the most appropriate data type for a pandas Series
        
        Returns: 'integer', 'float', 'date', 'boolean', or 'string'
        """
        # Remove NULL values for detection
        clean_series = series.dropna()
        clean_series = clean_series[~clean_series.isin(['', '-', ' '])]
        
        if len(clean_series) == 0:
            return 'string'  # Default if all NULL
        
        # Sample for performance (check first 1000 values)
        sample_size = min(1000, len(clean_series))
        sample = clean_series.head(sample_size)
        
        # Try Boolean first (most restrictive)
        if all(TypeDetector.is_boolean(v) for v in sample):
            return 'boolean'
        
        # Try Integer
        if all(TypeDetector.is_integer(v) for v in sample):
            return 'integer'
        
        # Try Float
        if all(TypeDetector.is_float(v) for v in sample):
            return 'float'
        
        # Try Date
        if all(TypeDetector.is_date(v) for v in sample):
            return 'date'
        
        # Default to String
        return 'string'

    @staticmethod
    def detect_date_format(series: pd.Series) -> str:
        """
        Detect the date format used in a series
        """
        clean_series = series.dropna()
        clean_series = clean_series[~clean_series.isin(['', '-', ' '])]
        
        if len(clean_series) == 0:
            return '%Y-%m-%d'  # Default
        
        # Try common formats
        date_formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%d.%m.%Y'
        ]
        
        sample = clean_series.head(100)
        
        for fmt in date_formats:
            try:
                success_count = 0
                for val in sample:
                    try:
                        datetime.strptime(str(val).strip(), fmt)
                        success_count += 1
                    except:
                        pass
                
                # If more than 80% match, consider it the format
                if success_count / len(sample) > 0.8:
                    return fmt
            except:
                continue
        
        return '%d/%m/%Y'  # Default fallback