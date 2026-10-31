"""
Data Masking Utilities for DataPulse.
Ensures personal data values are masked by default to uphold privacy-by-design.
"""
import re
from typing import Any, Optional

def mask_email(val: str) -> str:
    """Mask email while preserving domain structure: j***e@example.com"""
    if not val or "@" not in val:
        return "[MASKED EMAIL]"
    parts = val.split("@", 1)
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "***"
    else:
        masked_user = user[0] + "*" * (len(user) - 2) + user[-1]
    return f"{masked_user}@{domain}"

def mask_phone(val: str) -> str:
    """Mask all phone digits except the last four."""
    if not val:
        return "[MASKED PHONE]"

    clean = str(val).strip()
    digits = re.sub(r"\D", "", clean)

    if len(digits) < 7:
        return "***-****"

    return "*" * (len(digits) - 4) + digits[-4:]

def mask_name(val: str) -> str:
    """Mask person name: John Doe -> J*** D**"""
    if not val:
        return "[MASKED NAME]"
    words = str(val).strip().split()
    masked_words = []
    for w in words:
        if len(w) <= 2:
            masked_words.append(w[0] + "*")
        else:
            masked_words.append(w[0] + "*" * (len(w) - 1))
    return " ".join(masked_words)

def mask_dob(val: str) -> str:
    """Mask month and day of birth date: 1985-**-**"""
    if not val:
        return "[MASKED DOB]"

    clean = str(val).strip()

    # Match YYYY-MM-DD, YYYY/MM/DD, or YYYY.MM.DD
    m = re.match(r"^(\d{4})[-/.].*$", clean)

    if m:
        return f"{m.group(1)}-**-**"

    return "****-**-**"

def mask_gov_id(val: str) -> str:
    """Mask government ID surrogate: FICTIONAL-ID-00101 -> FICT****-00101"""
    if not val:
        return "[MASKED GOV ID]"
    clean = str(val).strip()
    if clean.upper().startswith("FICTIONAL-ID-"):
        suffix = clean.split("-")[-1]
        return f"FICT****-{suffix}"
    if len(clean) > 4:
        return clean[:2] + "****" + clean[-2:]
    return "****"

def mask_value_by_category(value: Any, category: str) -> str:
    """
    Returns masked value according to detected personal data category.
    If category is NONE or empty, returns original value as string.
    """
    if value is None:
        return "<NULL>"
    str_val = str(value)
    if str_val.strip() == "":
        return "<EMPTY>"

    cat = category.upper() if category else "NONE"
    if cat == "EMAIL":
        return mask_email(str_val)
    elif cat == "PHONE":
        return mask_phone(str_val)
    elif cat == "PERSON_NAME":
        return mask_name(str_val)
    elif cat == "DATE_OF_BIRTH":
        return mask_dob(str_val)
    elif cat == "GOVERNMENT_ID":
        return mask_gov_id(str_val)
    return str_val

def mask_record_dict(record: dict, column_categories: dict) -> dict:
    """
    Masks a full record dictionary according to column categories map.
    column_categories: {column_name: detected_category}
    """
    masked = {}
    for col, val in record.items():
        cat = column_categories.get(col, "NONE")
        masked[col] = mask_value_by_category(val, cat)
    return masked
