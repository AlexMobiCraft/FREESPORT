# Electric Orange Design Tokens

**Версия:** 2.3.1  
**Дата:** 2026-01-05  
**Статус:** ✅ Active Standard  
**Source:** `design.json`

---

## 🎨 Palette (Colors)

### Primary Colors

| Token | Value | CSS Variable | Usage |
|-------|-------|--------------|-------|
| `--color-primary` | `#FF6B00` | `var(--color-primary)` | CTAs, Links, Active States |
| `--color-primary-hover` | `#FF8533` | `var(--color-primary-hover)` | Hover interactions |
| `--color-primary-active` | `#E55A00` | `var(--color-primary-active)` | Active/Pressed states |
| `--color-primary-subtle` | `rgba(255,107,0,0.1)` | `var(--color-primary-subtle)` | Backgrounds, Ghost hovers |
| `--color-primary-glow` | `rgba(255,107,0,0.4)` | `var(--color-primary-glow)` | Shadows, Focus rings |

### Background Colors

| Token | Value | CSS Variable | Usage |
|-------|-------|--------------|-------|
| `--bg-body` | `#0F0F0F` | `var(--bg-body)` | Page background |
| `--bg-card` | `#1A1A1A` | `var(--bg-card)` | Cards, Panels, Modals |
| `--bg-card-hover` | `#222222` | `var(--bg-card-hover)` | Interactive cards hover |
| `--bg-input` | `transparent` | `var(--bg-input)` | Input fields |
| `--bg-overlay` | `rgba(0,0,0,0.85)` | `var(--bg-overlay)` | Modal backdrops |

### Text Colors

| Token | Value | CSS Variable | Usage |
|-------|-------|--------------|-------|
| `--color-text-primary` | `#FFFFFF` | `var(--color-text-primary)` | Headings, Body text |
| `--color-text-secondary` | `#A0A0A0` | `var(--color-text-secondary)` | Meta info, Subtitles |
| `--color-text-muted` | `#666666` | `var(--color-text-muted)` | Placeholders, Disabled |
| `--color-text-inverse` | `#000000` | `var(--color-text-inverse)` | Text on Primary bg |

### Borders

| Token | Value | CSS Variable | Usage |
|-------|-------|--------------|-------|
| `--border-default` | `#333333` | `var(--border-default)` | Cards, Inputs, Dividers |
| `--border-subtle` | `#2A2A2A` | `var(--border-subtle)` | Subtle separators |
| `--border-hover` | `#444444` | `var(--border-hover)` | Interactive border hover |
| `--border-active` | `#FF6B00` | `var(--border-active)` | Focused inputs, Active tabs |

### Semantic Colors

| Token | Value | CSS Variable |
|-------|-------|--------------|
| `--color-success` | `#22C55E` | `var(--color-success)` |
| `--color-warning` | `#EAB308` | `var(--color-warning)` |
| `--color-danger` | `#EF4444` | `var(--color-danger)` |

### Shadows (Glow)

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-hover` | `0 0 20px rgba(255, 107, 0, 0.2)` | Interactive elements hover |
| `--shadow-primary` | `0 0 15px rgba(255, 107, 0, 0.4)` | Primary buttons, Active states |
| `--shadow-glow` | `0 0 30px rgba(255, 107, 0, 0.3)` | Strong emphasis |

---

## 📐 Geometry

### Skew

**Rule:** All interactive or "kinetic" elements must be skewed.

| Token | Value | CSS Variable | Usage |
|-------|-------|--------------|-------|
| `--skew-angle` | `-12deg` | `var(--skew-angle)` | Containers (Buttons, Badges) |
| `--counter-skew` | `12deg` | `var(--counter-skew)` | Text inside skewed containers |

### Border Radius

**Rule:** Strictly 0px everywhere. Sharp corners.

| Token | Value | CSS Variable |
|-------|-------|--------------|
| `--border-radius-none` | `0px` | `var(--border-radius-none)` |

---

## 🔤 Typography

### Fonts

| Token | Value | CSS Variable | Usage |
|-------|-------|--------------|-------|
| `--font-display` | `'Roboto Condensed', sans-serif` | `var(--font-display)` | Headings, Buttons, Prices |
| `--font-body` | `'Inter', sans-serif` | `var(--font-body)` | Body text, Inputs, Labels |

### Weights

| Token | Value | Usage |
|-------|-------|-------|
| **Black** | `900` | Display XL, L, M |
| **Bold** | `700` | Headlines, Buttons, Prices |
| **SemiBold** | `600` | Titles |
| **Regular** | `400` | Body text |

### Sizes (Display)

| Token | Size | Line Height | Usage |
|-------|------|-------------|-------|
| `Display XL` | `72px` | `80px` | Hero Banners |
| `Display L` | `56px` | `64px` | Page Titles |
| `Display M` | `48px` | `56px` | Section Headers |

### Sizes (Body)

| Token | Size | Line Height | Usage |
|-------|------|-------------|-------|
| `Body L` | `18px` | `28px` | Lead Paragraphs |
| `Body M` | `16px` | `24px` | Default Body |
| `Body S` | `14px` | `20px` | Compact UI |
| `Caption` | `12px` | `16px` | Badges, Meta |

---

## 📏 Spacing

| Token | Value | CSS Variable |
|-------|-------|--------------|
| `--spacing-1` | `4px` | `var(--spacing-1)` |
| `--spacing-2` | `8px` | `var(--spacing-2)` |
| `--spacing-3` | `12px` | `var(--spacing-3)` |
| `--spacing-4` | `16px` | `var(--spacing-4)` |
| `--spacing-5` | `20px` | `var(--spacing-5)` |
| `--spacing-6` | `24px` | `var(--spacing-6)` |
| `--spacing-8` | `32px` | `var(--spacing-8)` |
| `--spacing-10` | `40px` | `var(--spacing-10)` |
| `--spacing-12` | `48px` | `var(--spacing-12)` |

---

## 🎬 Animation

| Token | Value | CSS Variable |
|-------|-------|--------------|
| `--duration-fast` | `0.15s` | `var(--duration-fast)` |
| `--duration-normal` | `0.3s` | `var(--duration-normal)` |
| `--easing-default` | `cubic-bezier(0.25, 0.46, 0.45, 0.94)` | `var(--easing-default)` |

### Keyframes

- `slideInRight`: TranslateX 100% -> 0%
- `slideOutRight`: TranslateX 0% -> 100%
- `spinnerBarFill`: Opacity/Scale animation for spinner bars
