# VerifAI UI design spec (Graphite)

Handoff for the React build. Design is finished and chosen; no UI code was written in the design session. Build from this file, `tokens.css`, and the static references in `reference/` (open them in a browser). All data in the references is made-up example content.

## Where things are

| File | What it is |
|---|---|
| `tokens.css` | Tailwind v4 `@theme` block. Paste into `frontend/src/index.css` |
| `graphite-reference.css` | Exact CSS from the latest live mockups (includes the review edits). Source of truth for sizes, spacing, states. Port to utilities; do not ship as is |
| `graphite-reference-mobile-overrides.css` | The few rules that differ in the mobile mockup (accordion header, source block, chevron) |
| `icons.svg` | Sprite with the 10 icons (`ic1` to `ic10`) |
| `reference/*.html` | One page per chosen screen (landing, loading, errors, results, disputed, mobile, components). Rebuilt from the live artifacts, so they include every comment edit made after the first publish |
| `sample-response*.json` | Frozen `VerifyResponse` shape: normal, partial failure, no claims. Use alongside `frontend/src/fixtures/` |

Existing scaffold in `frontend/`: Vite 8, React 19 (JSX, no TypeScript), Tailwind v4 via `@tailwindcss/vite`, `src/api.js` with `ApiError` and fixture mode (`VITE_USE_FIXTURES=true`). Keep that. No UI library. Build the UI from fixtures first.

## Chosen directions

| Screen | Choice |
|---|---|
| Landing and input | Graphite: brand top left, big light line, form at the bottom (phase 1, card 08) |
| Loading | B, One at a time |
| Errors | D, Toast (all four cases) |
| Results | D, Summary first |
| Disputed claim | D, Filter tabs |
| Mobile 390 px | Input E (bottom sheet form), Results D (accordion) |
| Components | Set B, Solid chip |

Assumption to confirm: Solid chip is applied to every screen, not just the component sheet. The reference pages already do this (`.set-2` on the wrapper). If you want tinted pills on screens instead, drop the `.set-2` rules.

## Look in one paragraph

Near-black, hairline borders, DM Sans with light 300 display lines, DM Mono for labels and data, mostly empty space, 200 ms ease on everything. Colour is only used for verdicts and the error state. Verdict colour is never the only signal: every verdict, stance and tier has an icon, a word or both.

## Tokens (see `tokens.css`)

- Surfaces: `page #070708` (presentation only), `bg #0C0C0D` (app background), `surface #141416` (cards, inputs), `surface-2 #1B1B1E` (toasts, sheets).
- Lines: `line #2A2A2E`, `line-strong #44444A` (hover, secondary borders).
- Text: `fg #EDEDED`, `fg-2 #BDBDC2` (body copy), `mu #8D8D93` (labels, hints).
- Verdict: supported `#5AB0F0`, contradicted `#F0794A`, disputed `#EBC24D`, insufficient `#8D8D93`; icon colour on a filled verdict is `#0C0C0D`.
- Type scale: lead 34/1.08 weight 300, tracking -0.03em (26 px small); claim text 18/1.35 weight 500; body 15; explanation 14/1.6; small 13; mono labels 11 to 12 px uppercase, tracking 0.08em. Use `font-variant-numeric: tabular-nums` for timers and counts.
- Radius: 6 px for buttons, inputs, verdict chips, toasts (Solid chip); 3 px tier badge; 16 px cards; 999 px only for pills that remain (loading pills, segmented control).
- Focus: 2 px white outline with 2 px offset on every interactive element; inputs also get the `shadow-focus` ring and a white border.
- Motion: `prefers-reduced-motion` turns off all animation and transitions.

## Shared components

All map directly to the API fields. Icons: check (`ic1`), cross (`ic2`), split arrows (`ic3`), question (`ic4`), minus (`ic5`), alert circle (`ic6`), search (`ic7`), external (`ic8`), chevron (`ic9`), link (`ic10`).

**VerdictBadge** (`verdict`): supported = check, "Supported"; contradicted = cross, "Contradicted"; disputed = split arrows, "Disputed"; insufficient_evidence = question, "Not enough evidence". Solid chip: filled with the verdict colour, dark text and icon, 6 px radius.

**ConfidenceMeter** (`confidence`): three rising bars (6, 10, 14 px tall), 1 to 3 filled in `fg`, rest `line-strong`, then the word "High confidence" / "Medium confidence" / "Low confidence". Never a percentage.

**TierBadge** (`tier`): "Tier N" in mono 11 px plus three pips; Tier 1 fills 3 pips, Tier 2 fills 2, Tier 3 fills 1. Tier 1 has a brighter border and text. `title` tooltip: 1 Government, 2 Education, fact-checker or Wikipedia, 3 Everything else.

**StanceChip** (`stance`): support = check in a small verdict-blue square, "Supports"; contradict = cross in orange, "Contradicts"; not_addressed = minus in grey, "Not addressed".

**SourceRow** (`sources[i]`, number is index + 1): 24 px outlined number circle, title (link, 500 weight, opens new tab with `rel="noopener noreferrer"`), domain in mono, then tier badge and stance chip, then the evidence sentence with a 2 px left rule in the stance colour. The number is required because explanations say "Source 1", "Source 2". Render "Source N" inside explanations as a small mono `ref` chip.

