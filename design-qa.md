# Vowen Mini App design QA

Result: passed

Scope: the real Vue Mini App, including all11 member sections and guest form flows.
Native Android now uses dark-only appearance and compact outline actions and builds
successfully; a full native workspace redesign and physical-device visual acceptance
remain outside this web result. No production deployment or live Telegram proof is
claimed. All participants/content in these captures are isolated synthetic fixtures.

## Source and owner decisions

The source is the owner-supplied `Vowen Luxury Rituals Showcase.png`. Source and
implementation were inspected together in one comparison input, comparing content
regions rather than the physical phone/tablet frame. Subsequent explicit owner
feedback takes precedence: separate full-page plain velvet, unchanged embossed
emblem with softly feathered edges, dark-only appearance, outline controls and
compact records rather than large decorative cards.

Fonts: Cormorant Garamond display headings and system body/control typography;
record titles use compact body type. Body density, repeated headings and long Russian
wrapping were reviewed. Spacing: reduced card/record padding and nested form borders;
62px mobile session rows; no irrelevant relationship toolbar on personal pages.
Colors: near-black, gold and rose; no light/system theme or leftover selector.
Assets: supplied crest/emblem retained; emblem size/proportions are unchanged and
its outer fabric is feathered at render time. Plain velvet repeats independently;
the decorative hero never represents a participant portrait. Copy: authorized API
counts only, explicit contextual roles, no fabricated presence, avatars, streaks,
points or progress. Icons use one outlined library and preserve consistent alignment.

## Viewports and captures

Local evidence under `artifacts/design/ui-context/` is ignored by Git:

- `mobile-<section>.jpg`: all11 sections, final390×844 capture frames. Existing
  browser zoom yields a333px CSS viewport; scrollWidth333 for every section.
- `tablet-<section>.jpg`: all11 sections, final1024×1366 capture frames; observed
  CSS viewport875px, scrollWidth875 for every section.
- `mobile-pages-contact.jpg` and `tablet-pages-contact.jpg`: both complete sets
  were visually inspected after the density revision.
- `mobile-metrics.json` and `tablet-metrics.json`: per-section DOM measurements.
- `entry-velvet-final.png`: independent background and original feathered emblem.
- `home-empty.png`: an existing member without relations/tasks; no invented metrics.

The ordinary screenshot wrapper distorted some zoomed captures. Final captures use
CDP Page.captureScreenshot with an explicit frame clip and include page content only.
Exact390/768/1024 CSS widths are additionally exercised by the browser regression
suite at its standard zoom, traversing all11 destinations (33 section/viewport pairs).

## Interactions and states

Passed: automatic signed Telegram entry keeps the preloader until profile loading
finishes, with no login form mounted; unknown identity denial; local debug selection;
sign-out/re-entry; desktop/sidebar and mobile More/dialog navigation; profile saving;
relationship selection with different D/s roles; explicit consents/scopes and pause;
private diary and reader withdrawal; guest/internal form draft/review/receipt;
recurring surveys and retained answers; ritual report/evidence/review/revision;
reward acceptance; notification failures preserving edits; dark-only legacy settings;
compact session current-device identification and revocation of another session.
Home request failure shows unavailable counts/state, then recovers through retry;
it does not present a failed load as an empty successful day.

Fixed during QA: oversized record typography and padding; full-page stretched emblem;
hard square asset edge; duplicate recurring-survey panel; missing completion wait
before refreshing newly confirmed authority; off-screen confirmation dialog;
unnamed mobile profile action/dialog; time labels compressed by blanket checkbox
layout. No open P0/P1/P2 findings remain in this scoped web acceptance.

Accessibility: labeled inputs/actions, keyboard focus and native navigation dialog,
reduced motion, dark contrast, wrapping and practical44px action targets. Compact
session actions paint a smaller outline within the44px hit area. The existing
browser zoom was preserved. Footer/navigation do not cause horizontal overflow.

## Verification and limits

210 backend tests,12 web unit tests and18 real-API browser scenarios passed locally.
Ruff, mypy, web lint/typecheck/build and contract/secret/diff checks passed. Android
unit/lint/debug APK/instrumentation APK builds passed; instrumentation was compiled,
not executed on a physical device for this slice.

Checks CI for integration39c3e72 passed both backend-web and Android:
https://github.com/Mesteriis/vowen/actions/runs/38813788301
The last quiet-hour field layout correction also passed all18 browser scenarios
locally; its final commit is checked separately by the same required workflow.

No unhandled page errors occurred in the browser regression. The development console
retains one historical Vite HMR error for the intentionally removed appearance
component, before the final reload; no new errors appeared during the final11-page
inspection. Live Telegram, native device visuals and deployment remain unverified.
