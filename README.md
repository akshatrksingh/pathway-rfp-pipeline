# Pantry

Automated RFP pipeline for restaurant ingredient procurement.

---

## Demo

See the [Loom walkthrough](https://www.loom.com/share/3380706f4e66415daadb61a2d2ff6a6c).

Menu source: [Bombay Bites (dummy restaurant name, real menu)](https://www.loom.com/share/3380706f4e66415daadb61a2d2ff6a6c)

---

## Architecture

The pipeline runs five steps with two human checkpoints:

```
Upload menu
    │
    ▼
[Parse] pdfplumber → text or vision (for scanned PDFs) → LLM → structured dishes + ingredients
    │
    ▼
[Human checkpoint 1] Review & edit ingredient list before anything is priced or sent
    │
    ▼
[Price] USDA FDC enrichment (category context) → batch LLM wholesale price estimate
    │
    ▼
[Distributors] Tavily web search → LLM extracts real businesses + maps to supply categories
    │
    ▼
[Emails] LLM drafts per-distributor RFP (only their ingredients) → user edits / skips
    │
    ▼
[Human checkpoint 2] Review, edit, or skip each email before anything is sent
    │
    ▼
[Send] AgentMail delivers emails from a dedicated agent inbox
```

The system automates data gathering — parsing, pricing, distributor search, email drafting. It pauses for human judgment at two points: ingredient review (the chef knows their recipes better than the AI) and email review (nothing goes out without approval).

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | [FastAPI](https://fastapi.tiangolo.com) + [SQLAlchemy](https://www.sqlalchemy.org) + SQLite |
| Frontend | [React](https://react.dev) + [Vite](https://vitejs.dev) |
| LLM | Swappable via env var — [Claude](https://www.anthropic.com) / [Groq](https://groq.com) / [OpenAI](https://openai.com) |
| Ingredient data | [USDA FoodData Central API](https://fdc.nal.usda.gov/) — FDC ID + food category |
| Distributor search | [Tavily Search API](https://tavily.com) — real-time web search for local distributors |
| Email | [AgentMail](https://agentmail.to) — API-first email infrastructure for AI agents; gives the agent its own inbox that can send, receive, and reply |
| PDF extraction | [pdfplumber](https://github.com/jsvine/pdfplumber) |

---

## Quick start

```bash
git clone <repo-url>
cd pathway-rfp-pipeline

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install agentmail      

cp ../.env.example ../.env
# Fill in API keys in .env (see section below)

uvicorn main:app --reload
# API runs at http://localhost:8000

# Frontend (separate terminal)
cd ../frontend
npm install
npm run dev
# UI runs at http://localhost:5173
```

---

## API keys needed

| Key | Where to get it |
|---|---|
| `LLM_API_KEY` | [Anthropic console](https://console.anthropic.com) (best quality) or [Groq](https://console.groq.com) (free tier) |
| `USDA_API_KEY` | [fdc.nal.usda.gov/api-key-signup](https://fdc.nal.usda.gov/api-key-signup) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) — 1,000 free credits/month |
| `AGENTMAIL_API_KEY` | [agentmail.to](https://agentmail.to) — free tier, 3 inboxes |

Set `LLM_PROVIDER` to `anthropic`, `groq`, or `openai` to select the provider. The default is `groq` with `meta-llama/llama-4-scout-17b-16e-instruct`.

Without an `AGENTMAIL_API_KEY`, emails are printed to the console instead of sent — useful for demos.

---

## Project structure

```
backend/
  main.py                    # FastAPI app, CORS
  config.py                  # Pydantic Settings, reads from .env
  models.py                  # SQLAlchemy ORM (13 tables)
  schemas.py                 # Pydantic request/response models
  database.py                # Engine (NullPool for SQLite), session, Base
  requirements.txt
  services/
    llm_client.py            # Provider abstraction (Groq/OpenAI/Anthropic) + retry
    menu_parser.py           # PDF text + vision fallback, image parse
    usda_client.py           # FoodData Central API — FDC ID + category lookup
    pricing.py               # Cache check → USDA enrich → batch LLM estimate
    distributor_finder.py    # 1 Tavily search + 2 LLM calls → real distributors
    email_composer.py        # Per-distributor RFP draft + prompt-to-edit rewrite
    email_sender.py          # AgentMail send with console fallback
  routers/
    menus.py                 # Menu upload + parse endpoint
    pipeline.py              # /start, /pricing, /distributors
    emails.py                # /draft, /send, /{id}/edit

frontend/
  src/
    App.jsx                  # Top-level state, view routing
    main.jsx
    components/
      TitleBar.jsx           # App header with restaurant selector
      WorkflowSidebar.jsx    # 8-step progress sidebar
      Sidebar.jsx            # Restaurant list panel
      MenuUpload.jsx         # File drop zone + restaurant form
      DishServings.jsx       # Per-dish servings/day input
      IngredientReview.jsx   # Editable ingredient table with soft state
      ConfirmModal.jsx       # Reusable Apple-style confirmation modal
      PipelineProgress.jsx   # Pricing → distributors → email draft steps
      EmailReview.jsx        # Per-distributor email preview + edit + send

docs/
  SYSTEM_DESIGN.md           # Architecture and design decision writeup
```

---

## Key features

- **PDF and image menu parsing** — pdfplumber extracts text from text-based PDFs; scanned / image-based PDFs fall back to concurrent LLM vision parse across pages; direct image uploads (PNG, JPG, WEBP) use vision parse directly
- **Dish-level volume control** — user sets servings/day per dish; the system multiplies by 30 to get monthly bulk quantities for the RFP
- **Editable ingredient table** — each ingredient tracks its own state (unchanged / edited / added / deleted) before any data is persisted; changes are highlighted visually and can be undone
- **USDA FoodData Central integration** — every ingredient is looked up against the USDA FDC to get a canonical FDC ID and food category, which improves LLM pricing accuracy
- **Batch LLM pricing** — all uncached ingredients are priced in a single LLM call with calibrated wholesale anchors; prices include `source` ("llm_estimate") and `confidence` ("low") so the restaurant knows what to verify during negotiations
- **Real distributor discovery** — Tavily performs a live web search for wholesale food distributors near the restaurant; an LLM extracts structured records and maps each distributor to supply categories; the system never fabricates distributor names
- **Targeted RFP emails** — each distributor only receives the ingredients they cover, not a generic blast; quantities are the monthly bulk totals calculated from the servings data
- **LLM-assisted email editing** — users can type natural language instructions (e.g. "make it more formal", "add a line about cold-chain requirements") and the AI rewrites the draft in place
- **Send/skip per distributor** — each email can be sent, edited, or skipped individually; nothing is sent without explicit confirmation
- **AgentMail delivery** — emails are sent from a dedicated agent inbox (`rfp-pathway@agentmail.to`), which supports receive and reply — the foundation for autonomous quote monitoring in future

---

## Design decisions

- **Tavily over LLM-generated distributors** — the system finds real businesses via web search. Results can be verified by the user; no fake companies are ever stored or emailed.
- **AgentMail over basic SMTP** — not just a sender. AgentMail gives the agent its own inbox. In production this enables autonomous quote monitoring: the agent watches for replies, parses quotes, and follows up on non-responses. It's agent-native infrastructure, not a one-shot mailer.
- **Batch LLM pricing** — all ingredients priced in a single API call. Avoids rate-limit exhaustion on large menus (a menu with 60+ ingredients would hit Groq limits with per-ingredient calls).
- **Two human checkpoints** — AI handles data gathering (parsing, pricing, searching, drafting); humans handle judgment calls (are these the right ingredients? should this email go out?). The pipeline pauses and waits at both points.
- **Swappable LLM provider** — change `LLM_PROVIDER` in `.env` to switch between Groq (free), Claude (highest quality), or OpenAI. The abstraction handles the different SDK formats transparently.
- **Price confidence scoring** — every price row stores its source and confidence level. "LLM estimate / low" signals that the restaurant should treat these as starting points for negotiation, not market data.
- **No auth by design** — the restaurant selector provides data scoping. Auth would add boilerplate without demonstrating system design.
- **SQLite with SQLAlchemy ORM** — zero-friction setup for evaluators (clone, pip install, run). Switching to Postgres is one `DATABASE_URL` change; the ORM handles the rest.

---

## Future extensions

- **Autonomous quote collection** — AgentMail webhook receives distributor replies; LLM parses quote data; agent auto-follows up on incomplete or missing responses; comparison table surfaces lowest per-ingredient bids
- **Scheduled price refresh** — configurable TTL per source; daily/weekly re-queries for volatile produce, weekly for stable dry goods
- **Commodity price alerts** — monitor USDA AMS MyMarketNews or commodity feeds for supply disruptions (avian flu, frost, port delays) and trigger proactive re-pricing
- **USDA AMS MyMarketNews integration** — real wholesale commodity prices as a high-confidence pricing source, replacing LLM estimates for covered categories
- **Quote feedback loop** — actual distributor quotes feed back as ground truth, improving future LLM price estimates for that ingredient and region
- **Ingredient deduplication** — embedding similarity to merge near-duplicates ("tomato" / "tomatoes", "naan" / "naan bread") before pricing and distributor matching
- **Multi-location support** — per-location distributor networks and pricing, with rollup views for restaurant groups