**Button**: primary is `fg` fill with dark text; ghost has a `line-strong` border. 12 px by 22 px padding (small 8 by 16). Disabled at 40% opacity.

**Input**: `surface` fill, 1 px `line` border, 6 px radius, 15 by 16 px padding; hover `line-strong`; focus white border plus ring; error border `contradicted` with an inline message (alert icon, `error-text` colour).

**Toast**: `surface-2`, `line-strong` border, 6 px radius, `shadow-toast`, icon, bold title, one line of body, dismiss cross. Anchored to the bottom of the viewport on mobile, bottom of the content area on desktop. `role="alert"`. Stays until dismissed or the next submit (proposal).

**EmptyState**: dashed `line-strong` border, search icon in a 44 px circle, "Nothing checked yet", one line of help, small primary button.

## Screens

### 1. Landing and input (`reference/landing.html`, `reference/mobile.html` input)
- Layout: brand (dot plus "VerifAI") top left, lead line "Is it true? Check the sources." at 34 px light, then space, then the form pinned toward the bottom.
- Form: text tabs "Link" and "Paste text" (active = white text with a 1 px underline). Link mode: one `url` input, label "Video or article link", placeholder `https://youtube.com/watch?v=...`. Paste mode: textarea, label "Text to check", counter.
- Hint line under the field (mu colour): "Paste a YouTube or article link." The same slot becomes the inline error message. Reserve its height so the layout does not jump.
- Validation before sending: link must parse as http or https. Pasted text must be at least 100 characters to match the backend `MIN_TEXT_CHARS = 100` (the mockup copy says 200; use 100). Show the Bad URL toast and the inline error together.
- Mobile (E): the whole form lives in a rounded `surface` card in the lower thumb zone with a full-width primary button, 15 px vertical padding. Changed in review: no brand in the top left corner; "VerifAI" is centered in the empty space above the form at 34 px, weight 400, tracking -0.01em, 12 px gap.
- The desktop landing keeps the brand top left (only the mobile input changed).
- Submit: button text "Check claims". On submit switch to the loading screen.

### 2. Loading (`reference/loading.html`)
- One stage at a time, large and light: stage name at 34 px, one grey sentence under it, step counter "2 / 4", four hairline dots (28 px by 2 px, filled when done or active), footer with elapsed time `00:10` and "Usually 20 to 50 s".
- Stages and sentences: Reading the page / Pulling the transcript from the video; Finding claims / Choosing 3 to 6 checkable claims; Searching the web / Looking for sources on each claim; Weighing sources / Labelling what each source says. For pasted text change the first sentence to "Reading your text".
- Important: the backend does not stream progress (live progress streaming is cut from v1). Advance the stage on a client timer: start at 0 s, then 6 s, 16 s, 34 s, and hold on "Weighing sources" until the response arrives. It is an estimate; do not claim it is live. Keep the copy "Usually 20 to 50 s", not a percentage.
- Under `prefers-reduced-motion`, show the current stage statically and update the text only.
- Optional proposal: after 60 s add a line "This is taking longer than usual."

### 3. Errors, toast variant (`reference/errors.html`)
Four cases, all with the toast in the lower area and the page content staying put.

| Case | Trigger | Toast title | Toast body | Page behaviour |
|---|---|---|---|---|
| Bad URL | client validation, or HTTP 4xx `{detail}` about input | That does not look like a link | Start with https:// and paste the full address of a YouTube video or an article. | Input keeps its value, red border, inline message |
| Extraction failed | HTTP 422 from extraction, or `errors[]` stage `extract` | We could not read that page | The page may block automated readers or need a login. | Keep the link field and add the Paste text fallback (switch tab to Paste text and focus it) |
| Partial failure | 200 response with `errors[]` containing `claim_id` (stage `search` or `evaluate`) | N of M claims were checked | The other two hit a problem. | Show results for finished claims, a failed row per `claim_id`, and a retry field "Try another link" plus "Check claims" |
| No claims found | 200 response with `claims: []`, usually `errors[]` stage `claims` | No checkable claims in this text | Opinions, jokes and plain descriptions do not count. | Retry field "Try another link" plus "Check claims" under the source chip |

Notes:
- Use the backend `detail` string as the toast body when it is user-safe (`ApiError.message` is already safe to show). The copy above is the fallback.
- A failed claim is only identified by `claim_id` in `errors[]`; the failed claim's text is not in the response (the mockup shows text, which the API cannot supply). Show "Claim 2 could not be checked" with the stage code (`search` or `evaluate`) and the message. If you want the text, the backend needs a change, which the frozen shape forbids without a decision.
- Orange marks the error and an alert icon repeats it. Network failure (`status` 0): title "We could not reach VerifAI", body "Check your connection and try again."

