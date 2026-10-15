# Vowen interface QA — local web slice

Result: blocked

Scope: real Vue Mini App, selected luxury screenshot, shared day and relationship
selector. Native Android redesign is still pending and is not covered by this report.
The existing server and actual participants/agreements were not modified.

## Evidence and comparison

Source: owner-supplied `Vowen Luxury Rituals Showcase.png`. Source and implementation
were inspected together in one comparison input, comparing the tablet content area
and ignoring the physical device frame. Current synthetic API-backed desktop capture:
`artifacts/design/ui-context/home-current.jpg` (1600×1111 CSS viewport observed).
The ordinary screenshot wrapper distorted captures at browser zoom; the CDP
Page.captureScreenshot path is used for subsequent viewport evidence.

Mandatory surfaces:

- Fonts: Cormorant Garamond display headings, native sans-serif controls, readable
  hierarchy. Long Russian mobile headlines wrap naturally.
- Spacing: desktop sidebar, main/aside composition, four real counters, agenda and
  diary/forms shortcuts; mobile single column and five destination bottom bar.
- Colors: warm gold, rose active selection, near-black surfaces; the owner's later
  request adds a separate plain velvet page background. The owner subsequently removed light/system themes entirely; all clients remain dark.
- Assets: supplied crest and embossed emblem retained. The emblem does not fill or
  stretch to the viewport. Original pixels are preserved with a render-time feather
  mask. A generated emblem edit was rejected because it changed the motif. Generated
  plain velvet texture repeats independently. Hero is decorative, not a member photo.
- Copy: no invented presence, portraits, streaks, points, achievements or progress.
  Metrics come from authorized API data; name initials identify actual demo members.

Iterations: corrected full-page stretched emblem into separate background plus
unchanged emblem; removed hard square edge through feathering; added local debug
selector; changed Telegram entry to loader → verified member workspace, with no
login form mounted during automatic authentication.

## Functional evidence so far

- Real signed synthetic Telegram assertion opened the provisioned demo profile
  automatically. This is not a live Telegram acceptance test.
- Local DEBUG_AUTH login, sign-out and re-entry worked through real API sessions.
- Shared day displayed own occurrences, delegated reviews and offered rewards.
- Selecting an incoming relationship displayed Submissive, removed unrelated review
  counts and retained only that pair's occurrences/rewards.
- Mobile CSS viewport observed333×721 at existing browser zoom; scrollWidth333,
  no horizontal overflow. Bottom navigation and API-backed content rendered.
- 210 backend tests passed, Ruff/mypy, 12 web unit tests, web lint/typecheck/build passed.

## Remaining acceptance

Finish responsive interaction checks, error/empty states and the exact-commit
CI browser scenarios. Record console findings and final screenshots. Until these
are complete, this report remains blocked and does not claim full design acceptance.

Dark-only revision: mobile menu, profile and return-to-home were exercised through
real controls. An unlabeled avatar button was corrected to name its profile action;
the mobile destination dialog now has an explicit heading label. Light mode was
inspected before the owner removed it; it is no longer a supported state.

## Owner density revision

A later owner review rejected the oversized record treatment. Session records now
use body typography and62px mobile rows, an adjacent compact outline action, current
device identification and collapsed access history. Other record titles, card
padding, text rhythm and repeated headings were reduced across the interface.
Personal pages no longer spend a row on an irrelevant relationship selector.
The initial design captures are historical; final mobile/tablet captures are refreshed
after this revision. Native outline controls compile; full native design QA remains
a separate pending slice.
