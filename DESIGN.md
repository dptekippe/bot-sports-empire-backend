# DynastyDroid Design System

> Created: 2026-02-22
> Purpose: Brand design system for all DynastyDroid pages

---

## Brand Words

- **Clean** — Minimal clutter, focused content
- **Futuristic** — AI-native, bot-centric aesthetic
- **Tech-focused** — Data-driven, analytical
- **High-contrast** — Dark backgrounds, bright accents
- **Premium** — Polished, professional sportsbook feel

---

## Color Palette

### Primary Colors
| Role | Color | Hex |
|------|-------|-----|
| Background Dark | Near Black | `#0a0a0f` |
| Background Card | Dark Gray | `#121218` |
| Background Row | Charcoal | `#1a1a24` |
| Border | Subtle Gray | `#2a2a3a` |

### Accent Colors
| Role | Color | Hex |
|------|-------|-----|
| Primary Accent | Electric Cyan | `#4a9eff` |
| Secondary Accent | Neon Lime | `#4CFF8F` |
| Danger | Coral Red | `#FF3B6B` |
| Royal | Purple | `#a855f7` |
| Hot Pink | Magenta | `#ec4899` |

### Text Colors
| Role | Color | Hex |
|------|-------|-----|
| Primary Text | Off-White | `#F5F7FA` |
| Secondary Text | Muted Gray | `#A0AEC0` |

---

## Typography

### Font Stack
- **Headings:** `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Body:** Same system stack for consistency
- **Monospace:** `'SF Mono', 'Monaco', 'Inconsolata', monospace` (for stats/numbers)

### Scale
- **H1:** 2.5rem (40px), bold
- **H2:** 2rem (32px), semibold
- **H3:** 1.5rem (24px), semibold
- **Body:** 1rem (16px), regular
- **Small:** 0.875rem (14px)
- **Caption:** 0.75rem (12px)

---

## Layout System

### Grid
- Max content width: 1200px
- Gutter: 24px
- Card padding: 20px

### Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

### Sections
1. **Hero** — Full-width, centered content
2. **Feature Cards** — 3-column grid
3. **Content Cards** — List/grid hybrid
4. **Navigation** — Sticky top bar

---

## Components

### Buttons
- Primary: Cyan background (#4a9eff), white text, 8px radius
- Secondary: Transparent, cyan border
- Hover: Brightness increase, subtle glow

### Cards
- Background: #121218
- Border: 1px solid #2a2a3a
- Border-radius: 12px
- Shadow: 0 4px 20px rgba(0,0,0,0.3)

### Inputs
- Background: #1a1a24
- Border: 1px solid #2a2a3a
- Focus: Cyan border glow

### Tabs
- Inactive: Muted text
- Active: Cyan underline + white text

---

## Visual Effects

### Gradients
- Hero: linear-gradient(135deg, #0a0a0f 0%, #121218 50%, #14141f 100%)
- Accent: linear-gradient(135deg, #4a9eff 0%, #4CFF8F 100%)

### Shadows
- Card: 0 4px 20px rgba(0,0,0,0.3)
- Glow: 0 0 20px rgba(74,158,255,0.3)

### Animations
- Hover transitions: 200ms ease
- Tab switches: 300ms ease
- Page loads: Fade in 500ms

---

## Page Templates

### Landing Page
- Hero with bot avatar + tagline
- Feature cards (3-4)
- CTA buttons
- Footer

### League Dashboard
- Sidebar navigation
- Tab content area
- Right panel (chat)

### Draft Board
- Center: Draft grid
- Left: Player pool
- Right: Bot commentary

---

## Usage

Use this design system in all Nano Banana Pro and Gemini prompts:

> "Use the DynastyDroid design system: dark theme (#0a0a0f, #121218), cyan accent (#4a9eff), clean modern typography, premium sportsbook aesthetic."

---

*Last updated: 2026-02-22*
