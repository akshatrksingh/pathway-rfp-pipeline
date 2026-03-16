# System Design: Restaurant RFP Automation Pipeline

## Overview

This system automates the end-to-end Request for Proposal (RFP) process for restaurants seeking ingredient quotes from local distributors. Given a restaurant menu, it parses dishes into structured recipes, fetches market pricing context, identifies relevant distributors, and sends targeted RFP emails requesting quotes.

The pipeline is designed around two principles:
1. **API-first, LLM-fallback**: Real data sources are queried first; LLM fills gaps where APIs fall short.
2. **Human-in-the-loop at decision points**: The system automates data gathering but pauses for human review before persisting ingredient data and before sending emails.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                       │
│                                                                      │
│  Restaurant Select → Menu Upload → Ingredient Review → Pipeline      │
│  Progress → Email Review → Results Dashboard                         │
│                                                                      │
│  SSE stream ←──────── FastAPI Backend ────────→ SQLite DB            │
└───────────────┬──────────────────────────────────┬───────────────────┘
                │                                  │
    ┌───────────┴───────────┐          ┌──────────┴──────────┐
    │    External APIs      │          │    LLM Provider     │
    │                       │          │    (Swappable)      │
    │  • USDA FoodData      │          │                     │
    │  • Pricing API        │          │  • Groq (default)   │
    │  • Tavily Search      │          │  • Claude           │
    │  • AgentMail          │          │  • OpenAI           │
    └───────────────────────┘          └─────────────────────┘
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | FastAPI + SQLAlchemy | Async-capable, clean routing, ORM for DB abstraction |
| Database | SQLite | Zero-friction setup. SQLAlchemy ORM allows Postgres swap via one env var. |
| LLM (runtime) | Groq free tier (Llama 4 Scout) | Free, fast inference for demo. Provider-swappable. |
| Ingredient data | USDA FoodData Central API | Standardized food identification, free, government source |
| Pricing | USDA FDC (identity) + LLM estimates (prices) | API-first canonicalization, LLM fills pricing gaps |
| Distributor search | Tavily API | AI-optimized search, structured results, 1000 free credits/month |
| Email | AgentMail | API-first email for agents. Handles send + receive. Free tier. |
| Frontend | React (Vite) | Fast dev, component model, SSE support |

---

## Pipeline Flow

The pipeline has 5 steps with 2 human checkpoints:

```
STEP 1 ──────── CHECKPOINT 1 ──────── STEPS 2-3 ──────── CHECKPOINT 2 ──────── STEP 4 ──── STEP 5
Menu Parse      Review/Edit           Automated           Review/Edit           Send        Collect
                Ingredients           (Pricing +          Emails                Emails      Quotes
                                      Distributors)
```

### Step 1: Menu → Recipes & Ingredients

**Input**: Restaurant name, street address, menu (PDF upload or URL).

**Process**:
1. PDF: extract text via pdfplumber. URL: fetch page HTML, extract text.
2. LLM parses text into structured dishes with ingredients and estimated monthly bulk purchasing quantities (assumes mid-size restaurant, ~150 covers/day).
3. Output presented to user for review.

**Human Checkpoint 1**: User reviews parsed dishes and ingredients. Can edit quantities, add/remove ingredients, adjust units. UI tracks edit state visually (highlighted edits, strikethrough deletes, badged additions). Nothing persists to DB until explicit confirmation.

### Step 2: Ingredient Pricing Trends

**Challenge**: USDA FoodData Central provides nutritional data, not pricing. The US has no standardized pricing (no MRP equivalent). Prices vary by retailer, region, and distributor.

**Solution (3-layer architecture)**:

| Layer | Source | Confidence | TTL |
|-------|--------|-----------|-----|
| 1. API data | USDA FDC (identity) + Pricing API (prices) | High | 7 days |
| 2. LLM estimate | Generated wholesale price range | Low | 1 day |
| 3. Future (documented) | Scheduled updates, event triggers, quote feedback | N/A | N/A |

USDA FDC provides ingredient canonicalization (FDC ID, standardized name, food category). The standardized name improves downstream pricing API queries. Price data stored with source attribution and confidence scoring.

**Caching**: First run hits APIs per ingredient. Subsequent runs check DB cache (by TTL). Second pipeline run is all cache hits.

### Step 3: Find Local Distributors

