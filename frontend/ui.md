# UI Design System Reference — Portkey.ai Inspired

> Extracted from [portkey.ai](https://portkey.ai) and adapted for Tone (AI Voice Agent Builder).
> This document serves as the single source of truth for the Tone authentication pages and future dashboard styling.

---

## 1. Theme Mode

- **Default**: System preference detection via `next-themes`
- **Dark mode**: `.dark` class on `<html>` element
- **Light mode**: `:root` (no class)
- **Toggle**: Sun/Moon icon button on auth pages; system dropdown in dashboard settings

---

## 2. Color Palette

### Primary / Accent

| Token             | Hex       | RGB                  | Usage                       |
| ----------------- | --------- | -------------------- | --------------------------- |
| `--primary`       | `#814ac8` | `rgb(129, 74, 200)`  | Buttons, links, focus rings |
| `--primary-light` | `#df7afe` | `rgb(223, 122, 254)` | Hover accents, gradients    |
| `--primary-dark`  | `#6d28d9` | `rgb(109, 40, 217)`  | Pressed states              |
| `--accent-cyan`   | `#06b6d4` | `rgb(6, 182, 212)`   | Info highlights, badges     |
| `--accent-orange` | `#ff7700` | `rgb(255, 119, 0)`   | Warnings, attention         |
| `--accent-blue`   | `#006fff` | `rgb(0, 111, 255)`   | Links, interactive          |

### Semantic / Status

| Token             | Hex       | RGB                 | Usage                      |
| ----------------- | --------- | ------------------- | -------------------------- |
| `--success`       | `#00d68f` | `rgb(0, 214, 143)`  | Success states, checkmarks |
| `--success-light` | `#9cf35b` | `rgb(156, 243, 91)` | Success backgrounds        |
| `--warning`       | `#fff700` | `rgb(255, 247, 0)`  | Warning indicators         |
| `--error`         | `#ff0f00` | `rgb(255, 15, 0)`   | Error states, destructive  |
| `--info`          | `#00badb` | `rgb(0, 186, 219)`  | Informational              |

### Neutrals — Light Mode

| Token                | Hex       | RGB                  | Usage                |
| -------------------- | --------- | -------------------- | -------------------- |
| `--background`       | `#ffffff` | `rgb(255, 255, 255)` | Page background      |
| `--surface`          | `#f6f7f9` | `rgb(246, 247, 249)` | Cards, panels        |
| `--surface-elevated` | `#fafafa` | `rgb(250, 250, 250)` | Elevated cards       |
| `--border`           | `#e6e6e6` | `rgb(230, 230, 230)` | Borders, dividers    |
| `--text-primary`     | `#0e0e0f` | `rgb(14, 14, 15)`    | Headings, body       |
| `--text-secondary`   | `#55555e` | `rgb(85, 85, 94)`    | Descriptions, labels |
| `--text-tertiary`    | `#a0a0a2` | `rgb(160, 160, 162)` | Placeholders, hints  |

### Neutrals — Dark Mode

| Token                | Hex       | RGB                  | Usage                  |
| -------------------- | --------- | -------------------- | ---------------------- |
| `--background`       | `#0e0e0f` | `rgb(14, 14, 15)`    | Page background        |
| `--surface`          | `#19191a` | `rgb(25, 25, 26)`    | Cards, panels          |
| `--surface-elevated` | `#232325` | `rgb(35, 35, 37)`    | Elevated cards, modals |
| `--border`           | `#292a2d` | `rgb(41, 42, 45)`    | Borders, dividers      |
| `--border-subtle`    | `#36363a` | `rgb(54, 54, 58)`    | Subtle borders         |
| `--text-primary`     | `#ffffff` | `rgb(255, 255, 255)` | Headings, body         |
| `--text-secondary`   | `#c4c3c7` | `rgb(196, 195, 199)` | Descriptions           |
| `--text-tertiary`    | `#a0a0a2` | `rgb(160, 160, 162)` | Placeholders, hints    |
| `--text-muted`       | `#55555e` | `rgb(85, 85, 94)`    | Disabled, ghost text   |

### Overlays / Transparency

| Token                | Value                       | Usage                |
| -------------------- | --------------------------- | -------------------- |
| `--overlay-white-60` | `rgba(255, 255, 255, 0.6)`  | Glassmorphism        |
| `--overlay-dark-80`  | `rgba(13, 13, 13, 0.8)`     | Modal backdrops      |
| `--overlay-white-05` | `rgba(255, 255, 255, 0.05)` | Subtle hover on dark |
| `--overlay-blue-20`  | `rgba(0, 111, 255, 0.2)`    | Focus indicators     |

---

## 3. Typography

### Font Families

| Role                   | Stack                                                                                         |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| **Display / Headings** | `"Inter Display", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` |
| **Body**               | `"Inter", "Figtree", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`       |
| **Code / Mono**        | `"JetBrains Mono", "Geist Mono", "Fragment Mono", "IBM Plex Mono", monospace`                 |

### Font Weights

| Weight   | Value | Usage                             |
| -------- | ----- | --------------------------------- |
| Regular  | `400` | Body text, descriptions           |
| Medium   | `500` | Labels, secondary headings        |
| Semibold | `600` | Buttons, form labels, subheadings |
| Bold     | `700` | Page headings, hero text          |

### Font Rendering

```css
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
font-display: swap;
```

---

## 4. Spacing & Layout

### Border Radius

| Token           | Value    | Usage                   |
| --------------- | -------- | ----------------------- |
| `--radius-sm`   | `4px`    | Small badges, tags      |
| `--radius-md`   | `6px`    | Inputs, buttons         |
| `--radius-lg`   | `8px`    | Cards, containers       |
| `--radius-xl`   | `12px`   | Modal, large cards      |
| `--radius-2xl`  | `16px`   | Hero panels, auth cards |
| `--radius-full` | `9999px` | Pills, avatars          |

### Buttons

| Property      | Value                                                  |
| ------------- | ------------------------------------------------------ |
| Height        | `36px` (default), `32px` (sm), `40px` (lg)             |
| Padding       | `8px 16px` (default), `8px 12px` (sm), `8px 24px` (lg) |
| Border radius | `6px`                                                  |
| Font weight   | `600`                                                  |
| Font size     | `14px`                                                 |
| Hover         | `opacity: 0.92` or `background` shift                  |
| Transition    | `all 150ms ease`                                       |

### Inputs

| Property          | Value                                          |
| ----------------- | ---------------------------------------------- |
| Height            | `40px`                                         |
| Padding           | `8px 12px`                                     |
| Border radius     | `8px`                                          |
| Border            | `1px solid var(--border)`                      |
| Background        | `transparent` (light), `var(--surface)` (dark) |
| Focus ring        | `2px solid var(--primary)` with `3px` offset   |
| Font size         | `14px`                                         |
| Placeholder color | `var(--text-tertiary)`                         |

### Cards / Containers

| Property      | Value                                   |
| ------------- | --------------------------------------- |
| Border radius | `8px` — `12px`                          |
| Padding       | `24px` (default), `16px` (compact)      |
| Border        | `1px solid var(--border)`               |
| Background    | `var(--surface)` or `var(--background)` |

---

## 5. Shadows

| Level | Light Mode                         | Dark Mode                          |
| ----- | ---------------------------------- | ---------------------------------- |
| `xs`  | `0 1px 2px rgba(0,0,0,0.05)`       | `0 1px 2px rgba(0,0,0,0.3)`        |
| `sm`  | `0 1px 3px rgba(0,0,0,0.1)`        | `0 1px 3px rgba(0,0,0,0.4)`        |
| `md`  | `0 4px 6px -1px rgba(0,0,0,0.1)`   | `0 4px 6px -1px rgba(0,0,0,0.4)`   |
| `lg`  | `0 10px 15px -3px rgba(0,0,0,0.1)` | `0 10px 15px -3px rgba(0,0,0,0.4)` |

---

## 6. Auth Page Layout

### Split Screen (Desktop)

| Property    | Value                                                                   |
| ----------- | ----------------------------------------------------------------------- |
| Left panel  | Form content — 50% width, centered vertically                           |
| Right panel | Brand illustration — 50% width, hidden on mobile                        |
| Mobile      | Full-width form, right panel hidden (`md:flex`)                         |
| Left bg     | `var(--background)`                                                     |
| Right bg    | Gradient: `linear-gradient(145deg, #1e1b4b, #312e81, #4338ca, #6d28d9)` |

### Right Panel Elements

- **Dot grid overlay**: `radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)` at `28px` spacing
- **Floating orbs**: 2-3 animated gradient circles
- **Voice waveform**: Animated bars (12 bars, staggered animation)
- **Headline**: "Build AI Agents That Sound Human"
- **Feature cards**: Glassmorphism — `background: rgba(255,255,255,0.06)`, `backdrop-filter: blur(16px)`, `border: 1px solid rgba(255,255,255,0.08)`
- **Trust indicators**: Bottom-pinned, `text-white/30`, uppercase tracking

---

## 7. Responsive Breakpoints

| Name  | Min-width | Usage                     |
| ----- | --------- | ------------------------- |
| `sm`  | `640px`   | Small adjustments         |
| `md`  | `768px`   | Tablet — show right panel |
| `lg`  | `1024px`  | Desktop                   |
| `xl`  | `1280px`  | Wide desktop              |
| `2xl` | `1440px`  | Ultra-wide                |

---

## 8. Animation

| Animation      | Duration | Easing                 | Usage           |
| -------------- | -------- | ---------------------- | --------------- |
| `fadeIn`       | `300ms`  | `ease-out`             | Page entrance   |
| `slideUp`      | `300ms`  | `ease-out`             | Form entrance   |
| `auth-float-*` | `15-22s` | `ease-in-out infinite` | Decorative orbs |
| `audio-bar`    | `1.4s`   | `ease-in-out infinite` | Voice waveform  |
| Button hover   | `150ms`  | `ease`                 | Scale + opacity |
| Input focus    | `150ms`  | `ease`                 | Border + ring   |

---

## 9. Tech Stack

| Layer          | Technology                          |
| -------------- | ----------------------------------- |
| **Framework**  | Next.js 15 (App Router)             |
| **UI Library** | shadcn/ui + Tailwind CSS v4         |
| **Theme**      | `next-themes` (class-based `.dark`) |
| **Font**       | Inter (via `next/font/google`)      |
| **Icons**      | Lucide React                        |
| **Forms**      | react-hook-form + Zod               |
| **State**      | Jotai                               |
| **Build**      | Turbopack                           |

---

## 10. Source References

- [Portkey.ai Homepage](https://portkey.ai/)
- [Portkey Pricing Page](https://portkey.ai/pricing)
- [Portkey Design Case Study](https://portkey.ai/blog/portkey-prompt-engineering-studio-a-user-centric-design-facelift/)
- [Portkey Observability Docs](https://portkey.ai/docs/product/observability)
- [Portkey Logs Docs](https://portkey.ai/docs/product/observability/logs)
