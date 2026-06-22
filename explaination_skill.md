# Skill File: Deep Line-by-Line Code Explanation Protocol

## 1. Intent & Objective
[cite_start]The user is a student building an enterprise-grade, asynchronous AI-powered transaction processing pipeline [cite: 11] [cite_start]under a strict 4-day deadline[cite: 12]. [cite_start]To maximize conceptual understanding, accelerate troubleshooting, and perfectly prepare the user for a technical engineering design review video, **no code blocks shall be provided without a comprehensive, sequential, line-by-line explanation.**

## 2. Mandatory Response Format
Whenever a file, configuration script, or block of code is about to be implemented, the response must strictly follow this 3-step structural layer:

### Step A: The "Why" & Architectural Purpose
[cite_start]A brief, high-level summary explaining exactly why this specific code is required, what domain layer it belongs to (e.g., `src/core/`, `src/services/`), and how it interacts with neighboring services (like PostgreSQL, Redis, or Celery)[cite: 22, 23].

### Step B: The Code Implementation
The clean, production-grade Python or configuration code block, organized matching our enterprise directory structure.

### Step C: The Line-by-Line Deep Dive (The Blueprint)
A sequential breakdown mapping every single line of code (or logical group of lines) to a clear explanation of its exact execution mechanic. This must explain:
- Python keyword logic (e.g., why `flush()` is used instead of `commit()`).
- Database abstractions (SQLAlchemy parameters, constraint tracking).
- API patterns (FastAPI dependency injections, async/await boundaries).

---

## 3. Verification & Safety Safeguards
- **Zero Black Boxes:** No lines of code can be glossed over or summarized as "standard setup logic."
- [cite_start]**Video Alignment:** Explanations must consciously highlight the specific "Request Lifecycle" and "Scale Bottleneck" reasoning [cite: 78, 80][cite_start], directly preparing the user to speak authoritatively to their Tech Lead during evaluation.
- **No Floating Scripts:** Every script snippet must explicitly state its targeted destination filename according to the production folder layout.