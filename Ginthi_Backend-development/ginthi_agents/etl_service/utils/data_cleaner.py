import pandas as pd
import numpy as np
import re
from typing import Any


class DataCleaner:
    """
    Utility class for data cleaning operations
    """

    @staticmethod
    def clean_null_values(df: pd.DataFrame) -> pd.DataFrame:
        """
        Replace common NULL representations with actual NULL
        Handles: '-', '', ' ', 'null', 'NULL', 'N/A', 'n/a', etc.
        """
        null_representations = ['-', '', ' ', 'null', 'NULL', 'N/A', 'n/a', 'NA', 'None', 'none']
        
        # Replace all null representations with NaN
        df = df.replace(null_representations, np.nan)
        
        # Also handle whitespace-only strings
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(lambda x: np.nan if isinstance(x, str) and x.strip() == '' else x)
        
        return df

    @staticmethod
    def trim_strings(df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove leading and trailing whitespace from all string columns
        """
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
        
        return df

    @staticmethod
    def remove_special_characters(value: Any, keep_chars: str = '') -> Any:
        """
        Remove special characters from string
        keep_chars: characters to keep (e.g., '.-' to keep dots and hyphens)
        """
        if pd.isna(value) or not isinstance(value, str):
            return value
        
        # Keep alphanumeric and specified characters
        pattern = f'[^a-zA-Z0-9{re.escape(keep_chars)} ]'
        return re.sub(pattern, '', value)

    @staticmethod
    def remove_line_endings(df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove carriage returns and line feeds (^M, \r, \n)
        """
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(
                lambda x: x.replace('\r', '').replace('\n', '').replace('^M', '') 
                if isinstance(x, str) else x
            )
        
        return df

    @staticmethod
    def standardize_text(value: Any, method: str = 'title') -> Any:
        """
        Standardize text casing
        methods: 'upper', 'lower', 'title', 'trim'
        """
        if pd.isna(value) or not isinstance(value, str):
            return value
        
        if method == 'upper':
            return value.upper()
        elif method == 'lower':
            return value.lower()
        elif method == 'title':
            return value.title()
        elif method == 'trim':
            return value.strip()
        
        return value

    @staticmethod
    def remove_duplicates(df: pd.DataFrame, subset: list = None) -> tuple:
        """
        Remove duplicate rows
        Returns: (cleaned_df, number_of_duplicates_removed)
        """
        original_count = len(df)
        
        if subset:
            df_clean = df.drop_duplicates(subset=subset, keep='first')
        else:
            df_clean = df.drop_duplicates(keep='first')
        
        duplicates_removed = original_count - len(df_clean)
        
        return df_clean, duplicates_removed

    @staticmethod
    def remove_extra_spaces(value: Any) -> Any:
        """
        Replace multiple spaces with single space
        """
        if pd.isna(value) or not isinstance(value, str):
            return value
        
        return re.sub(r'\s+', ' ', value).strip()

    @staticmethod
    def clean_numeric_strings(value: Any) -> Any:
        """
        Clean numeric values stored as strings
        Removes: currency symbols, commas, etc.
        """
        if pd.isna(value):
            return value
        
        value_str = str(value).strip()
        
        # Remove currency symbols and commas
        value_str = re.sub(r'[₹$€£,]', '', value_str)
        
        # Try to convert to float
        try:
            return float(value_str)
        except (ValueError, TypeError):
            return value

    @staticmethod
    def validate_numeric_range(series: pd.Series, min_val: float = None, max_val: float = None) -> pd.Series:
        """
        Flag values outside the specified range
        Returns boolean series indicating valid values
        """
        valid = pd.Series([True] * len(series))
        
        if min_val is not None:
            valid &= (series >= min_val) | series.isna()
        
        if max_val is not None:
            valid &= (series <= max_val) | series.isna()
        
        return valid

    @staticmethod
    def handle_outliers(series: pd.Series, method: str = 'iqr', threshold: float = 1.5) -> pd.Series:
        """
        Detect outliers using IQR or Z-score method
        Returns boolean series indicating non-outliers
        """
        if method == 'iqr':
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            return (series >= lower_bound) & (series <= upper_bound) | series.isna()
        
        elif method == 'zscore':
            mean = series.mean()
            std = series.std()
            
            z_scores = np.abs((series - mean) / std)
            
            return (z_scores <= threshold) | series.isna()
        
        return pd.Series([True] * len(series))