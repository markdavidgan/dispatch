---
version: alpha
name: Dispatch
description: >-
  An editorial newsroom aesthetic for a daily engineering brief app.
  Inspired by Monocle magazine and Field.io kinetic design.
  Restrained, high-contrast, almost monochrome with a single signal accent.
colors:
  primary: "#0b0b0e"
  paper: "#f9f7f2"
  paper-deep: "#f0ede5"
  ink: "#0b0b0e"
  ink-soft: "#2c2c30"
  ink-mute: "#787884"
  signal: "#ff2a2a"
typography:
  display:
    fontFamily: Inter Tight
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.5
  headline:
    fontFamily: Inter Tight
    fontSize: 2.625rem
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: -0.04em
  body:
    fontFamily: Inter Tight
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.5
  body-lg:
    fontFamily: Inter Tight
    fontSize: 1.0625rem
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.22em
    fontFeature: '"ss02" on, "ss03" on'
  label-nav:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.14em
  meta:
    fontFamily: JetBrains Mono
    fontSize: 0.625rem
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.22em
  numeral:
    fontFamily: Inter Tight
    fontSize: 12.5rem
    fontWeight: 800
    lineHeight: 0.85
    letterSpacing: -0.04em
  stat:
    fontFamily: Inter Tight
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1
    letterSpacing: -0.02em
rounded:
  none: 0px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  rail: 96px
components:
  nav-link:
    typography: "{typography.label-nav}"
    textColor: "{colors.ink-mute}"
    backgroundColor: transparent
    padding: "8px 14px"
  nav-link-active:
    typography: "{typography.label-nav}"
    textColor: "{colors.primary}"
    backgroundColor: transparent
    padding: "8px 14px"
  button-primary:
    typography: "{typography.label}"
    textColor: "{colors.primary}"
    backgroundColor: transparent
    rounded: "{rounded.none}"
    padding: "10px 16px"
  button-primary-hover:
    typography: "{typography.label}"
    textColor: "{colors.paper}"
    backgroundColor: "{colors.primary}"
    rounded: "{rounded.none}"
    padding: "10px 16px"
  button-signal:
    typography: "{typography.label}"
    textColor: "{colors.paper}"
    backgroundColor: "{colors.signal}"
    rounded: "{rounded.none}"
    padding: "10px 16px"
  project-row:
    typography: "{typography.body}"
    textColor: "{colors.primary}"
    backgroundColor: transparent
    padding: "12px 0"
  project-row-hover:
    backgroundColor: "{colors.paper-deep}"
  section-header:
    typography: "{typography.label}"
    textColor: "{colors.primary}"
    padding: "0 0 14px 0"
  card:
    textColor: "{colors.ink}"
    backgroundColor: transparent
    rounded: "{rounded.none}"
    padding: "18px 0"
  body-prose:
    typography: "{typography.body-lg}"
    textColor: "{colors.ink-soft}"
    backgroundColor: transparent
  ticker-dot:
    backgroundColor: "{colors.signal}"
    rounded: "{rounded.full}"
    size: "8px"
---

## Overview

Dispatch is a daily editorial brief for software projects. The visual identity is **Editorial Minimalism meets Engineering Newsroom** — inspired by Monocle magazine's information density and Field.io's kinetic restraint.

The design philosophy is:
- **Information first, decoration never.** Every pixel serves the content.
- **Restraint is the accent.** The palette is almost monochrome; a single red signal draws the eye to what matters.
- **Typography is the hierarchy.** Size, weight, and tracking do the work that color usually does.
- **Motion is information.** Animations indicate state (on-air dot), arrival (numeral fade-in), or urgency (bullet pulse) — never decoration.

The UI should feel like a premium broadsheet or a mission-control dashboard designed by a typographer: precise, confident, and quietly urgent.

## Colors

The palette is intentionally small. Four ink tones, two paper tones, one signal accent.