**Process**:
1. Aggregate confirmed ingredients, LLM assigns categories (produce, dairy, dry goods, etc.)
2. Tavily search per category + restaurant location (e.g., "wholesale dairy supplier Brooklyn NYC")
3. LLM extracts structured distributor data from search results
4. Fallback: LLM generates plausible distributors if Tavily returns nothing for a category

**No human checkpoint**: Results shown in UI for transparency but don't block the pipeline. Human approval happens at the email review stage.

### Step 4: Send RFP Emails

**Process**:
1. LLM composes targeted email per distributor (only their relevant ingredients, with quantities and quote deadline)
2. Emails stored as drafts

**Human Checkpoint 2**: User reviews all draft emails before sending. Can:
- Directly edit email text
- Use prompt-to-edit: type natural language instruction ("make it more formal", "add urgency") and LLM rewrites the email
- Toggle send/skip per distributor
- Send all or send selected

Emails sent via AgentMail. Mock recipients use Gmail `+` aliases for demo.

### Step 5: Collect & Compare Quotes (Bonus)

Schema and comparison UI built. Agent workflow documented but not fully implemented:
- AgentMail webhook receives distributor replies
- LLM parses quoted prices per ingredient
- Auto-follow-up if quote is incomplete
- Comparison table: ingredients as rows, distributors as columns, best prices highlighted

---

## Database Schema

### Entity Relationship Diagram

<!-- ERD diagram would be embedded here as an image -->
<!-- See the mermaid ERD in the project root or rendered in the README -->

### Design Decisions

1. **Ingredients are global, everything else is scoped.** "Mozzarella" is one row regardless of which restaurant uses it. USDA data, pricing, and distributor mappings attach to the canonical ingredient once. Per-restaurant context (quantities, units, notes) lives in the `dish_ingredients` join table.

2. **No separate recipes table.** A dish IS its recipe. The recipe is the set of `dish_ingredients` rows linked to that dish. Adding a separate table adds complexity without value at this scale.

3. **`price_data` is append-only with TTL.** Multiple rows per ingredient over time enables trend visualization. `fetched_at` and `expires_at` drive the caching strategy. `source` and `confidence` fields enable the API-first, LLM-fallback pattern.

4. **`run_distributors` vs `distributor_ingredients` serve different purposes.** `distributor_ingredients` maps general supply capability. `run_distributors` tracks which distributors were found for a specific pipeline run. Different menu, different ingredients, potentially different distributors.

5. **`pipeline_runs` tracks execution state.** The `status` field drives the progress UI via SSE. Links restaurant + menu to all downstream data.

6. **`quotes` is normalized per-ingredient-per-distributor.** Enables comparison queries: "show me what every distributor quoted for mozzarella."

7. **`edit_status` on `dish_ingredients`** supports the soft edit UI pattern. Frontend tracks state (unchanged/edited/deleted/added) visually before persisting.

### Table Definitions

```sql
-- Core entities
CREATE TABLE restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    name TEXT,
    raw_text TEXT NOT NULL,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id INTEGER NOT NULL REFERENCES menus(id),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT
);

CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    usda_fdc_id INTEGER,
    usda_category TEXT,
    default_unit TEXT
);

CREATE TABLE dish_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id INTEGER NOT NULL REFERENCES dishes(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quantity REAL,
    unit TEXT,
    notes TEXT,
    edit_status TEXT DEFAULT 'unchanged'
);

-- Pricing (global, timestamped, cached)
CREATE TABLE price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    price_low REAL,
    price_avg REAL,
    price_high REAL,
    unit TEXT,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Pipeline execution
CREATE TABLE pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    menu_id INTEGER NOT NULL REFERENCES menus(id),
    status TEXT DEFAULT 'started',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Distributors
CREATE TABLE distributors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    website TEXT,
    specialty TEXT,
    area TEXT
);

CREATE TABLE run_distributors (
    pipeline_run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),
    distributor_id INTEGER NOT NULL REFERENCES distributors(id),
    PRIMARY KEY (pipeline_run_id, distributor_id)
);

CREATE TABLE distributor_ingredients (
    distributor_id INTEGER NOT NULL REFERENCES distributors(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    PRIMARY KEY (distributor_id, ingredient_id)
);

-- RFP Emails
CREATE TABLE rfp_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),
    distributor_id INTEGER NOT NULL REFERENCES distributors(id),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    sent_at TIMESTAMP
);

CREATE TABLE rfp_email_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_email_id INTEGER NOT NULL REFERENCES rfp_emails(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quantity_needed REAL,
    unit TEXT
);

-- Quotes (Step 5 bonus)
CREATE TABLE quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_email_id INTEGER NOT NULL REFERENCES rfp_emails(id),
    distributor_id INTEGER NOT NULL REFERENCES distributors(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quoted_price REAL,
    unit TEXT,
    delivery_terms TEXT,
    valid_until DATE,
    received_at TIMESTAMP,
    raw_email_text TEXT
);
```

