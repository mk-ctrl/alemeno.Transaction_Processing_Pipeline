import logging
from typing import List, Dict, Any

logger = logging.getLogger("alemeno.services.anomaly")

DOMESTIC_BRANDS = ["swiggy", "ola", "irctc"]

def calculate_median(values: List[float]) -> float:
    """
    Computes the mathematical median of a list of numeric values.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 != 0:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

def detect_anomalies(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates transaction records for anomaly rules:
    1. Statistical Outlier: amount > 3x the median transaction value of the specific account_id.
    2. Logical Rule: currency is USD and merchant name matches domestic Indian brands (Swiggy, Ola, IRCTC).
    """
    logger.info("Executing outlier and anomaly detection services...")
    
    # Step 1: Group amounts by account_id to compute medians
    account_amounts: Dict[str, List[float]] = {}
    for txn in transactions:
        account_id = txn.get("account_id")
        amount = txn.get("amount")
        if account_id and amount is not None:
            account_amounts.setdefault(account_id, []).append(amount)
            
    # Calculate medians for each account
    account_medians: Dict[str, float] = {
        acc_id: calculate_median(amounts)
        for acc_id, amounts in account_amounts.items()
    }
    
    logger.info(f"Calculated medians for {len(account_medians)} unique account IDs.")
    
    # Step 2: Apply anomaly criteria
    for txn in transactions:
        reasons = []
        is_anomaly = False
        
        amount = txn.get("amount")
        account_id = txn.get("account_id")
        currency = txn.get("currency")
        merchant = txn.get("merchant") or ""
        
        # 1. Outlier Check: amount > 3 * account median
        if account_id and amount is not None:
            median = account_medians[account_id]
            # Verify threshold condition (greater than 3x the account median)
            if amount > 3 * median:
                is_anomaly = True
                reasons.append(
                    f"Outlier: Amount {amount:.2f} is strictly greater than 3x the account median {median:.2f}"
                )
                
        # 2. Logical Check: Domestic brand billed in USD
        if currency == "USD" and merchant:
            merchant_lower = merchant.lower()
            if any(brand in merchant_lower for brand in DOMESTIC_BRANDS):
                is_anomaly = True
                reasons.append(
                    f"Mismatched Currency: Domestic brand '{merchant}' billed in USD"
                )
                
        # Populate anomalies properties on transaction dictionary
        txn["is_anomaly"] = is_anomaly
        txn["anomaly_reason"] = "; ".join(reasons) if is_anomaly else None
        
        if is_anomaly:
            logger.debug(
                f"Flagged anomaly on txn_id={txn.get('txn_id')}: {txn['anomaly_reason']}"
            )

    logger.info("Outlier and anomaly detection processing completed.")
    return transactions
