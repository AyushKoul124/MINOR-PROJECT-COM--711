# Frontend visual upgrade spec (CURSOR_BRIEF §6)

**Goals:** More appealing while keeping **Dark Utilitarian + Bento + Spatial UI**; motion stays subtle (150ms opacity, no bounce).

## Design tokens (align brief)

- Canvas `#090d16`, cards `#0f172a`, borders `#1e293b`
- Primary cyan `#0ea5e9` (replace generic `#3b82f6` accents where primary actions)
- CIB rose `#f43f5e`, support green `#10b981`

## `index.css` additions

1. **Atmospheric canvas** — `.app-container::before` fixed grid + radial cyan/emerald glows (low opacity).
2. **`.badge-cyan`** — missing class used in Overview.
3. **`.nav-agent-pill`** — A/B/C/D/E letter chips on sidebar items.
4. **`.bento-card::after`** — thin top edge gradient on hover (spatial depth).
5. **`.pipeline-rail`** — horizontal A→E status strip styles.
6. Remove/limit `transform: translateY(-1px)` on `.btn-trigger-viva:hover` (brief: low motion); keep glow only.

## `App.jsx`

1. Add `agent: 'A'|'B'|...` per `NAV_ITEMS`; render pill in nav button.
2. Subtitle under logo: **"Audience Intelligence Testbed"** (not operational SOCMINT).
3. Optional **pipeline rail** under top-bar showing Components A–E with monospace labels.
4. Widen sidebar slightly (260px) + active nav left border `2px solid var(--accent-cyan)`.

## `Overview.jsx` copy fixes (ethics)

- Title: **"AI-Driven Audience Intelligence Framework"**
- Subtitle: public Telegram academic prototype; **NTRO = problem statement inspiration only**
- Keep RUN ANALYSIS NOW button prominent with cyan gradient using `#0ea5e9`

## `index.html`

- Meta description for viva reviewers.

## Views (light pass)

- **QueryPanel:** citation drawer styling with `backdrop-blur-md`
- **NetworkGraph:** legend line "Anomaly signal — not confirmed coordination"
- **Demographics:** tooltip on greyed cards for k-anonymity

Agent mode should implement these files directly without pasting from this doc.
