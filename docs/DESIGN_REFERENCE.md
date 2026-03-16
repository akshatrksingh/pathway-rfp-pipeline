# Design Reference

Inspired by workwithpathway.com. Warm minimalism, editorial serif headings, macOS-style layout. NOT dark mode. NOT generic Tailwind/shadcn defaults.

## CSS Variables

```css
:root {
  /* Backgrounds */
  --bg-page: #F5F3EE;
  --bg-sidebar: #ECEAE4;
  --bg-card: #FFFFFF;
  --bg-card-hover: #FAFAF8;
  --bg-input: #FFFFFF;
  --bg-tag: #F5F3EE;

  /* Borders */
  --border-default: #D3D1C7;
  --border-light: #E8E6E0;

  /* Text */
  --text-primary: #2C2C2A;
  --text-secondary: #5F5E5A;
  --text-muted: #888780;
  --text-hint: #B4B2A9;

  /* Accent: Green (success, complete, CTA) */
  --green-strong: #0F6E56;
  --green-medium: #1D9E75;
  --green-light: #E1F5EE;
  --green-text: #085041;

  /* Accent: Amber (running, in-progress, estimates, warnings) */
  --amber-strong: #EF9F27;
  --amber-medium: #BA7517;
  --amber-light: #FAEEDA;
  --amber-text: #854F0B;

  /* Accent: Red (errors, failures) */
  --red-strong: #E24B4A;
  --red-light: #FCEBEB;
  --red-text: #791F1F;

  /* Typography */
  --font-serif: 'Georgia', 'Times New Roman', serif;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

  /* Spacing */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-pill: 20px;
}
```

## Typography Rules

- **Step/section headings**: `font-family: var(--font-serif); font-size: 17px; font-weight: 500; color: var(--text-primary);`
- **Body text**: `font-family: var(--font-sans); font-size: 14px; color: var(--text-secondary);`
- **Labels/captions**: `font-family: var(--font-sans); font-size: 12px; color: var(--text-muted);`
- **Sidebar section labels**: `font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted);`
- **Data/numbers**: `font-family: var(--font-sans); font-size: 18px; font-weight: 500; color: var(--text-primary);`
- **Units after numbers**: `font-size: 12px; color: var(--text-muted); font-weight: 400;`
- Two fonts only. Serif for personality (headings), sans for readability (everything else).
- No font-weight above 500. No ALL CAPS except sidebar section labels.

## Component Patterns

### App Shell
```
┌─ Title bar ──────────────────────────────────────┐
│  (centered) "RFP Pipeline — {Restaurant Name}"   │
├─ Sidebar (220px) ─┬─ Main content ───────────────┤
│                    │                              │
│  Restaurants       │   Pipeline stepper           │
│  • Selected ←bg   │   Step cards (stacked)        │
│  • Other           │                              │
│                    │                              │
│  Pipeline runs     │                              │
│  • Current ←bg    │                              │
│  • Previous        │                              │
└────────────────────┴──────────────────────────────┘
```

- Title bar: `background: var(--bg-sidebar); padding: 10px 16px; border-bottom: 0.5px solid var(--border-default);`
- No macOS traffic light dots. Just centered text.
- Sidebar: `width: 220px; background: var(--bg-sidebar); border-right: 0.5px solid var(--border-default);`
- Selected sidebar item: `background: var(--bg-page); border-radius: var(--radius-md);`
- Main content: `padding: 24px 32px; background: var(--bg-page);`

### Pipeline Stepper (horizontal, top of main content)
```
[✓]——[✓]——[●]——[4]——[5]  Step 3 of 5 — Finding distributors
green  green amber gray  gray
```
- Complete: `28px circle, background: var(--green-strong), white checkmark SVG`
- Running: `28px circle, background: var(--amber-strong), white dot center`
- Pending: `28px circle, background: var(--bg-sidebar), border: 1.5px solid var(--border-default), step number in center`
- Connector lines: `height: 2px, 40px wide`. Green if between completed steps, gray otherwise.
- Status text: `font-size: 13px; color: var(--text-muted); margin-left: 12px;`

