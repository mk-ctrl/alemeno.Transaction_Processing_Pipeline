import logging
import time
import json
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field
import google.generativeai as genai
from config.settings import settings

logger = logging.getLogger("alemeno.services.llm")

# Configure Google Gemini AI SDK
if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_gemini_"):
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not configured or is using the placeholder. LLM calls will fail if not mocked.")

# 1. Pydantic contracts for Structured outputs

VALID_CATEGORIES = Literal[
    "Food",
    "Shopping",
    "Travel",
    "Transport",
    "Utilities",
    "Cash Withdrawal",
    "Entertainment",
    "Other"
]

class CategoryAssignment(BaseModel):
    temp_id: str
    category: VALID_CATEGORIES

class BatchCategoryResponse(BaseModel):
    assignments: List[CategoryAssignment]

class ExecutiveSummaryResponse(BaseModel):
    total_spend_inr: float
    total_spend_usd: float
    top_merchants: List[str] = Field(..., max_length=3)
    anomaly_count: int
    narrative: str
    risk_level: Literal["low", "medium", "high"]


# Helper for retries with exponential backoff
def call_llm_with_retry(model, prompt: str, schema_class, max_retries: int = 3, initial_delay: float = 2.0):
    """
    Executes a structured content generation call to Gemini with exponential backoff.
    """
    delay = initial_delay
    last_exception = None
    
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=schema_class
    )
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Attempting Gemini call {attempt}/{max_retries}...")
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            # Parse response text as JSON and validate using Pydantic model
            data = json.loads(response.text)
            return schema_class(**data)
        except Exception as e:
            logger.warning(f"Gemini API invocation attempt {attempt} failed: {e}")
            last_exception = e
            if attempt == max_retries:
                break
            time.sleep(delay)
            delay *= 2
            
    raise last_exception or RuntimeError("Gemini API call failed.")


def classify_uncategorised_batch(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identifies 'Uncategorised' rows, packages them into a single batch, and queries Gemini
    to classify them into constrained enums. Handles retry backoffs.
    """
    # 1. Gather indexes of uncategorised items
    uncategorised_indices = [
        idx for idx, txn in enumerate(transactions)
        if txn.get("category") == "Uncategorised"
    ]
    
    if not uncategorised_indices:
        logger.info("No uncategorised transactions found for batch LLM classification.")
        return transactions

    logger.info(f"Bundling {len(uncategorised_indices)} uncategorised transactions for batch LLM categorization...")
    
    # 2. Package into a payload with temp_id mapped to stringified index
    batch_payload = []
    for idx in uncategorised_indices:
        txn = transactions[idx]
        batch_payload.append({
            "temp_id": str(idx),
            "merchant": txn.get("merchant"),
            "amount": txn.get("amount"),
            "currency": txn.get("currency"),
            "notes": txn.get("notes")
        })
        
    prompt = (
        "Classify the following transactions into one of these categories: "
        "Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other.\n"
        f"Input Transactions:\n{json.dumps(batch_payload, indent=2)}\n"
        "Return assignments matching the requested schema."
    )
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        structured_resp: BatchCategoryResponse = call_llm_with_retry(
            model=model,
            prompt=prompt,
            schema_class=BatchCategoryResponse
        )
        
        # 3. Map classifications back
        for assignment in structured_resp.assignments:
            try:
                target_idx = int(assignment.temp_id)
                transactions[target_idx]["category"] = assignment.category
                transactions[target_idx]["llm_failed"] = False
                logger.debug(f"Classified index {target_idx} to category: {assignment.category}")
            except (ValueError, IndexError):
                logger.error(f"LLM returned invalid temp_id mapping: {assignment.temp_id}")
                
    except Exception as err:
        logger.error(f"All batch LLM categorization attempts failed: {err}. Flagging rows as llm_failed.")
        for idx in uncategorised_indices:
            transactions[idx]["llm_failed"] = True
            
    return transactions


def generate_executive_summary(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates summary metrics of the processing pipeline, submits analysis to Gemini,
    and returns a structured JSON Executive Summary response.
    """
    logger.info("Generating executive summary via Gemini...")
    
    # Calculate metadata metrics for the prompt context
    total_spend_inr = sum(t["amount"] for t in transactions if t.get("currency") == "INR" and t.get("amount") is not None)
    total_spend_usd = sum(t["amount"] for t in transactions if t.get("currency") == "USD" and t.get("amount") is not None)
    anomaly_count = sum(1 for t in transactions if t.get("is_anomaly") is True)
    
    # Package clean transaction subsets for summary analysis context
    transaction_summaries = []
    for t in transactions:
        transaction_summaries.append({
            "txn_id": t.get("txn_id"),
            "merchant": t.get("merchant"),
            "amount": t.get("amount"),
            "currency": t.get("currency"),
            "category": t.get("category"),
            "is_anomaly": t.get("is_anomaly"),
            "anomaly_reason": t.get("anomaly_reason")
        })
        
    prompt = (
        "Analyze the following transactions dataset and generate an executive narrative report.\n"
        f"Global Ingestion Metrics:\n"
        f"- Total Spend INR: {total_spend_inr:.2f}\n"
        f"- Total Spend USD: {total_spend_usd:.2f}\n"
        f"- Anomaly Count: {anomaly_count}\n\n"
        f"Transaction Details:\n{json.dumps(transaction_summaries[:50], indent=2)}\n\n"
        "Generate the summary JSON payload containing: total_spend_inr, total_spend_usd, "
        "top_merchants (exactly 3 highest spend/frequency merchants), anomaly_count, "
        "narrative (a tight 2-to-3 sentence executive behavioral overview), and risk_level (low, medium, or high)."
    )
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        structured_resp: ExecutiveSummaryResponse = call_llm_with_retry(
            model=model,
            prompt=prompt,
            schema_class=ExecutiveSummaryResponse
        )
        return structured_resp.model_dump()
    except Exception as err:
        logger.error(f"Failed to generate executive summary from Gemini: {err}. Falling back to default metrics.")
        # Safe fallback summary structure
        return {
            "total_spend_inr": total_spend_inr,
            "total_spend_usd": total_spend_usd,
            "top_merchants": [],
            "anomaly_count": anomaly_count,
            "narrative": "Pipeline finished processing. Gemini narrative summary was unavailable due to service error.",
            "risk_level": "medium"
        }