---

## LLM Provider Abstraction

The system supports multiple LLM providers through a thin abstraction layer. All runtime LLM calls go through `services/llm_client.py`.

**Provider swap**: Change one environment variable (`LLM_PROVIDER`) to switch between Groq, OpenAI, Claude, or any OpenAI-compatible provider. No code changes required.

**Why this matters**: At a startup, you're constantly evaluating new models. A new Llama release? Change the model string. Want to test Claude for better structured output? Flip the provider. The abstraction costs 20 lines of code and saves hours of refactoring later.

```
Groq / OpenAI / Together / Fireworks → OpenAI SDK (same interface, different base_url)
Anthropic → Anthropic SDK (different message format, handled in abstraction)
```

---

## Frontend Design

### Design Language

Inspired by Pathway's own website (workwithpathway.com). Warm minimalism with an editorial touch.

| Element | Value |
|---------|-------|
| Background | Warm cream `#F5F3EE` |
| Primary text | Dark charcoal `#2C2C2A` |
| Secondary text | Muted gray `#888780` |
| Success/complete | Mint green `#0F6E56` (strong), `#E1F5EE` (fill) |
| Running/estimate | Amber `#EF9F27` (strong), `#FAEEDA` (fill) |
| Error | Muted coral |
| Cards | White `#FFFFFF`, 0.5px border `#D3D1C7`, 12px radius |
| Sidebar | Warm gray `#ECEAE4` |
| Headings | Serif (Georgia) |
| Body/UI | Sans-serif (Inter / system) |

### Layout

macOS-inspired: sidebar with restaurant/run history, main content area with pipeline steps as stacked cards. Pipeline progress shown via horizontal stepper and per-step card states (complete/running/pending).

### Key UX Patterns

**Progressive reveal**: Automated pipeline steps show as collapsed cards. As each completes, it expands to show output. Active step shows progress bar and live status text via SSE.

**Soft edits**: Ingredient review tracks changes visually (highlighted, strikethrough, badged) before persisting. Undo-able. Nothing hits DB until explicit confirm.

**Prompt-to-edit emails**: In addition to direct text editing, users can type natural language instructions to have the LLM revise draft emails. Combines manual control with AI assistance.

**Confidence indicators**: Green dot for API-sourced prices, amber dot for LLM estimates. Amber-tinted card background for estimated data. User immediately sees what to trust vs verify.

**Non-blocking errors**: Pipeline continues past failures. Issues surfaced as warnings with fallback actions. Green/amber/red for success/degraded/failed. Every error has a recovery path.

---

## Error Handling Philosophy

The system is designed for graceful degradation, not hard failures:

| Scenario | Behavior |
|----------|----------|
| USDA returns no match for ingredient | Ingredient proceeds without FDC ID. Pricing falls back to LLM estimate. |
| Pricing API has no data | LLM generates estimated range with low confidence indicator. |
| Tavily finds no distributor for a category | Orphaned ingredients bundled into general distributor's email. |
| Email fails to send | Shown as failed with retry/edit/skip actions inline. |
| LLM returns malformed JSON | Retry with stricter prompt. If persistent, surface error to user. |

---

## Future Architecture (Not Built, Documented)

### Scheduled Price Updates
Cron job re-queries pricing APIs on configurable cadence (daily/weekly). Tracks price deltas over time for trend charts. LLM estimates get shorter TTL so they refresh sooner, gradually replaced by real API data.

### Event-Driven Triggers
Monitor commodity feeds for supply disruptions (avian flu affecting egg prices, frost in Florida affecting citrus, shipping disruptions on imported ingredients). Could be an LLM agent watching RSS feeds or commodity index APIs, triggering re-pricing and proactive distributor outreach.

### Distributor Quote Feedback Loop
Actual quotes from Step 5 feed back into the pricing database as ground truth. Over time, the system learns real market rates for the restaurant's area, improving estimate accuracy and reducing LLM fallback dependence.

### Confidence Promotion
As real data accumulates, `llm_estimate` rows get replaced by API or quote-based data. Confidence upgrades from low to high automatically.