### Step Card (complete)
```css
background: var(--bg-card);
border: 0.5px solid var(--border-default);
border-radius: var(--radius-lg);
padding: 20px 24px;
margin-bottom: 16px;
```
- Title: serif, 17px, with status pill to the right
- Summary text: `font-size: 12px; color: var(--text-hint);` (e.g., "12 dishes, 47 ingredients")
- Expandable content below title

### Step Card (running/active)
```css
background: var(--bg-card);
border: 1.5px solid var(--amber-strong);  /* thicker amber border */
border-radius: var(--radius-lg);
padding: 20px 24px;
```
- Progress bar: `height: 4px; background: var(--bg-sidebar); border-radius: 2px;` with inner fill `background: var(--amber-strong);`
- Live status text: `font-size: 13px; color: var(--text-secondary);`

### Step Card (pending)
```css
opacity: 0.5;
/* Same as complete card otherwise */
```

### Status Pills
```css
font-size: 11px;
padding: 3px 10px;
border-radius: var(--radius-pill);
```
- Complete: `background: var(--green-light); color: var(--green-strong);`
- Running: `background: var(--amber-light); color: var(--amber-text);`
- Pending: `background: var(--bg-tag); color: var(--text-muted);`
- Failed: `background: var(--red-light); color: var(--red-text);`

### Pricing Cards
**High confidence (API source)**:
```css
background: var(--bg-tag);  /* #F5F3EE */
border-radius: var(--radius-md);
padding: 12px;
```
- Label: 11px, `var(--text-muted)`
- Price: 18px, font-weight 500
- Confidence dot: `6px circle, background: var(--green-strong)` + "high confidence" text

**Low confidence (LLM estimate)**:
```css
background: var(--amber-light);  /* #FAEEDA */
border-radius: var(--radius-md);
padding: 12px;
```
- Label: 11px, `var(--amber-text)`
- Price: 18px, font-weight 500, `color: var(--amber-text)`
- Confidence dot: `6px circle, background: var(--amber-strong)` + "LLM estimate" text

### Tag/Chip (for dish names, ingredient categories)
```css
font-size: 12px;
padding: 4px 12px;
background: var(--bg-tag);
border-radius: var(--radius-sm);
color: var(--text-secondary);
```

### Buttons
**Primary CTA** (Confirm, Send All):
```css
background: var(--green-strong);
color: #FFFFFF;
border: none;
border-radius: var(--radius-pill);
padding: 10px 24px;
font-size: 14px;
font-weight: 500;
cursor: pointer;
```

**Secondary** (Send Selected, Edit):
```css
background: transparent;
color: var(--text-primary);
border: 0.5px solid var(--border-default);
border-radius: var(--radius-pill);
padding: 10px 24px;
font-size: 14px;
```

### Email Draft Card (Step 4 review)
```css
background: var(--bg-card);
border: 0.5px solid var(--border-default);
border-radius: var(--radius-lg);
padding: 20px 24px;
```
- Distributor name: serif, 15px, font-weight 500
- Ingredient list: tags/chips
- Email body: textarea or contentEditable div, `font-family: var(--font-sans); font-size: 13px; border: 0.5px solid var(--border-light); border-radius: var(--radius-md); padding: 12px;`
- Prompt-to-edit input: same styling as email body, with placeholder "Ask AI to adjust..." and a small send icon
- Send/Skip toggle: simple checkbox or toggle switch

### Ingredient Review (Step 1 edit screen)
- Dish as expandable card (serif title, category tag)
- Ingredients as editable rows within the card:
  - Name (text), Quantity (number input), Unit (select), Notes (text input)
  - Delete button (X icon, grayed)
  - Add ingredient button at bottom of each dish card
- Edit states:
  - Unchanged: default styling
  - Edited: `border-left: 3px solid var(--amber-strong); background: var(--amber-light);` (very subtle)
  - Deleted: `opacity: 0.4; text-decoration: line-through;` with undo link
  - Added: `border-left: 3px solid var(--green-strong); background: var(--green-light);`

## Anti-Patterns (DO NOT)
- No purple or blue gradients
- No dark mode
- No shadcn default styling
- No neon/bright status colors
- No heavy drop shadows
- No more than 2-3 colors in any single view
- No generic "AI-powered" copy
- No overly rounded corners (max 12px on cards, 20px on pills only)
- No icon libraries (use simple SVG paths or CSS shapes if needed)
