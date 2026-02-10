"""
Utility functions: Logging, input parsing, and common helpers.
"""

import datetime
from pathlib import Path


def convert_arabic_digits(text: str) -> str:
    """
    Convert Arabic numerals (٠-٩) to English (0-9).
    
    Args:
        text: Input string
        
    Returns:
        String with converted digits
    """
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    trans = str.maketrans("".join(arabic_digits), "0123456789")
    return text.translate(trans)


def safe_int(text: str, default=None) -> int:
    """
    Safely parse integer from user input, handling Arabic digits.
    
    Args:
        text: User input string
        default: Default value if parsing fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(convert_arabic_digits(text.strip()))
    except (ValueError, TypeError):
        return default


def log(log_file: Path, message: str) -> None:
    """
    Append timestamped log message to file.
    
    Args:
        log_file: Path to log file
        message: Message to log
    """
    timestamp = datetime.datetime.utcnow().isoformat()
    log_message = f"{timestamp}: {message}\n"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message)