import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def group_words_into_lines(words_data: List[Dict]) -> List[List[Dict]]:
    """Group words into lines based on vertical positioning"""
    if not words_data:
        return []
        
    # Sort words by vertical position
    sorted_words = sorted(words_data, key=lambda x: x['bbox']['top'])
    
    lines = []
    current_line = [sorted_words[0]]
    line_tolerance = 10  # pixels
    
    for word in sorted_words[1:]:
        # Check if word is on the same line
        if abs(word['bbox']['top'] - current_line[-1]['bbox']['top']) <= line_tolerance:
            current_line.append(word)
        else:
            # Sort current line by horizontal position
            current_line.sort(key=lambda x: x['bbox']['left'])
            lines.append(current_line)
            current_line = [word]
    
    # Add the last line
    if current_line:
        current_line.sort(key=lambda x: x['bbox']['left'])
        lines.append(current_line)
    
    return lines

def extract_key_value_pairs_advanced(lines: List[List[Dict]]) -> Dict[str, str]:
    """Extract key-value pairs using advanced bounding box analysis"""
    try:
        logger.info("Extracting key-value pairs with advanced positioning analysis...")
        logger.info("Extracting key-value pairs with positioning analysis...")

        key_value_pairs = {}
        if not lines:
            return key_value_pairs

        # Common key patterns
        key_patterns = [
            r'(?:invoice|bill)\s*(?:no|number|#)',
            r'(?:date|dated)',
            r'(?:gst|gstin)\s*(?:no|number)?',
            r'(?:pan|pan\s*no)',
            r'(?:vendor|supplier|company)\s*(?:name)?',
            r'(?:total|grand\s*total|final\s*amount)',
            r'(?:quantity|qty)',
            r'(?:rate|price|amount)',
            r'(?:hsn|sac)',
            r'(?:cgst|sgst|igst)',
            r'(?:taxable|tax)\s*(?:amount|value)',
            r'(?:description|particulars|item)'
        ]

        for line in lines:
            if len(line) < 2:
                continue

            # Reconstruct line text
            line_text = ' '.join([word['text'] for word in line])

            # Look for colon-separated pairs
            if ':' in line_text:
                parts = line_text.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower()
                    value = parts[1].strip()

                    # Check against patterns or add if reasonable
                    for pattern in key_patterns:
                        if re.search(pattern, key, re.IGNORECASE):
                            key_value_pairs[key] = value
                            break
                    else:
                        # Add if it looks reasonable
                        if len(key) > 2 and len(key) < 50 and len(value) > 0 and len(value) < 200:
                            key_value_pairs[key] = value

            # Look for label-value patterns (adjacent words)
            elif len(line) >= 2:
                for i in range(len(line) - 1):
                    key_word = line[i]['text'].lower()
                    value_word = line[i + 1]['text']

                    # Check if key matches patterns
                    for pattern in key_patterns:
                        if re.search(pattern, key_word, re.IGNORECASE):
                            # Check proximity
                            distance = line[i + 1]['bbox']['left'] - (line[i]['bbox']['left'] + line[i]['bbox']['width'])
                            if distance < 100:  # Within 100 pixels
                                key_value_pairs[key_word] = value_word
                            break

        logger.info(f"Extracted {len(key_value_pairs)} key-value pairs")
        return key_value_pairs
        
    except Exception as e:
        logger.error(f"Error in advanced key-value extraction: {e}")
        return {}


def extract_table_data_advanced(lines: List[List[Dict]]) -> List[List[str]]:
    """Extract table data using advanced word positioning"""
    try:
        logger.info("Extracting table data with advanced positioning...")
        table_rows = []
        header_row = None

        if not lines:
            logger.info("No lines provided, returning empty table")
            return []

        for line_idx, line in enumerate(lines):
            if len(line) >= 3:  # Potential table row
                line_text = [word['text'] for word in line]
                if any(keyword in ' '.join(line_text).lower() for keyword in 
                       ['description', 'qty', 'rate', 'amount', 'hsn', 'total', 'particulars', 'item', 'quantity']):
                    header_row = line_text
                    continue
                table_rows.append(line_text)

        # Limit to 50 rows to prevent excessive output
        table_rows = table_rows[:50] if len(table_rows) > 1 else []
        logger.info(f"Extracted {len(table_rows)} table rows")
        return table_rows
        
    except Exception as e:
        logger.error(f"Error in advanced table extraction: {e}")
        return []