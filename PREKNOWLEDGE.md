# Preknowledge Blueprint: AI-Powered Transaction Processing Pipeline

## 1. System Overview
The objective is to build a high-performance, containerized, asynchronous backend pipeline that ingests a dirty CSV financial export, processes records out-of-band using a job queue, applies custom statistical rules and LLM validation/summarization, and stores the structured results in a relational database.

## 2. Technical Stack Specifications
- **API Framework:** FastAPI (Python) with automated OpenAPI/Swagger documentation (`/docs`).
- **Database:** PostgreSQL utilizing SQLAlchemy ORM for relational mapping and schema safety.
- **Asynchronous Task Queue:** Celery with Redis acting as the message broker.
- **AI/LLM Engine:** Gemini 1.5 Flash (via the Google AI SDK) utilizing native structured JSON output constraints.
- **Infrastructure:** Docker and Docker Compose. The entire application must provision seamlessly via `docker compose up` with zero manual intervention.

## 3. Architecture Blueprint (Domain-Layered Structure)
The project must adhere strictly to a production-grade, decoupled folder layout to ensure isolation of concerns:
```text
config/              # Centralized environment variables & settings (Pydantic)
src/
  ├── api/           # API routes, request parameters, endpoint handlers
  ├── core/          # Core infrastructure (DB session config, engine creation)
  ├── models/        # Relational PostgreSQL SQLAlchemy Database blueprints
  ├── schemas/       # Input/Output Pydantic data validation contracts
  ├── services/      # Pure business logic (Data Cleaning, LLM Client wrappers)
  └── workers/       # Celery application initialization and task consumer definitions
```

## 4. API Endpoint Definitions & Lifecycle

The API handles state transition tracking using a polling model rather than processing heavy operations within the HTTP lifecycle:

* `POST /jobs/upload`: Accepts a raw CSV upload, initializes a database log with status `pending`, pushes the `job_id` to Redis, and instantly responds with the ID.
* `GET /jobs/{job_id}/status`: Polls tracking metrics. Returns: `pending`, `processing`, `completed`, or `failed`.
* `GET /jobs/{job_id}/results`: Fetches full structural data (cleaned rows, anomalies, breakdown, narrative).
* `GET /jobs`: Lists all historic runs with optional filtering query parameters `?status=`.

## 5. Sequential Processing Pipeline Rules (Celery Worker Logic)

When the worker picks up a `job_id` from the Redis queue, it must execute these precise steps in strict sequential order:

### Layer A: Data Ingestion & Relational Creation

* Parse the raw `transactions.csv` bytes.
* Create **one** parent metadata record in the `Job` table.
* Create **individual** placeholder rows in the `Transaction` table linked back to the parent `job_id` via a Foreign Key relation.

### Layer B: Core Data Normalization & Cleaning

* Format all mismatched text dates to strict ISO 8601 strings.
* Strip literal string markers (e.g., `$`) from the `amount` column, keeping values numeric.
* Force all `status` markers (`SUCCESS`, `FAILED`, `PENDING`) to consistent uppercase.
* Inspect empty string fields in the `category` column and initialize them with the string `"Uncategorised"`.
* Strip matching duplicate line entries out entirely.

### Layer C: Statistical Outlier & Anomaly Detection (Pure Python Logic)

* **Outlier Logic:** Group rows by `account_id` and compute the mathematical **median** transaction value per account. If an individual record's `amount` is strictly greater than 3x that calculated account median, flag it with `is_anomaly = True` and populate `anomaly_reason`.
* **Logical Rules:** Evaluate rows where the currency value evaluates to `USD`. If the merchant name contains domestic-only brands (specifically: `Swiggy`, `Ola`, or `IRCTC`), flag it as an anomaly.

### Layer D: Batched LLM Classification

* Aggregate all transactions that have been labeled `"Uncategorised"`.
* **Constraint:** Do not make a separate LLM API request per transaction. Bundle these rows into a single structured batch call.
* Instruct the LLM to choose a matching category label strictly constrained to this exact enum: `Food`, `Shopping`, `Travel`, `Transport`, `Utilities`, `Cash Withdrawal`, `Entertainment`, or `Other`.
* Handle failures by utilizing exponential backoff retries up to 3 times. If all retries fail, mark the specific row batch as `llm_failed = True` and let the task continue.

### Layer E: Structured Narrative Executive Summary

* Compile the global metrics of the finalized file.
* Fire a single, final structured text block request to the LLM to analyze the entire data cluster.
* **Enforced JSON Output Contract:** The LLM must return a valid JSON payload matching these keys:
* `total_spend_inr`: Floating-point total.
* `total_spend_usd`: Floating-point total.
* `top_merchants`: Array of strings identifying the 3 highest velocity merchants.
* `anomaly_count`: Integer representing total flagged items.
* `narrative`: A tight 2-to-3 sentence executive behavioral overview.
* `risk_level`: A strict text token rating of either `low`, `medium`, or `high`.


* Persist this data format directly into a linked relational table or database field.
* Mark the parent job tracker record as `completed`.
