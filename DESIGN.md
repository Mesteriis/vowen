---
name: Vowen
description: A private workspace in dark velvet, warm gold and burgundy.
colors:
  background: "#0e0d0c"
  surface: "#191614"
  raised: "#221c18"
  inset: "#100f0e"
  text: "#f3e9dc"
  muted: "#c0ad98"
  gold: "#e4bd7a"
  gold-hover: "#f1d3a3"
  on-gold: "#25190f"
  burgundy: "#63322f"
  rose: "#efaaa0"
  outline: "#574432"
  control-outline: "#806344"
  focus: "#f3c276"
  error: "#ffb8ac"
  approved: "#c1dfc2"
  approved-outline: "#688c6a"
  startup: "#090909"
  native-outline: "#967958"
  native-surface-low: "#151210"
  native-surface-highest: "#2d241d"
typography:
  headline:
    fontFamily: '"Cormorant Garamond", Georgia, serif'
    fontSize: "28px"
    fontWeight: 400
    lineHeight: 1.2
  title:
    fontFamily: '"Cormorant Garamond", Georgia, serif'
    fontSize: "23px"
    fontWeight: 400
    lineHeight: 1.2
  item-title:
    fontFamily: '"Cormorant Garamond", Georgia, serif'
    fontSize: "20px"
    fontWeight: 400
    lineHeight: 1.2
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    lineHeight: 1.55
  button:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: ".9rem"
    fontWeight: 600
  metadata:
    fontSize: ".9rem"
  status:
    fontSize: ".75rem"
rounded:
  tag: "5px"
  control: "6px"
  navigation: "8px"
  surface: "12px"
spacing:
  compact: "8px"
  control-inline: "12px"
  content: "16px"
  compact-section: "20px"
  section-gap: "24px"
  section: "28px"
  page: "32px"
components:
  button-primary:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.on-gold}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  button-primary-hover:
    backgroundColor: "{colors.gold-hover}"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.gold}"
    rounded: "{rounded.control}"
    padding: "10px 17px"
  field:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "11px 12px"
  section:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.surface}"
    padding: "28px"
  status-tag:
    textColor: "{colors.gold}"
    typography: "{typography.status}"
    rounded: "{rounded.tag}"
    padding: "4px 8px"
  navigation-link:
    rounded: "{rounded.navigation}"
    padding: "13px 16px"
  report-attempt:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text}"
    padding: "12px 16px"
---

# Design System: Vowen

## Overview

**Creative North Star: "Dark velvet and warm gold"**

The supplied Luxury Rituals Showcase defines the material world: near-black velvet, restrained gold, burgundy accents and warm ivory text. The Gold V Heart-Knot Crest identifies the workspace; the Embossed Velvet V Emblem belongs to startup. Both assets remain local.

Daily screens use readable content, quiet divisions and serif headings. Web and native Android share this palette and identity; Android retains Compose Material components and platform interaction patterns rather than copying browser geometry.

**Key Characteristics:**

- Dark tonal surfaces with warm, readable text.
- Gold actions and burgundy navigation emphasis.
- Serif headings paired with system UI body text.
- Local crest and velvet startup artwork; responsive native interactions.

## Colors

### Primary

Warm gold identifies primary actions, navigation accents, summary values and the wordmark. Gold-hover lightens web primary buttons; on-gold supplies their dark text.

### Secondary

Burgundy anchors the current web navigation emphasis and native primary/secondary containers. Rose distinguishes a request for changes. Approval has its own pale green text and outline; errors use warm coral. Status wording remains visible.

### Neutral

Background is the near-black canvas; surface holds sections; raised supports secondary controls; inset holds fields and report attempts. Ivory text and muted warm beige divide primary content from metadata. Fine brown outlines separate surfaces and controls. Native outline and surface steps are separate tokens because the Compose palette explicitly differs from web borders.

**The Material Continuity Rule.** Keep the supplied crest, velvet artwork and warm dark palette together across clients.

## Typography

**Heading Font:** Locally bundled Cormorant Garamond on both clients; Georgia and serif are the web fallbacks. Android applies the bundled face to displayLarge/Medium/Small, headlineLarge/Medium/Small and titleLarge/Medium.

**Body Font:** System UI stack on web; default Material Typography on Android.

### Hierarchy

Web section headlines use the headline token, subheadings use title, and occurrence names use item-title. Member page titles are 32px on desktop and 27px on compact screens; other page titles use clamp(28px, 3vw, 40px). Section headlines reduce to 26px at the compact breakpoint. The startup wordmark is 36px Cormorant Garamond. The font is self-hosted with an OFL license; no remote font request is required. Body font size remains the browser default, with a 75ch paragraph maximum; metadata and status use the frontmatter roles. Native sizes and weights remain the installed Material defaults rather than a separately claimed numeric type ramp.

