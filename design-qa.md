# Participant profile design QA — 2026-10-18

**Source visual truth:** `static/web/design/profile/concept-passport-with-wizard.png`; selected original passport `static/web/design/profile/concept-passport.png`.

**Rendered implementation:** debug `http://127.0.0.1:5176/#profile` and isolated real-API Playwright instance. Evidence in `artifacts/deployment/ui-context/profile-v2/`: `desktop.png`, `mobile.png`, `wizard-mobile.png`, `visibility-mobile.png`, `comparison-desktop.png`, `comparison-mobile.png`, `comparison-focus.png`.

## Frames, density and states

- Source combined canvas: 1643×957 pixels. Desktop artwork occupies x=0..1220, mobile x=1237..1643. It is a generated concept sheet, not a browser screenshot with a known CSS density.
- Full desktop board crops the desktop artwork and scales it to 1440×1130 for composition comparison, beside an actual 1440×1024 debug screenshot. The extra source height is presentation aspect ratio, not an implementation overflow finding.
- Mobile artwork width 406 is normalized to 390. Actual Web screenshots use 390 CSS pixels / deviceScaleFactor=1, full-page height varies with real data. Playwright also verifies 768/1024/1440 widths with no page overflow.
- Concept has a populated synthetic profile. Actual screenshots deliberately retain empty participant data and show real empty states; no suggested practices or health facts are silently filled into a user's profile.
- Concept's mobile canvas mixes overview and wizard detail. Specification deliberately separates these states; actual wizard evidence is `wizard-mobile.png` (first chapter) and `visibility-mobile.png` (sixth chapter).
- Browser developer viewport overrides are temporary and reset after QA. No personal data or tokens are included in screenshots.

## Comparison history and fixes

1. **P1 — legacy section cards covered the velvet.** Initial screenshots showed one opaque passport panel and two nested overview cards, unlike the open editorial source. Scoped CSS removes legacy global `section` background/border/padding inside this feature. Post-fix board `comparison-desktop.png` shows velvet between sections.
2. **P1 — primary banner button had nearly black text on a transparent background.** A global button rule overrode its fill. Scoped primary action now has explicit gold background and dark foreground; desktop and mobile captures show readable actions.
3. **P2 — mobile biography stayed squeezed beside the monogram.** Mobile grid now gives biography/dynamics full width under name/avatar. Updated `mobile.png` and `comparison-mobile.png` show the corrected stack.
4. **P2 — mobile action bar could sit behind persistent navigation.** Wizard actions now stick above the bottom navigation and safe area. `wizard-mobile.png` and `visibility-mobile.png` show all actions; E2E publishes at 390px successfully.
5. **P2 — health action inherited an opaque button strip.** Final scoped override restores transparent row treatment. Post-fix debug capture is checked after this rule, consistent with open overview rows.

6. **P2 — inherited compact workspace typography reduced body readability.** Scoped profile copy now uses 15–16px, mobile 14px, with explicit heading sizes. Final debug capture and responsive E2E were repeated after the change.

## Required fidelity surfaces

- **Typography:** existing Cormorant Garamond headings and system sans controls retained. Hierarchy, wrapping and readable controls checked in full boards and the focused identity/banner/tab comparison. Dynamic empty text intentionally changes height versus the populated concept.
- **Spacing/layout:** desktop two-column open overview, mobile stack, compact side menu, underlined tab groups, distinct wizard chapter navigation. No page overflow at four tested widths. Horizontal tab scrolling is intentional; not every tab needs to fit 390px simultaneously.
- **Colors/tokens:** existing gold, ivory, muted text and velvet preserved. Gold primary actions have dark text; focus is visible, status labels are textual.
- **Images/icons:** existing repository crest/velvet assets and Tabler icons. Existing monogram remains the avatar as agreed; no photo-placeholder service or invented imagery. Reference selectors use real catalogue thumbnails where available.
- **Copy/content:** real account name and selected values only. Unknown is distinct from permission; health remains owner-private by default. Language/timezone and personal notification/session tabs remain available. No compatibility score or public matching was added.

## Functional and accessibility evidence

- Real API E2E passes: real catalogue practice selection with independent preference/experience/participation, wizard start, save, exit, reload with a fresh Telegram authentication payload, resume, skip, publish, ordinary-editor→wizard→publish preservation, delayed save with disabled inputs, network failure retaining entered text.
- 390/768/1024/1440px overflow assertions pass. E2E collected page errors: none.
- Debug first wizard step was opened with Enter and the heading receives focus. Field labels and explicit disabled states were inspected. Reduced motion has a local CSS override.
- Actual virtual keyboard on a physical phone and native Android rendering were **not** verified. Android source and tests exist, but Gradle/device execution is excluded by the user's no-build instruction. Web responsive QA does not establish Android acceptance.

## Intentional differences / residual gaps

- Empty-state content differs from synthetic populated artwork; this is required to avoid inventing participant preferences.
- Mobile uses practical ≥44px actions and a larger banner than the decorative scaled mock. This preserves usable touch targets.
- Wizard is a separate mode, per the written specification; no nested overview-plus-wizard page.
- No remaining actionable P0/P1/P2 visual findings in inspected Web states. Native/device keyboard validation remains explicitly unverified, not reported as passed.

**final result: passed**