- **Paper (#f9f7f2):** Warm off-white foundation. Softer than pure white; reduces eye strain during long reading sessions. Used for all backgrounds.
- **Paper Deep (#f0ede5):** Slightly darker paper for hover states and subtle depth. Used for `project-row-hover` and alternate row backgrounds.
- **Ink (#0b0b0e):** Near-black for primary text, borders, and the sticky header rule. Not pure black — slightly desaturated to pair with the warm paper.
- **Ink Soft (#2c2c30):** Dark grey for secondary body text and article prose. Provides gentler contrast than pure ink for long-form reading.
- **Ink Mute (#787884):** Medium grey for metadata, captions, timestamps, and inactive nav links. The "whisper" layer of the hierarchy.
- **Signal (#ff2a2a):** The sole accent — a vivid red used sparingly. Indicates the "on-air" status dot, active project bullets, the audio play button when playing, and text selection. It should feel like a live broadcast light, not a warning.
- **Hair:** Near-transparent ink (`rgba(11, 11, 14, 0.08)`) for subtle dividers between project rows and sidebar cells. Not defined as a solid token because it relies on alpha compositing over paper.
- **Hair Strong:** Slightly more visible ink (`rgba(11, 11, 14, 0.16)`) for stronger dividers and grid borders. Also alpha-based, described in prose only.
- **Signal Dim:** A faint red wash (`rgba(255, 42, 42, 0.12)`) used occasionally for hover or focus backgrounds behind signal elements.

**Contrast discipline:** Signal (#ff2a2a) on paper (#f9f7f2) is below WCAG AA at 3.49:1 — this is an intentional design choice. Signal is used sparingly for the on-air dot, active bullets, and the audio play state, where it reads as a "live broadcast" indicator rather than body text. For actual text-on-signal usage (e.g., the Transmit button when playing), the context is a small UI control, not reading text. Ink on paper is effectively maximum contrast. Ink-mute on paper may be used for metadata where AA is not strictly required.

## Typography

Two font families, no more.

- **Inter Tight (Display):** Weights 400–800. Used for all display, headline, body, and stat text. The tight variant has reduced metrics that feel more editorial than standard Inter. Load weights 400, 500, 600, 700, 800.
- **JetBrains Mono (Meta):** Weights 400–600. Used exclusively for labels, metadata, navigation, timestamps, and UI chrome. Its slightly squared proportions give it an engineering feel without being aggressively technical. Load weights 400, 500, 600.

**Type scale (all in rems, base 14px):**

- **Numeral (12.5rem / 200px):** The signature element. A massive issue number on the homepage. Weight 800, tight leading (0.85), negative tracking. This is the visual anchor.
- **Headline (2.625rem / 42px):** Page titles and project names. Weight 800, leading 0.95, negative tracking.
- **Body (1rem / 16px):** Standard reading text. Weight 400, leading 1.5.
- **Body Large (1.0625rem / 17px):** Project row names and slightly emphasized body. Weight 600, leading 1.55.
- **Label (0.6875rem / 11px):** Section headers, uppercase, tracking 0.22em. The workhorse of the UI hierarchy — used for "Projects", "Today", "Briefings", masthead metadata. Always uppercase.
- **Label Nav (0.6875rem / 11px):** Top navigation links. Same as label but with 0.14em tracking (slightly less air).
- **Meta (0.625rem / 10px):** Smallest text — status badges, "HELD" dividers, inline metadata. Uppercase, tracking 0.22em.
- **Stat (2rem / 32px):** Large numbers in sidebar cells and issue counters. Weight 700, tabular-nums.

**Typography rules:**
- All labels and meta text are uppercase. This is non-negotiable.
- Tracking (letter-spacing) is used generously on small text to create air and authority.
- Negative tracking is used only on large display text (headlines, numerals) to tighten word-images.
- Font feature settings `ss02` and `ss03` on JetBrains Mono enable alternate glyphs for certain characters.

## Layout

The layout is **asymmetric and editorial**, not centered or balanced in the conventional sense.

**Container:**
- Max width: 1400px
- Horizontal padding: 16px mobile, 32px tablet+
- Centered with auto margins

**Homepage grid:**
- Desktop: `grid-cols-[minmax(0,8fr)_minmax(0,3fr)]` — an 8:3 split. The main content column is dominant; the sidebar is narrow and marginal.
- Gap between columns: 64px (gap-16)
- Left rail: On desktop, a 24px fixed ticker strip (`lg:pl-24`) sits at the viewport edge, not inside the container. It displays recent event timestamps in vertical text.

**Sticky header:**
- Full-width, border-bottom in ink
- Background: paper (opaque, no blur)
- Height: auto (py-4 padding)
- Contains: logo + on-air dot (left), navigation (right)
- Z-index: 20

**Project rows:**
- Grid: `grid-cols-[18px_1fr_90px_100px_24px]` — bullet, name, kind, stats, arrow
- Gap: 16px
- Border-bottom: 1px hair
- Hover: background shifts to paper-deep

**Section headers:**
- Flex, justify-between
- Label typography, uppercase, tracking
- Bottom border: 1px ink
- Often contain a counter or metadata on the right side in ink-mute

**Responsive behavior:**
- Below `lg` (1024px): Single column, ticker becomes horizontal scroll strip, sidebar stacks below main content
- The 8:3 grid collapses to a single column with standard vertical flow

## Elevation & Depth

**No shadows.** Depth is achieved through:
- **Borders:** 1px solid ink for major divisions (header, section headers). 1px hair for minor divisions (rows, cells).
- **Background shifts:** `paper` → `paper-deep` on hover or alternate rows.
- **Opacity:** Held projects are rendered at 55% opacity. Archived projects are hidden from the homepage entirely.

The design is deliberately flat. There are no cards with shadows, no elevated panels, no backdrop blur. The paper is the paper; ink is the ink.

## Shapes

- **Corners:** Almost everything is square (border-radius 0). The exceptions are:
  - The on-air dot: fully round (9999px)
  - Project bullets: fully round (8px circles)
  - No rounded buttons, no rounded cards, no rounded inputs
- **Lines:** All dividers are 1px. No thicker rules, no double borders.
- **Dots and indicators:** The on-air dot is 8px. Project bullets are 8px. Signal bullets pulse with a spreading shadow animation.

## Components

### Navigation
- Horizontal list of links: Today, Briefings, Projects, Podcasts
- Font: JetBrains Mono, 11px, uppercase, tracking 0.14em
- Inactive: ink-mute. Active: ink. Hover: ink.
- No underline, no background pill, no border. Pure typographic state.

### Project List
- Section header: "Projects" label left, "XX active · XX held" counter right
- Active projects first, then a hair divider with "HELD" label, then held projects at 55% opacity
- Each row: bullet indicator (red = active today, amber = recent activity, sand = quiet), project name in 17px semibold, kind label in 10px uppercase, live stats in mono, arrow
- Hover: background shifts to paper-deep, transition 120ms

### Audio Player (Transmit Button)
- A single button with a play-icon triangle and "TRANSMIT" label
- Default state: border ink, text ink, transparent background. Hover: background ink, text paper.
- Playing state: background signal, border signal, text paper. Icon pulses.
- Font: JetBrains Mono, 11px, uppercase, tracking 0.18em

### Masthead
- Three metadata items in a horizontal band: "Filed at", date, duration
- Font: JetBrains Mono, 11px, uppercase, tracking
- Separated by middots or thin spaces

### Filing Ticker (Wire)
- Desktop: Fixed to left viewport edge, 24px wide, vertical text showing recent event times and project slugs
- Mobile: Horizontal scroll strip below the masthead
- Font: JetBrains Mono, 10px, uppercase
- The latest event is highlighted; others are muted

### Addendum Card
- Appears below the lead hero when mid-day updates exist
- Label in JetBrains Mono (e.g., "Addendum — 14:32")
- Body in standard body text
- Animates in with a subtle translate-Y fade

## Do's and Don'ts

### Do
- Use uppercase + wide tracking for ALL labels, metadata, navigation, and timestamps.
- Use the 8:3 grid on desktop. Let the content breathe in the wide column.
- Use signal red sparingly — it should feel like a live broadcast light, not a warning banner.
- Use tabular-nums for all numbers (issue numbers, stats, counters) to prevent jitter.
- Respect `prefers-reduced-motion` — all animations should disable gracefully.
- Use the sticky header with an opaque paper background — no backdrop-filter blur.

### Don't
- Don't use border-radius on cards, buttons, or panels. The design is square-edged.
- Don't use shadows for elevation. Use borders and background shifts instead.
- Don't add decorative colors beyond the defined palette. No gradients, no pastels, no neon.
- Don't center-align major text blocks. The editorial aesthetic is left-aligned with an asymmetric grid.
- Don't use generic component libraries (shadcn/ui, Material, etc.) without heavy customization. Everything should feel bespoke and hand-set.
- Don't make the signal color feel like an error state. It's vitality, not danger.