**The Readable Ritual Rule.** Use serif type for headings and system UI type for reports, forms and controls; preserve readable wrapping for long content.

## Layout

The web member workspace is a centered grid capped at 1500px: 210px navigation, a flexible content column, 40px gap and 32px page padding. Below 1100px, navigation narrows to 170px, the gap and padding become 24px, and ritual updates move below the main list. At 760px and below, content becomes a single block with 18px page padding and a horizontally scrollable navigation row. Section padding becomes 20px. Summary counts keep three columns; compact ritual summaries place number and label side by side. Compact ritual sections use 16px padding and 12px top margin; navigation bottom margin is 8px. Compact member controls use 8px 10px padding with a 6px gap, hide the repeated member heading and keep actions visible. The ritual section subtitle is hidden on compact screens, and occurrence rows reduce to 12px vertical padding. Form field pairs retain two flexible columns.

Web ritual content uses a 2:1 main/update split with a 36px gap before collapsing. Modal content caps at 650px wide and 85dvh high with internal scrolling. General non-member pages cap at 820px. Safe-area padding protects the page edges.

Native workspace navigation changes at 720dp: a 156dp side column with a 24dp content gap on expanded screens, scrollable tabs below that width. Ritual content uses an 8dp vertical rhythm and 16dp card padding. Web interactive fields/buttons have a 44px minimum height; Android keeps Material touch behavior.

## Elevation & Depth

The web system uses tonal layering and fine borders without box shadows. Reports and inputs sit on inset surfaces; major sections sit on surface. The modal backdrop is translucent black (#000b). Android uses the configured Material dark surface roles, including its low and highest container steps, with default Material component elevation behavior.

**The Tonal Depth Rule.** Separate daily surfaces with tone and fine warm borders; do not add decorative drop shadows to the extracted web system.

## Shapes

Web sections and dialogs use the surface radius, navigation/fieldsets the navigation radius, controls the control radius and status tags the tag radius. Report attempts remain rectangular. Borders are one pixel. Android retains Material shapes, including rounded buttons and cards; the web radius scale is not a native override.

## Components

### Buttons

Gold filled primary actions have dark text, a fine gold-brown border and the primary padding token. Secondary actions use raised surfaces, gold text and a control outline; member controls use a quieter 500 weight and compact 8px 12px padding. Hover lightens primary fill and warms secondary fill. Disabled web buttons use .5 opacity; focus-visible uses a 3px gold outline with 4px offset. Native Button and TextButton use the Material palette and states.

### Inputs / Fields

Inset fills, warm outlines and rounded corners distinguish web fields; textareas resize vertically. Focus shares the gold outline. Native fields use OutlinedTextField, preserving platform labels and enabled states.

### Cards / Containers

Major web sections use a surface fill, thin outline and section padding, reducing on compact screens. Occurrences are divided rows within the section rather than individually raised cards. Native occurrences use Card with 16dp internal padding. Report attempts use the inset panel pattern and preserve line breaks.

### Chips

The web status tag is a noninteractive outlined label. Default status uses gold, approved uses pale green, and needs_changes uses rose. Native status is text, not a custom chip. Both clients localize status labels and dates for Russian/English, preserving machine status keys separately.

### Navigation

Web desktop navigation is sticky at 32px and becomes a horizontal overflow row on compact screens. The first link currently carries burgundy emphasis; it is not a scroll-tracking active-state system. Native uses NavigationDrawerItem on expanded screens and ScrollableTabRow/Tab on compact screens, with actual selected-tab state.

### Startup

The velvet image is centered against the startup canvas with a serif wordmark and loading copy. Web gates it on instance bootstrap; native StartupGate uses the supplied loading state. There is no progress percentage or decorative animation. Reduced-motion disables smooth web scrolling.

## Do's and Don'ts

### Do:

- **Do** preserve the user-supplied crest and startup artwork as local assets.
- **Do** keep gold focus outlines visible and respect reduced-motion scrolling.
- **Do** retain native Android controls, typography roles and adaptive navigation.
- **Do** present explicit status text alongside status color.

### Don't:

- **Don't** reproduce miniature low-contrast showcase text in functional controls.
- **Don't** invent portraits, ratings, points or activity metrics to fill the design.
- **Don't** add a fake loading percentage or a cosmetic minimum startup delay.

<!-- Implementation extension 2026-10-15: rewards reuse catalogue rows and grant cards
with status/history and explicit native actions; reports add bounded file selection
and HTTPS links inside the existing protected dialog. These preserve current tokens.
Recipient grants lead on native; catalogue follows. Files are saved/downloaded explicitly. -->
