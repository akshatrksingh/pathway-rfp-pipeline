# RFP Automation Pipeline

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: React (Vite)
- LLM: Groq (llama-4-scout-17b) default, swappable via config
- APIs: USDA FoodData Central, Tavily (distributor search), AgentMail (email)
- Config: Pydantic BaseSettings + .env

## Project Structure
```
backend/
  main.py              # FastAPI app, CORS, SSE streaming
  config.py            # Pydantic Settings from .env
  models.py            # SQLAlchemy ORM models
  schemas.py           # Pydantic request/response schemas
  database.py          # Engine, session, Base
  services/
    llm_client.py      # Provider abstraction (Groq/OpenAI/Anthropic)
    menu_parser.py     # PDF/URL text extraction + LLM structured parsing
    usda_client.py     # FoodData Central API integration
    pricing.py         # API-first pricing with LLM fallback, caching
    distributor_finder.py  # Tavily search + LLM extraction
    email_composer.py  # LLM email drafting + prompt-to-edit
    email_sender.py    # AgentMail send/receive
  routers/
    restaurants.py
    menus.py
    pipeline.py        # SSE endpoint for live progress
    emails.py
    quotes.py
frontend/
  src/
    App.jsx
    components/
    hooks/
    styles/
docs/
  SYSTEM_DESIGN.md     # Human-readable design doc for evaluators
  ARCHITECTURE.md      # This file's extended version
```

## Database (SQLite)
13 tables. Key relationships:
- restaurants → menus → dishes → dish_ingredients → ingredients (global)
- ingredients → price_data (timestamped, cached with TTL)
- pipeline_runs → run_distributors, rfp_emails → rfp_email_ingredients, quotes
- distributors (global) → distributor_ingredients, run_distributors

## LLM Abstraction
All LLM calls go through `services/llm_client.py`:
- `get_completion(messages)` — text in, text out
- `get_vision_completion(image_bytes, prompt)` — for image menus (Claude/OpenAI only, Groq falls back to OCR)
- Provider determined by LLM_PROVIDER env var
- Groq/OpenAI use OpenAI SDK (same interface, different base_url)
- Anthropic uses Anthropic SDK (different message format)

## Pipeline Steps
1. Menu Parse: PDF→pdfplumber→text or URL→fetch→text, then LLM→structured JSON
2. Pricing: USDA FDC search→FDC ID + category. LLM generates wholesale price estimates using USDA category as context. Cache with TTL. Architecture supports plugging in a real pricing API later.
3. Distributors: Tavily search per ingredient category + restaurant location, LLM extracts structured data
4. Emails: LLM drafts per-distributor RFP emails, user reviews/edits, AgentMail sends
5. Quotes (bonus): AgentMail webhook receives replies, LLM parses, comparison table

## Key Patterns
- API-first, LLM-fallback: pricing and distributors both try real APIs first, LLM fills gaps
- Two human checkpoints: after ingredient parsing (review/edit), before email sending (review/edit/prompt-to-edit)
- SSE streaming for pipeline progress updates to frontend
- Soft edit state in UI: track unchanged/edited/deleted/added before persisting
- Price data cached with different TTLs: 7 days for API, 1 day for LLM estimates

## Conventions
- Type hints on all functions
- Pydantic models for all API request/response schemas
- Each pipeline step is a standalone service with clear input/output
- Return structured JSON from LLM calls (use system prompt to enforce format)
- Store source + confidence on all generated/fetched data

## Frontend Design
- Cream background (#F5F3EE), dark charcoal text (#2C2C2A)
- Mint green for success/complete (#0F6E56 strong, #E1F5EE light)
- Amber for running/estimates (#EF9F27 strong, #FAEEDA light)
- Serif font (Georgia) for step headings, sans (Inter/system) for UI
- macOS-style sidebar layout, no traffic light dots
- White cards with 0.5px border, 12px radius
- Status pills: muted, pill-shaped, small text

## Do NOT
- Overengineer. Take-home, not production infra.
- Add auth/login. Restaurant selector provides scoping.
- Use async unless needed for SSE streaming.
- Add unnecessary middleware.
- Use dark mode. Light/warm only.
- Use shadcn defaults or purple/blue gradients.
- Add vector DB, Redis, or Docker (except optional Postgres compose).
- **NEVER run git commands.** No git add, git commit, git push, git checkout, or any git operation. User handles all git operations manually. This is a hard rule with no exceptions.
