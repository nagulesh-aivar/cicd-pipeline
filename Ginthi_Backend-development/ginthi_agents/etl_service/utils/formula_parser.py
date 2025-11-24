import pandas as pd
import numpy as np
import re
from typing import Any, Dict


class FormulaParser:
    """
    Parse and evaluate formulas for calculated columns
    """

    @staticmethod
    def evaluate_formula(df: pd.DataFrame, formula: str) -> pd.Series:
        """
        Evaluate a formula using dataframe columns
        
        Supported operations:
        - Arithmetic: +, -, *, /, %
        - Functions: SUM, AVG, MIN, MAX, ABS, ROUND
        - Conditional: IF(condition, true_val, false_val)
        
        Examples:
        - "price * quantity"
        - "received_qty - returned_qty"
        - "IF(tax > 0, price * (1 + tax/100), price)"
        """
        try:
            # Handle IF statements first
            if 'IF(' in formula.upper():
                return FormulaParser._evaluate_if_statement(df, formula)
            
            # Handle functions
            if any(func in formula.upper() for func in ['SUM', 'AVG', 'MIN', 'MAX', 'ABS', 'ROUND']):
                return FormulaParser._evaluate_functions(df, formula)
            
            # Simple arithmetic evaluation using pandas eval
            return df.eval(formula)
        
        except Exception as e:
            print(f"Error evaluating formula '{formula}': {str(e)}")
            return pd.Series([np.nan] * len(df))

    @staticmethod
    def _evaluate_if_statement(df: pd.DataFrame, formula: str) -> pd.Series:
        """
        Evaluate IF(condition, true_value, false_value) statements
        
        Example: IF(tax > 0, price * 1.05, price)
        """
        # Extract IF statement pattern
        pattern = r'IF\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)'
        match = re.search(pattern, formula, re.IGNORECASE)
        
        if not match:
            raise ValueError(f"Invalid IF statement: {formula}")
        
        condition = match.group(1).strip()
        true_value = match.group(2).strip()
        false_value = match.group(3).strip()
        
        # Evaluate condition
        condition_result = df.eval(condition)
        
        # Evaluate true and false branches
        true_result = FormulaParser.evaluate_formula(df, true_value) if not true_value.replace('.','').isdigit() else float(true_value)
        false_result = FormulaParser.evaluate_formula(df, false_value) if not false_value.replace('.','').isdigit() else float(false_value)
        
        # Apply condition
        return pd.Series(np.where(condition_result, true_result, false_result))

    @staticmethod
    def _evaluate_functions(df: pd.DataFrame, formula: str) -> pd.Series:
        """
        Evaluate functions like SUM, AVG, MIN, MAX, ABS, ROUND
        """
        formula_upper = formula.upper()
        
        # ROUND(column, decimals)
        if 'ROUND(' in formula_upper:
            pattern = r'ROUND\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)'
            match = re.search(pattern, formula, re.IGNORECASE)
            if match:
                col_expr = match.group(1).strip()
                decimals = int(match.group(2))
                
                # Evaluate the expression inside ROUND
                result = FormulaParser.evaluate_formula(df, col_expr)
                return result.round(decimals)
        
        # ABS(column)
        if 'ABS(' in formula_upper:
            pattern = r'ABS\s*\(\s*([^)]+)\s*\)'
            match = re.search(pattern, formula, re.IGNORECASE)
            if match:
                col_expr = match.group(1).strip()
                result = FormulaParser.evaluate_formula(df, col_expr)
                return result.abs()
        
        # For aggregation functions, return scalar applied to all rows
        # SUM(column)
        if 'SUM(' in formula_upper:
            pattern = r'SUM\s*\(\s*([^)]+)\s*\)'
            match = re.search(pattern, formula, re.IGNORECASE)
            if match:
                col_name = match.group(1).strip()
                total = df[col_name].sum()
                return pd.Series([total] * len(df))
        
        # AVG(column)
        if 'AVG(' in formula_upper:
            pattern = r'AVG\s*\(\s*([^)]+)\s*\)'
            match = re.search(pattern, formula, re.IGNORECASE)
            if match:
                col_name = match.group(1).strip()
                avg = df[col_name].mean()
                return pd.Series([avg] * len(df))
        
        # MIN(column)
        if 'MIN(' in formula_upper:
            pattern = r'MIN\s*\(\s*([^)]+)\s*\)'
            match = re.search(pattern, formula, re.IGNORECASE)
            if match:
                col_name = match.group(1).strip()
                minimum = df[col_name].min()
                return pd.Series([minimum] * len(df))
        
        # MAX(column)
        if 'MAX(' in formula_upper:
            pattern = r'MAX\s*\(\s*([^)]+)\s*\)'
            match = re.search(pattern, formula, re.IGNORECASE)
            if match:
                col_name = match.group(1).strip()
                maximum = df[col_name].max()
                return pd.Series([maximum] * len(df))
        
        # If no function matched, try simple eval
        return df.eval(formula)

    @staticmethod
    def validate_formula(df: pd.DataFrame, formula: str) -> tuple:
        """
        Validate if a formula is valid
        Returns: (is_valid, error_message)
        """
        try:
            # Check if columns referenced in formula exist
            # Extract potential column names (simple heuristic)
            potential_cols = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', formula)
            
            for col in potential_cols:
                if col.upper() not in ['IF', 'SUM', 'AVG', 'MIN', 'MAX', 'ABS', 'ROUND', 'AND', 'OR', 'NOT']:
                    if col not in df.columns:
                        return False, f"Column '{col}' not found in dataframe"
            
            # Try to evaluate
            result = FormulaParser.evaluate_formula(df.head(5), formula)
            
            if result is None or len(result) == 0:
                return False, "Formula evaluation returned no results"
            
            return True, "Valid formula"
        
        except Exception as e:
            return False, f"Formula validation error: {str(e)}"