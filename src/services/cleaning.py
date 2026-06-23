import csv
import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("alemeno.services.cleaning")

DATE_FORMATS = [
    "%d-%m-%Y",  # e.g., 04-09-2024
    "%Y/%m/%d",  # e.g., 2024/02/05
    "%Y-%m-%d",  # e.g., 2024-07-15
]

def parse_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    """
    Normalizes variable date formats from CSV to strict ISO 8601 (YYYY-MM-DD) strings.
    """
    if not date_str or not date_str.strip():
        return None
    
    cleaned_date = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed_dt = datetime.strptime(cleaned_date, fmt)
            return parsed_dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    logger.warning(f"Unable to parse date string: {date_str}. Returning raw value.")
    return cleaned_date

def clean_amount(amount_str: Optional[str]) -> Optional[float]:
    """
    Strips literal currency markers (like $) and parses amount value into a float.
    """
    if not amount_str or not amount_str.strip():
        return None
    
    cleaned = amount_str.strip()
    # Strip common currency symbols
    cleaned = cleaned.replace("$", "").replace("₹", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        logger.error(f"Failed to cast amount to float: {amount_str}")
        return None

def clean_status(status_str: Optional[str]) -> str:
    """
    Forces status tags to uppercase. Defaults to 'PENDING' if blank.
    """
    if not status_str or not status_str.strip():
        return "PENDING"
    return status_str.strip().upper()

def clean_currency(currency_str: Optional[str]) -> str:
    """
    Forces currency strings to consistent uppercase. Defaults to 'INR'.
    """
    if not currency_str or not currency_str.strip():
        return "INR"
    return currency_str.strip().upper()

def clean_category(category_str: Optional[str]) -> str:
    """
    Maps missing/blank categories to 'Uncategorised'.
    """
    if not category_str or not category_str.strip():
        return "Uncategorised"
    return category_str.strip()

def parse_and_clean_csv(csv_content: str) -> Tuple[List[Dict[str, Any]], int]:
    """
    Reads raw CSV string data, parses columns, applies cleaning/normalization rules,
    and removes exact duplicate records.
    """
    logger.info("Starting CSV data ingestion parsing and cleaning lifecycle...")
    
    # Read rows using built-in DictReader
    f = io.StringIO(csv_content.strip())
    reader = csv.DictReader(f)
    
    # Normalize headers dynamically to be case-insensitive, strip whitespace, and map synonyms
    if reader.fieldnames:
        normalized_fieldnames = []
        for name in reader.fieldnames:
            if name:
                # Lowercase, strip surrounding whitespaces, and replace spaces/hyphens with underscores
                n = name.strip().lower().replace(" ", "_").replace("-", "_")
                
                # Check for common header synonyms and map to our standard fields
                if n in ["txn_id", "transaction_id", "transactionid", "tx_id", "txnid", "id"]:
                    n = "txn_id"
                elif n in ["account_id", "accountid", "account_no", "account_number", "acc_id"]:
                    n = "account_id"
                elif n in ["date", "txn_date", "transaction_date"]:
                    n = "date"
                elif n in ["merchant", "vendor", "payee"]:
                    n = "merchant"
                elif n in ["amount", "value", "price"]:
                    n = "amount"
                elif n in ["currency", "curr"]:
                    n = "currency"
                elif n in ["status", "txn_status"]:
                    n = "status"
                elif n in ["category", "cat"]:
                    n = "category"
                elif n in ["notes", "note", "description", "desc"]:
                    n = "notes"
                normalized_fieldnames.append(n)
            else:
                normalized_fieldnames.append("")
        reader.fieldnames = normalized_fieldnames
    
    cleaned_rows: List[Dict[str, Any]] = []
    seen_signatures = set()
    
    row_idx = 0
    for row_idx, row in enumerate(reader, start=1):
        # Extract fields (fallback to empty string if missing)
        txn_id = (row.get("txn_id") or "").strip() or None
        date = (row.get("date") or "").strip() or None
        merchant = (row.get("merchant") or "").strip() or None
        amount_raw = (row.get("amount") or "").strip() or None
        currency_raw = (row.get("currency") or "").strip() or None
        status_raw = (row.get("status") or "").strip() or None
        category_raw = (row.get("category") or "").strip() or None
        account_id = (row.get("account_id") or "").strip() or None
        notes = (row.get("notes") or "").strip() or None

        # Apply cleaning filters
        iso_date = parse_date_to_iso(date)
        numeric_amount = clean_amount(amount_raw)
        upper_currency = clean_currency(currency_raw)
        upper_status = clean_status(status_raw)
        category = clean_category(category_raw)

        # Generate a distinct signature to detect duplicate lines.
        # Include key structural values. If txn_id is missing, we use other values to evaluate.
        signature = (
            txn_id,
            iso_date,
            merchant,
            numeric_amount,
            upper_currency,
            upper_status,
            category,
            account_id
        )
        
        if signature in seen_signatures:
            logger.debug(f"Row {row_idx}: Duplicate record detected and stripped: txn_id={txn_id}")
            continue
            
        seen_signatures.add(signature)
        
        cleaned_rows.append({
            "txn_id": txn_id,
            "date": iso_date,
            "merchant": merchant,
            "amount": numeric_amount,
            "currency": upper_currency,
            "status": upper_status,
            "category": category,
            "account_id": account_id,
            "notes": notes
        })

    logger.info(f"Ingestion completed. Processed {row_idx} rows. Extracted {len(cleaned_rows)} unique cleaned records.")
    return cleaned_rows, row_idx