### 4. Results, summary first (`reference/results.html`, mobile D)
- Top: source chip (link icon, URL or "Pasted text", plus title when known) and "N claims".
- Summary: a distribution bar (8 px tall, one segment per verdict with count > 0, flex weight = count, 3 px gaps) and a row of verdict chips with counts, e.g. "1 Supported".
- Claims as an accordion, one `details` per claim. The first claim starts open.
- Accordion header (always visible, open or collapsed; changed in review so the verdict never hides): grid with the claim text on top at 18/1.35 weight 500 (same as the claim text on a card), the chevron to its right, then a second row with the verdict chip on the left and the confidence meter on the right. Header padding 16 px by 20 px. The confidence meter has `min-width: 140px` and is left-aligned inside it, so High, Medium and Low line up. Chevron is white (`#fff`), 16 px, stroke 2.4 (not grey), rotates 180 degrees when open.
- Open content (padding 0 20 20): explanation with `ref` chips, then the dense source list. It no longer repeats the verdict and confidence row.
- Order: keep response order. Do not sort by verdict.
- Failed claims (from `errors[]` with `claim_id`) appear as muted failure rows after the claims, never silently dropped.

### 5. Disputed claim, filter tabs (`reference/disputed.html`)
- Applies when `verdict === "disputed"`. Inside the open accordion item show a segmented control: "All n", "Supporting n", "Contradicting n" (counts from `stance`). Default is All.
- One source list below it, filtered by stance. Sources keep their original numbers (1..N) so explanations stay correct. `not_addressed` sources show only under All.
- Tier weights (3, 2, 1) are not shown in this variant; the verdict rule stays internal.
- Segmented control: 3 px padding, 999 px radius, active = `fg` fill with dark text. Use `role="tablist"` with arrow-key support.

### 6. Mobile (390 px) (`reference/mobile.html`)
- Input E and Results D as above. Minimum control height 44 px. Content gutter 18 px.
- Results D source block (changed in review): topic title on the first line (15/1.35, weight 500, white), the URL below it in mono 12 px in the lighter grey. No border, box or pill. Long values wrap, never truncate with an ellipsis. "N claims" stacks under it, left aligned.
- Results D accordion header: wraps; minimum height 56 px; 14 px by 16 px padding; chevron 20 px, white. Claim text 15/1.35 weight 500. Verdict chip and confidence meter sit in a two-column row (140 px, then auto) so the meter starts at the same x for High, Medium and Low. Open body padding 0 16 18; source title 15 px, evidence 13.5 px, 8 px gap between source lines.
- "Check another link" (label, text input and a "Check" button on one row, input 12 by 14 px padding, `flex: 1`) was added to results E (source sheet) in review. The chosen D has no such field in the live artifact; the reference page shows it under the accordion as a proposal, in line with the retry fields on the error screens. Confirm.
- Toasts sit at the bottom with safe-area inset padding.

## Copy deck

- Brand: VerifAI. Lead: "Is it true? Check the sources."
- Button: "Check claims". Tabs: "Link", "Paste text". Labels: "Video or article link", "Text to check", "Try another link".
- Hint: "Paste a YouTube or article link." / "Paste at least 100 characters so there are claims to check."
- Inline link error: "That does not look like a link. Start with https:// and paste the full address."
- Short text error: "That is too short to hold checkable claims. Paste at least 100 characters."
- Verdicts: Supported, Contradicted, Disputed, Not enough evidence. Stances: Supports, Contradicts, Not addressed.
- Empty state: "Nothing checked yet" / "Paste a video or article link and the claims will appear here."
- No em dashes anywhere in UI copy.

## Accessibility rules

- Colour is never the only cue; every verdict, stance and tier has an icon or word.
- Contrast: `mu` on `bg` is about 6:1; dark text on every verdict fill passes.
- Toast and inline errors use `role="alert"`; the segmented control is a real tablist; accordion uses native `details`.
- Visible focus on every control. All animation off under `prefers-reduced-motion`.
- External links: `target="_blank"` with `rel="noopener noreferrer"`.

## Suggested React structure

`App.jsx` holds one state: `idle | loading | results | error`. Components: `LandingForm`, `LoadingStage`, `ResultsView`, `ClaimAccordion`, `SourceList`, `DisputedTabs`, `Toast`, plus the small shared ones above (`VerdictBadge`, `ConfidenceMeter`, `TierBadge`, `StanceChip`, `SourceRow`). Keep the API contract in `src/api.js`. Build order: tokens, shared components and component sheet, landing, loading, results with fixtures, disputed tabs, toasts and error mapping, mobile pass.

## Review edits already folded in

These were made on the live artifacts through comments after the first publish and are now in the references and this spec: white chevrons; verdict and confidence visible in the collapsed accordion header (desktop and mobile); header aligned with the claim cards; fixed-width confidence column; mobile source block as topic plus URL without a box and without truncation; larger tap targets on the mobile accordion; mobile input E with the centered 34 px name; retry field on No claims found and Partial failure toasts. One comment (aligned "as well" on the results header) got a clarifying question and is still open on the artifact.

## Open questions

0. Add the "Check another link" row to the mobile results accordion (currently only in results E)?
1. Solid chip on every screen, or only the component sheet (see Chosen directions)?
2. Failed claim text is not in the API; show "Claim N" or change the backend?
3. Show a "taking longer than usual" line after 60 s?
