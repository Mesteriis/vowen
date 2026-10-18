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

## Selected compact entry variant (2026-10-16)

Source: first displayed ideation result,
`/Users/avm/.codex/generated_images/01a13ec4-c67e-7871-84f2-defcce20ba28/exec-c9753daf-6c2e-41d1-9553-eb0329a8f27a.png`.
Implementation: `artifacts/design/ui-context/entry-strip-desktop.png` and
`entry-strip-mobile.png`. Same selected synthetic member: Алекс · демо.
Focused comparison: `entry-strip-comparison.jpg` puts source and implementation
in the same input, normalizing the source component crop1097×257 to516×121.
Implementation component measures516×131 CSS px at1272px desktop viewport;
mobile check observed433 CSS px, scrollWidth433, both controls44px high.
The native browser screenshot has surrounding viewport padding; it is not a
pixel-exact390px screenshot. No horizontal overflow was observed in DOM metrics.

Fonts: compact system sans, quiet12px metadata,13px label and14px controls.
Spacing: one row with12px gap,16px padding,10px radius; source composition preserved.
Colors: existing dark/gold/rose tokens, muted separator and subdued metadata.
Images: original velvet/emblem unchanged; no new raster assets needed.
Copy: DEBUG / local development, participant field, short Sign in action;
removed copy and Telegram button do not return in debug mode.
No actionable P0/P1/P2 discrepancies in the focused comparison. Source uses a
slightly brighter gold action border (P3); existing product token retained.
Primary interaction verified: selecting a member enables the action and opens
that member's actual workspace. Temporary viewport override reset afterward.
Web lint, typecheck/build and12 unit tests passed. Live Telegram not exercised.
Final result: passed.

Entry annotation follow-up: compared `entry-strip-final.png` with `entry-blended.png`
in `entry-blend-comparison.jpg` at the same desktop state. Owner-requested differences:
12px inset library chevron; the brighter embossed pixels blend over page velvet
without a dark square. Typography, spacing, copy and source image dimensions remain
unchanged. Native select selection works; control height44px. No P0/P1/P2 findings
for this scoped polish. Final result: passed.

## Contextual rituals and relationship shop (2026-10-16)

Scoped continuation of the existing velvet/gold visual direction and owner's role
feedback. Captures: artifacts/design/ui-context/rituals-dominant-v2.png and
shop-dominant-v3.png. Actual local app at /, synthetic Alex -> Luna active context.
Dominant shop labels "Монеты участника: Луна · демо", provides credit/listing management
and no Buy action. Subordinate purchase/balance/history and390px overflow are covered
by real-API browser regression. Opposite-directed relationships remain distinct.

Fonts: existing serif headings/system controls. Spacing: compact rows and outline
controls, collapsed templates/settings/catalogue/history. Colors: existing dark,
gold and rose tokens. Images: original velvet and emblem retained. Copy: ownership
is explicit; no personal Dominant wallet, own executions hidden in Dominant context.
No P0/P1/P2 visual findings in the inspected desktop shop/ritual surfaces. This is
not acceptance of unfinished diary/stylus or full native navigation redesign.
Native builds passed; no native device visual acceptance or live Telegram evidence.
Final result for these scoped Mini App surfaces: passed.

## Selected Home direction and owner refinements (2026-10-16)

Source truth: /Users/avm/.codex/generated_images/01a13ec4-c67e-7871-84f2-defcce20ba28/exec-4a14e0ec-9e34-43df-a128-d9581b7fcf6d.png
(first displayed result). Follow-up owner requirements remove phone greeting/tagline
and reduce task text to16px, supporting text12–13px, section title22px. These take
precedence over the initial mock. No other page is redesigned.

Evidence: artifacts/design/ui-context/home-phone.png (390x844 CSS/pixels),
home-tablet.png (834x1194 CSS/pixels), home-phone-comparison.jpg and
home-tablet-comparison.jpg. CDP explicit CSS clips avoid IAB backing-density crop;
viewport overrides were cleared after capture. Source board1278x1230 contains frames
approximately380x1136 and822x1136; comparison crops are scaled uniformly to matching
width, without stretching. Source frame height differs from requested viewport;
this is a structural comparison, not a pixel-perfect/density-equivalent claim.
Synthetic Alex -> Luna active context; live API supplies two current-day tasks,
one pending report; source has three differently timed mock tasks. Data-count/date
content differences are intentional; no fake fixture records are inserted into UI.

Earlier P2: phone header retained80px minimum after greeting removal. Fixed to44px
and8px bottom gap; final capture shows context selector directly beneath compact
brand/profile. Empty upcoming section/footer removed. Earlier P2: icon-only wide
navigation lost link names; explicit aria-labels restore accessible names.

Typography: existing Cormorant/system families,16px sans task names,12px metadata;
smaller than initial mock by owner's explicit request. Spacing:76px task touch rows,
44px actions, single context selector; phone one column, tablet two columns, square
690px folded-device simulation uses supplementary column. Colors: existing dark
velvet/gold/rose tokens retained. Assets: original crest, velvet texture and trust
image reused; trust image is decorative, not uploaded report evidence. Copy: live
participant/status/report text, no invented counts or personal Dominant wallet.
Promotional bottom tile omitted under the owner's request to remove excess UI.

Interactions: actual IAB Review action opened the exact report dialog with current
text; cancelled and returned Home.19 real-API browser scenarios pass, including
review deep link, denied auth, error/retry and viewport overflow/touch checks at
390/690/768/1024 widths. No new console errors observed during interaction.

Native: Home component instrumentation passed at390x844,834x1194,690x828 in a local
Android emulator, selecting Dominant context and verifying the exact occurrence
callback. Screens:home-android-phone/tablet/fold.png. Six existing native real-host
navigation/consent/profile tests also passed. Component screenshots are not full
MainActivity navigation screenshots or physical Fold7 validation.18 native unit
tests/lint/debug/instrumentation builds pass. OS bars are emulator-owned.

No remaining actionable P0/P1/P2 in this scoped comparison with owner amendments.
P3: platform-native icon shapes differ; real Fold7 safe areas/font settings remain
physical-device acceptance. No deployment or live Telegram evidence.
Final result: passed.

## Annotated relationship picker (2026-10-16)

Owner screenshot of native white popup is the before-state, not a design to clone:
/var/folders/7z/9z8k42j54vb2zfhzw6nx82g00000gn/T/TemporaryItems/NSIRD_screencaptureui_4CnKwh/Снимок экрана — 2026-10-16 в 13.27.31.png
After:artifacts/design/ui-context/picker-phone.png at390x844 CSS/pixels and
picker-desktop.png at the normal IAB viewport. Scoped request is removal of OS
white/blue popup, poor contrast and one-line repeated context. Names14px, role/status
12px,60px touch rows, compact48/52px trigger. Existing dark/gold/rose tokens and
Tabler icons; no new raster assets. Selected check, explicit listbox/option state,
keyboard navigation and pointer closing verified. Same directional context values;
no permission behavior changes. Web lint/build/unit and real-API shop/responsive
checks passed. No P0/P1/P2 in the inspected opened-list states. Native menu not changed.
Final result: passed.

## Rituals: selected direction 3 + compact icon amendment (2026-10-16)

Source: /Users/avm/.codex/generated_images/01a13ec4-c67e-7871-84f2-defcce20ba28/exec-6a8f4153-d740-4a3d-a166-655ea7c975e0.png
Owner amendment: replace oversized schedule/reward/pause text buttons with icons.
Reused supplied velvet/crest/fonts; Tabler web icons and Android platform icons.
No new decorative raster assets. Compared source phone/list and wide inspector
with actual local renders: artifacts/deployment/ui-context/ritual-web-desktop.png,
ritual-web-phone-list.png, ritual-web-phone-detail.png and ritual-native-{phone,fold,tablet}.png.
Source is a composite; compare app-owned content at matching phone/wide states,
not generated device/outer frame. Synthetic API fixture cadence/title/count differ
from illustration and are preserved rather than faked for the screenshot.

Verified: charcoal/gold palette, compact grouped cards, underline tabs, selected
inspector, separate phone settings, 44px/dp icon action targets with accessible
names. Source text actions intentionally replaced per subsequent owner instruction.
Creation/schedule/reward dialogs, report/review/evidence/history remain functional.
Web real-API regression covers mobile dialog transitions, editor dismissal,
reward snapshot editing and report revisions; Android instrumentation covers these
compact controls and actual host navigation. Native visual captures use a Surface
and wait for platform window transitions. No remaining scoped P0/P1/P2.
P3: Android platform icon shapes differ from Tabler; physical Fold safe areas and
user font scaling still need real-device acceptance. No live Telegram/deployment.
Final result: passed.

## Ritual masthead annotation (2026-10-16 14:19)

Source: owner screenshot of excessive vertical gaps, attached in this conversation.
Scope: compact the existing selected ritual direction without another redesign.
After: artifacts/deployment/ui-context/ritual-header-phone.png (390x844) and
ritual-header-desktop.png (1280x1000), inspected against the supplied before-state.
Title/profile row, close context row and tabs/create row replace the previous
separate creation row. Mobile repeated brand is removed. No clipped tabs/actions
or horizontal page overflow observed. Real-API E2E bounds navigation to <170px
from title row at390/690/834 widths, and checks creation remains in the tab row.
Status feedback is below navigation. Content fade/3px entrance160ms and tab140ms
transitions are disabled under prefers-reduced-motion. Native compact heading
compiled/unit/lint checked; no new native screenshot claim in this follow-up.
No scoped P0/P1/P2 remaining. Final result: passed.

## Ritual relationship avatar annotation (2026-10-16 14:25)

Owner requested replacing the wide context strip with viewer avatar → relationship
symbol → partner avatar. Scoped after capture:
artifacts/deployment/ui-context/ritual-avatar-current.png and
web/test-results/ritual-avatar-phone.png. Initial-based avatars reflect the current
profile contract (no photograph field); no invented profile images or asset calls.
Directed arrow derives from the selected relation, never global profile labels.
Pause/revocation/proposal and shared-day symbols preserve distinct states; full
names/roles/status remain in the accessible dark menu and trigger tooltip.
Compact44px trigger fits beside title; separate context strip is removed only on
rituals. Existing keyboard/listbox/outside-dismiss retained. Web real-API tests
cover both roles and mobile/editor flows. Native parity compiled/lint/unit-tested,
without a new emulator visual acceptance claim. No scoped P0/P1/P2.
Final result: passed.

## Review queue card annotation (2026-10-16 14:33)

Before: owner screenshot of loose text on velvet. After:
artifacts/deployment/ui-context/ritual-review-current.png and
web/test-results/ritual-review-{390,690,1280}.png. Actual local review tab inspected
against the source annotation, preserving its synthetic report/recipient.
A bounded charcoal card groups identity/status, latest report, submission/evidence
metadata, history and a compact decision action. Four-line preview does not replace
the complete report in the decision dialog/history. Cards stay <=620px and inside
viewport; phone is one column. Card capture waits for entrance opacity1. Existing
request-change/approval/history/download regression passes. Android visual parity
compiled/lint/unit checked, without new emulator proof. No scoped P0/P1/P2.
Final result: passed.

## Template catalogue annotation (2026-10-16 14:33)

Before: owner screenshot with uncontained template text, wide text buttons and
inline version history. After: artifacts/deployment/ui-context/ritual-templates-current.png,
ritual-template-history.png and ritual-templates-{390,690,1280}.png. Inspected actual
local template and opened version history against the supplied before-state.
Cards group title/status/description and44px icon actions. Three-line descriptions
are previews; full descriptions remain in history/editors. Phone single column;
wider catalogue wraps cards. Separate history dialog avoids pushing the catalogue
down and closes with button/Escape. No new decorative assets; installed Tabler and
platform Android icons reused. Web actual interactions/card bounds tested; native
compiled/unit/lint checked, without a new native visual acceptance claim.
No scoped P0/P1/P2 remaining. Final result: passed.

## Compact review row + centered monograms (2026-10-16 15:32–15:35)

Owner rejected the tall nested report card and offset initials. After:
artifacts/deployment/ui-context/ritual-review-compact-current.png and latest
ritual-review-{390,690,1280}.png. Compared with the attached large-card/А–Л source
annotations. Review is now a roughly80px desktop row, with one-line text preview,
metadata and44px icon; full history/content live in the bounded dialog. Real-API
regression enforces <=140px row height across phone/Fold/wide and read-only history
has no decision controls. No large nested preview panel or list history remains.
Monograms share centered flex/line-height1 metrics; inspected А/Л raster bounding
centers deviate less than1px from circle centers. Android ritual initials disable
font padding; compact row/dialog changes compiled/unit/lint checked, not newly
visually accepted on an emulator. No scoped P0/P1/P2. Final result: passed.

## Journal: selected timeline + focused ink mode (2026-10-16)

final result: passed (web)

Sources: artifacts/design/ui-context/journal-reference-main.png and
journal-reference-ink.png, combined by the owner's explicit selection. The combined
handoff is journal-reference-combined.png. Opened main source with
journal-tablet-main.png and ink source with journal-tablet-ink.png together in one
comparison input. Rendered tablet frames are834x1194; additional phone captures
journal-phone-main.png and journal-phone-ink.png are390x844. Source renders have
matching portrait aspect; compared normalized product regions. Captures show a
separate synthetic Demo10 entry, not invented records in the owner's diary.

Fonts/typography: existing Cormorant24–28px headings,14px text and11–13px labels;
compact scale follows the owner's earlier mobile density corrections. Sample
handwriting is actual persisted test ink, not a decorative handwriting-font asset.
Spacing/layout: date rail, one expanded writing/reading surface, simple collapsed
rows, compact44px actions. Large inline handwriting from the initial mock is
intentionally a bounded preview because the owner selected a separate fullscreen
writing mode. Focused mode hides navigation. Mobile places six tools underneath
the paper; tablets place them right. Fold-sized wide views use the600px+4/5 aspect
breakpoint for the side toolbar. No page overflow observed at390/834; dialog fills
the viewport without hiding top save or tools.
Colors/tokens: existing near-black, ivory, gold and selected rose retained. Preview
surface corrected from transparent velvet to charcoal; writing sheet is charcoal.
Assets: supplied Vowen crest, existing velvet, Tabler UI icons retained. Canvas
renders user strokes and functional page guides, not substitute decorative assets.
Copy/content: date grouping, today's creation, private-by-default access controls;
removed search/tag filter/date input. Synthetic English account labels differ from
the Russian source; the real user's Russian page was separately inspected.

Fixed findings: mobile back control had no accessible label after hiding its text;
now explicitly labelled. Narrow native nib-width select truncated its label;
replaced by a44px cycling nib icon with descriptive label. No remaining P0/P1/P2
web findings. P3: individual nib colors and multi-page notebooks are not part of
this iteration.

Interaction evidence: typed text+stroke saved via real local API; reopening retains
stroke; undo/redo and segment eraser tested with normal viewport pointer input.
Emulated CDP pen coordinates did not hit the target; repeated this check without
emulation using Cua drag and confirmed eraser/undo. No physical stylus proof.
Access and date invariants have PostgreSQL tests. No browser console errors in the
separate QA session. Android source is updated but unbuilt/unverified per owner.

Final responsive follow-up:690x780 Fold-sized viewport has body=row and
pen tools=column with no horizontal overflow;390px has tools=row. The native
keyboard action now requests text focus after leaving ink mode. Native transient
draft state is session-bound ViewModel memory across configuration changes;
this behavior is source-only and is not included in the passed web QA result.
The source's previous/next-date footer is intentionally represented by returning
to the date timeline, avoiding a second navigation model during unsaved writing.

## Rules — selected option 1, 2026-10-16

final result: passed (web only)

Reference: generated option 1 `exec-dc1aeb43-55d2-4fbd-8c38-5509c0214565.png`, opened and inspected. Existing brand/fabric/fonts/icons reused. Compared expanded-card main view to `artifacts/design/ui-context/rules-tablet.png` and phone layout to `rules-phone.png`; task editor captures are `rules-phone-editor.png`, `rules-tablet-editor.png`, `rules-fold-editor.png`.

Preserved direction: charcoal accordion cards, separators for conditions/recipient, underline tabs, compact outlined icons, avatar pair context. Intentional adaptations: no redundant mobile brand bar; contextual author/recipient actions rather than role-inconsistent generated labels; tab is «Правила» because pending, paused and revoked assignments remain visible; user clarified «Наказание» is an existing-record selector. Never copy generated sample claims into real data.

P2 fixed: base dialog specificity prevented truly full-screen phone editors. Verified editor bounds 390×844 CSS px on phone; 540px wide bounded dialog at 834×1194 and 690×780. No horizontal overflow. Rule disclosure and punishment choices are excluded from the broad glass-action selector; tabs remain transparent and underlined. Reduced-motion disables reveal animation. Native dialog focus containment/ESC and keyboard activation of custom punishment disclosure exercised in web.

Interaction checks: create/save rule; existing punishment selector loads authorized records, saves current conditions snapshot, retains legacy text and allows none; publish; assignment stays pending consent; collapse/expand; role-specific context. Existing approval APIs and consent semantics retained. No new fake records are rendered client-side; the QA-labelled data is persisted only in synthetic local preview DB. Web typecheck + 18 existing unit tests passed; Android source/test changes unbuilt and not included in this passed result. Physical keyboard/IME, Telegram WebView and Android/fold hardware remain unverified.

Additional interaction verification: reopened the published rule in a fresh local login, opened exact version history, then reopened version editor and confirmed the previously selected punishment conditions remain selected. Subordinate context exposes «Предложить правило», hides author templates, opens the same punishment selector inside the approval request; Escape closes the request and restores focus. Console error/warning list was empty in the QA tab. QA tab closed; user tab preserved.

## Rewards marketplace — selected option 1, 2026-10-16

final result: passed (web only)

Reference: first displayed generation `exec-b475b0a7-0dfe-4557-a3e7-33d31f0670f2.png`. Opened alongside actual `rewards-phone.png` and `rewards-tablet.png` before final comparison. Preserved horizontal photo shelves, charcoal product cards, gold price/outline actions, role-specific balance/management and compact paired avatars. Reused existing global navigation instead of the generated alternate mobile nav. Real synthetic catalog has three listings, not the six illustrative products from the mock. Legacy versions default to the dinner cover; authors explicitly choose covers on new versions. No fake product fillers.

User-added audience field is included in management/create-lot flows, with one or multiple explicit authorized recipients. Availability is server-enforced rather than merely hidden in CSS. New backend tests exercise two recipients, concurrent creation, rollback on invalid target and stale revisions. Existing versioned rewards/history are preserved when hiding products.

P2 fixes during QA: reduced mobile product-card image/spacing to preserve density; aligned caption footers; excluded carousel navigation and product-image/disclosure triggers from action glass; reduced management/purchase photo height so fields/actions fit; screenshot capture accounts for document scroll when inspecting fixed dialogs. Verified exact 390×844 phone, 834×1194 tablet and 690×780 Fold dimensions through DOM metrics. Page overflow=false throughout. Fold dialog width 520px, phone purchase sheet width390 and bottom844 with accessible confirmation/remaining balance. See `rewards-phone-buy.png` and `rewards-fold-availability.png`.

Functional browser checks: create definition with selected cover/category, add priced listing, read/edit audience, hide/restore and observe receiver visibility, grant coins with comment, purchase exact item, observe one debit and received grant, keyboard carousel scroll, Escape closes dialog. Buyer console errors/warnings empty. Owner log contains one historical HMR missing-participants warning during editing; required prop was wired before audience verification and no later repeat observed. Current typecheck passes.

Checks: 232 backend tests; Ruff; Mypy72 sources; web typecheck;18 web tests; diff whitespace. Native source updates unbuilt/unverified. Physical Android/Fold, Telegram WebView and image-memory/performance tests remain outside this local web QA result; no claim of release or real-device proof.

### Rewards shared catalogue — 2026-10-16

Owner clarification: public products are visible to all space members; dominants
can view other authors' private active products. Editing remains author-only,
purchases use an active direct relationship wallet with the author. Implemented
server checks and web/native source controls; no new visual direction required.
Web: common-context catalogue visibly populated; public checkbox saved and reopened
checked for the synthetic evening item. Owner dialog captured in
`artifacts/design/ui-context/rewards-public-access.png`. DOM geometry at390×844 and
690×780 CSS px stays within viewport with no horizontal page overflow. Native
sources updated; no Android build/device proof. Server ACL/ledger regression
scenario passes; no production data or live Telegram used.

### Rewards 100-product fixtures — 2026-10-16

Exactly100 complete fixture records,100 distinct local covers (96 newly generated
individually through ImageGen and4 existing), native copies match. All100 assets
loaded in a temporary local review gallery and visually inspected in two captures;
review tab closed. Prompt set and generated-source manifest stored beside fixtures.
Actual app shows shelf counts63 and37 with working product cards and descriptions;
current user tabs preserved. Capture: `artifacts/design/ui-context/rewards-100-products.png`.
No native build/device claim.242 backend and18 web tests pass, typechecks/linters pass.

## 2026-10-16: магазин — права и резерв

- Локальная страница #rewards, synthetic Alex (switch), Sasha (dominant), Luna
  (bottom): действия соответствуют серверным разрешениям. У switch нет покупки,
  добавления/редактирования; доступность привязана к своему низу.
- У dominant открывается редактор чужой фикстуры, выключенный товар остаётся
  видимым с grayscale. Глобальный и персональный переключатели восстановлены.
- У bottom покупка показана как запрос с предупреждением о резерве. Реальная
  локальная заявка зарезервировала45 из80, верх увидел разрешение/отказ;
  отзыв снял резерв без списания. Погашение обоими участниками и гонки проверены
  PostgreSQL-тестами, не имитируются клиентом.
- Снимки: shop-switch-disabled.png, shop-dominant-disabled.png,
  shop-purchase-reserved.png, shop-purchase-approval.png.
- Web typecheck/18 тестов; backend246 тестов. Android изменения только в исходниках,
  без сборки/инструментального запуска. Live Telegram не проверялся.

## 2026-10-16: switch с верхним покупает

- Новое уточнение заменяет прежний запрет. В браузере выбран Alex→Sasha: виден
  собственный баланс0 и кнопки «Купить». Для Alex→Luna сохраняется «Доступ».
- Снимок:artifacts/design/ui-context/shop-switch-buy.png. Денежные данные design
  не менялись; цикл покупки switch проверен PostgreSQL-тестом.
- 16 тестов магазина/экономики, Ruff/Mypy/web typecheck прошли. Android исходники
  приведены к той же модели, без сборки и проверки на устройстве.

## 2026-10-16 — выбранный фото-список магазина

### Visual truth and capture

- Выбран третий ImageGen из последней тройки:exec-fbd36b75-1341-4f02-8422-acd08a4b79a3.png.
  Копия:artifacts/design/ui-context/rewards-selected-list.png,853×1844 pixels.
- Телефон:rewards-list-phone-v2.png,456×988 pixels; DOM viewport389.7×844.4 CSS px,
  browser density/zoom1.17. Нормализация source и implementation к390×844 для
  сравнения. Browser zoom влияет на физический clip; ранний урезанный exact-capture
  не использован как финальное evidence.
- Состояние:rewards, shop, Alex-switch в отношениях с Sasha-upper, баланс0,
  обе категории свёрнуты до4/3 строк;103 реальных локальных товара. В макете100,
  последние указания добавляют3 и удваивают верхние миниатюры — намеренное отличие.
- Совместное сравнение:rewards-list-comparison-v1.png и rewards-list-comparison-v2.png.
  Фокусированный сравнительный участок:rewards-list-detail-comparison.png.
- Дополнительно:rewards-list-tablet.png (1024×1194 CSS viewport),
  rewards-list-fold.png (730×844 CSS viewport),rewards-list-phone-sheet.png,
  rewards-list-final.png (обычное окно869×859). Это browser QA, не реальные устройства.

### Comparison history and fidelity

- V1 [P2]: яркая зернистая текстура мешала читать тонкие строки по сравнению с
  выбранным макетом. Исправлено:яркость реальной фоновой текстуры уменьшена
  только для магазина; параллакс сохранён. V2 повторно открыт и сравнён в общем
  и фокусированном обзоре; текст/цены отделяются от фона, actionable issue закрыт.
- Акценты действий:явный золотой цвет/контур и44px зона нажатия; исходные тёмные
  нейтральные иконки уточнены перед финальным сравнением.
- Typography:существующий Cormorant Garamond для заголовков, system sans для
  метаданных;17px названия,11px описание и24px шапка на телефоне. Компактнее макета
  намеренно, с учётом предыдущего требования владельца уменьшить размеры шрифта.
  Длинные названия переносятся, описания ограничены2 строками; нет обрезания цены.
- Spacing/layout:тонкие разделители,4/3 строки и порционное раскрытие вместо103
  строк сразу; увеличенная лента по последнему требованию. Планшетные колонки и
  последовательный Fold-список не переполняют документ по горизонтали.
- Colors/tokens:сохранены ivory/gold/rose/charcoal продукта, приглушена только
  интенсивность текстуры магазина. Табы и аватары не превращены в кнопочные панели.
- Images:реальные локальные103 фотографии, object-fit cover, без заглушек;
  новые3 обложки уникальны и побайтно совпадают в web/Android. Порядок/тексты/цены
  следуют данным, а не выдуманному порядку макета; старая цена свечи45 сохранена.
- Copy/content:магазин64+39, новый контент включён. Роль и контекст определяют
  покупку/доступ/редактирование; покупки не отправляются без проверки условий.
- Primary interactions:открытие и закрытие товара, недоступная покупка при балансе0,
  shop/requests, показать ещё7→15 и свернуть15→7, авто-пауза/возобновление.
- Motion:scrollLeft2285.47 не менялся на паузе; после возобновления и установки
  позиции перед краем цикл10608 замкнулся в1355. Reduced-motion удержал1355.128
  неизменным и animationName=none; настройки эмуляции возвращены в обычные.
  Нет длительных autoplay-анимаций вне явно запрошенной ленты.
- Console:последняя выборка error-логов пуста.18 web-тестов/typecheck прошли,
 14 backend-тестов магазина/фикстур/OpenAPI прошли. Без сборок и коммитов.
- Android:список, увеличенная автолента, пауза и анимации обновлены в исходниках;
  сборка и проверка на телефоне/планшете/Fold не выполнялись.

### Remaining notes

[P3] При желании можно отдельно уточнить визуальный акцент активного «Ещё» в нижней
навигации; это существующая общая навигация, в этом проходе не перерабатывалась.
Нет незакрытых P0/P1/P2 по проверенным web-состояниям. Приватные данные, балансы и
ранее созданные покупки при импорте сохранены. Автопрокрутка снова включена в
оставленной пользователю вкладке; временные размеры и reduced-motion сняты.

final result: passed

2026-10-16: scoped category/search follow-up. 103 fixture products / 12 shelves verified in rendered shop. Search «МАССАЖ» returns Массаж + Массаж рук, unmatched text has empty state, clear restores all shelves. Phone 389px: no horizontal overflow, 44px clear control, carousel hidden while searching. Tablet category grid 1024px: two columns / no overflow. Evidence rewards-categories.png, rewards-categories-phone.png, rewards-search-phone.png. Android source adapted; no native build/device verification. No new visual direction introduced.

2026-10-17 punishment types: functional extension of existing screen. Physical form has relation-scoped device/body selectors, add controls, count and 1–10 intensity. Ban switches to days; other omits typed parameters. Advanced settings collapsed. Browser dictionary addition persisted after reopening editor. Phone 389 CSS px one column/no horizontal overflow; tablet 1024 CSS px two columns/no overflow. Screenshots punishment-types-desktop.png and punishment-types-phone.png. Native Android source only, not built or device-verified.

## 2026-10-17 — Relationships profile, selected displayed option 2

Initial responsive finding: [P2] at 1024 CSS px the proposal action wraps below the partner strip, creating a largely empty extra toolbar row. At narrower tablet sizes the identity action group can also wrap to its own row. Fix: keep the tablet strip on one line with a labelled 44 px add icon and horizontal partner scrolling; use an explicit identity grid at 761–950 px. Validation of the revised capture follows below.

Current iteration result: blocked pending revised captures and reference comparison.

Additional [P2] from the correctly scaled 389 px capture: placing state/actions next to the names forces long real participant names onto multiple lines. Revised phone identity follows the source ordering (pair, names/roles, then state/actions on a separate row). Hide the horizontal strip scrollbar while preserving touch scrolling and a partial next item. No user data was shortened or replaced to match the mock.

### Revised comparison / final review — Relationships profile

- Source visual truth: `artifacts/design/ui-context/relations-selected-profile.png`, the second displayed generated image (`exec-21984900-4948-4110-8eaa-1689ab9bd989.png`), 1672×941 px concept board. Left desktop region 1245×941; right phone-content region approximately 382×884. The board is a visual concept, not a native 1:1 CSS screenshot.
- Implementation: `relations-profile-desktop.png` (1685×1198 raster, 1440×1024 CSS), `relations-profile-tablet.png` (1198×1397, 1024×1194 CSS), `relations-profile-fold.png` (1000×900, 854×769 CSS), `relations-profile-phone.png` (456×988, 389×844 CSS). Browser zoom 1.17, emulated deviceScaleFactor 1. Normalize desktop to 1440×1024 and phone to 389×844; reference crops and normalized implementation are letterboxed proportionally rather than stretched.
- State: Alex → Luna, active, version 3, confirmed 2/2, six actual server-provided scopes. Actual names retain synthetic-data suffixes and the existing longer agreement. The concept’s shorter sample names/agreement are not substituted into live records.
- Combined full-view comparison: `relations-comparison-desktop.png`, `relations-comparison-phone.png`. Focused identity/agreement/permission comparison: `relations-comparison-detail.png`. Source and implementation were opened together in these boards after the final changes.

**Findings / iteration history**

- Fixed [P2] redundant tablet toolbar row: proposal becomes a labelled 44 px icon at 761–1100 px, the partner strip remains one line and scrolls. Updated tablet/Fold captures show the agreement starts higher.
- Fixed [P2] squeezed phone participant names: identity now orders avatars → full-width names/roles → status/actions. Full actual names fit without being truncated. Final phone comparison verifies the correction.
- Accepted intentional differences: existing compact Rituals type sizes are retained, as requested earlier in this thread; no new large display typography. Permissions remain read-only actual scopes, so the concept’s misleading per-row navigation chevrons and expanded authority wording are omitted. The phone proposal action uses a labelled + icon to retain space. Longer real agreement copy and names increase phone scroll depth; bottom navigation stays available and content scrolls above it.

**Required fidelity surfaces**

- Fonts/typography: supplied Cormorant Garamond for headings/initials, system sans for controls/content. Compact 24–28 px headings and 13–14 px body/list text align with established page conventions; no clipped names or oversized greetings. Initials share the existing centered avatar style.
- Spacing/layout: selected profile structure, strip, open two-column composition and stacked phone layout retained. No opaque enclosing panel; dividers align with content. Tablet and phone P2 findings above corrected. Actual agreement line length capped at 65ch.
- Colors/tokens: existing cream, muted gray, gold, rose and green tokens reused. Green active status, rose pause/destructive action, visible gold focus. Actual inactive scopes are labelled inactive. Tab/navigation controls do not acquire glass fills.
- Image quality/assets: original crest and velvet texture reused at existing resolutions. Existing parallax remains. Tabler outline icons are reused; no fabricated logos, stock portraits, CSS illustrations or replacement background. New raster assets were unnecessary.
- Copy/content: actual contextual direction, agreement/version/confirmations and allowed scopes shown. No invented statistics, timestamps, transitively granted permissions or mock agreement overwrites.

**Interactions / checks**

- Browser: three partner choices update detail/header; paused status exposes request-resumption dialog; cancellation retains existing relationship; permissions expand/collapse; proposal form selects participant, direction and scopes, accepts agreement text, enables submission only with required fields, and closes/resets. No real proposal or relationship transition was submitted in this visual QA.
- Four CSS viewports above have no document horizontal overflow. Mobile action targets ≥44 px; native dialog focus/cancel and visible focus styles, reduced-motion fallback retained. Existing lower navigation remains visible while page content scrolls.
- Browser error log: empty. Web typecheck: passed. Vitest: 22 passed. Scoped `git diff --check`: passed. Backend/API/schema unchanged by this screen redesign.
- Native Android sources and regression-test sources updated, but no build or device run; physical touchscreen, Telegram WebView and Android rendering remain unverified.

**Implementation checklist**

- [x] Partner strip and selected profile on open velvet.
- [x] Shared compact header/menu, two-column desktop and stacked phone layout.
- [x] Real agreement/scopes and version-bound existing commands.
- [x] Separate proposal editor, pending/paused states and short action dialogs.
- [x] Responsive captures, combined reference comparison, two P2 fixes, typecheck/tests.

**Follow-up polish**

- [P3] A future physical-device pass can tune finger-scroll feel and density using real Telegram/Android WebView font rendering. No visual P0/P1/P2 remains in the verified Web scope.

final result: passed

## 2026-10-17 — Notifications, selected displayed option 2

Initial [P2]: at 389×844 CSS px, the save action ended at y≈795 while the persistent navigation began at y≈783, partially covering it on the initial view. Move reload into the compact mobile header beside the profile avatar; retain a thin divider and compact top padding. Revised capture and comparison follow below.

Current iteration result: blocked pending revised mobile capture.

### Notifications — revised/final comparison

**Source and captures**

- Selected source: second displayed image, `exec-f732aa5c-1ad3-44b9-b317-6842501e84c8.png`, copied as `artifacts/design/ui-context/notifications-selected-two-zones.png`. Concept board 1672×941 px, desktop region ≈1250×941 and phone-content region ≈377×915. These are concept-board regions, not native 1:1 CSS screenshots.
- Rendered implementation: `notifications-desktop.png` 1296×922 raster / 1440×1024 CSS; `notifications-tablet.png` 922×1075 / 1024×1194 CSS; `notifications-fold.png` 769×692 / 854×769 CSS; `notifications-phone.png` 350×760 / 389×844 CSS. Final browser zoom 0.9, emulated deviceScaleFactor 1. CSS sizes and zero scroll position were measured live before capture. Early captures at a different browser zoom were superseded; final captures use the measured zoom.
- Combined comparisons opened for review: `notifications-comparison-desktop.png`, `notifications-comparison-phone.png`, `notifications-comparison-detail.png`. Implementation normalized to the stated CSS size, source regions proportionally contained/letterboxed rather than stretched.
- State: both channel preferences on, bot disconnected, quiet hours off with configured 22:00–08:00 in Europe/Madrid. The connection preference is not presented as proof of bot opt-in.

**Findings / correction history**

- [P2] initial save action overlapped the bottom navigation at 389×844. Moving reload into the header removed a redundant toolbar row, followed by a small reduction in phone section/footer gaps. A second top-of-document measurement caught the remaining overlap. Final measurement at scrollY=0: save bottom ≈762.6 CSS px, navigation top ≈782.9. Full save target visible with ≈20 px gap. Final phone capture confirms the fix; no fixed overlay action was added.
- Intentional adaptations: restore compact icon rail/header and existing small typography, as explicitly requested across earlier screens, instead of retaining the old large sidebar shown by Image Gen. Personal avatar only. Long bot instructions and delivery notes are disclosures, as played back in the brief. Time fields are actually disabled with quiet hours off. Compact desktop content width is capped at 1080 px rather than enlarging text to fill the screen.

**Required fidelity surfaces**

- Typography: existing Cormorant Garamond headings (24–28 px), system sans body/controls. Compact 13–14 px primary labels and 11–12 px supporting copy retained; phone time inputs 16 px. No clipped labels, oversized greeting or duplicate page heading.
- Spacing/layout: selected two-zone hierarchy and divider preserved; stacked phone layout with visible save and existing bottom navigation. P2 overlap fixed; all four measured widths have no document horizontal overflow. Full-width clickable switch labels have a minimum 44 px target.
- Colors/tokens: existing gold, cream, gray and rose/green connection states; switch on/off distinction, muted disabled fields and visible focus. No opaque enclosing panel or blanket glass on navigation. Actions reuse existing glass.
- Image/asset fidelity: original velvet/crest and shared parallax reused. Tabler device, Telegram, moon, info and reload icons; no generated replacement imagery or fabricated decorative assets needed.
- Copy/content: two actual channels only, real server timezone and connection state. No fabricated inbox, counts, push settings, test-send control or relationship selector. Bot opt-in remains personal via the existing command. Quiet-hours explanation explicitly names Telegram; no promise that in-app tasks become inaccessible.

**Functional checks**

- Existing settings loaded; unchanged values saved successfully and success appeared only after server response. Telegram/in-app channels were not disabled, bot not connected, and no message was sent.
- Quiet toggle enables time fields; equal start/end disables save and shows the validation message. 22:00–08:00 is valid. This modified quiet draft was discarded by reloading, returning the original off state.
- Both explanatory disclosures open/close; compact reload works. Browser error log empty. Typecheck passed, 22 Vitest passed, scoped whitespace check passed. Backend/API contract unchanged.
- Native Android source/test-source updated, but no build or device test. Physical Fold/tablet, Telegram WebView and Android rendering are unverified.

**Implementation checklist**

- [x] Two open zones, compact shared navigation and personal avatar.
- [x] Real channel preferences, independent Telegram status and help.
- [x] Quiet-hour validation, timezone, explicit versioned save and success/error states.
- [x] Phone/tablet/Fold/desktop captures, combined full/focused visual comparison.
- [x] Mobile save overlap fixed and measured at page top.

**Follow-up polish**

- [P3] Physical-device testing can refine native time-picker appearance and switch feel. No actionable visual P0/P1/P2 remains in the verified Web scope.

final result: passed

## 2026-10-17 — Profile / Quiet Index (displayed option 1)

Scope: browser implementation only. Android changes are source-only and excluded from this visual pass.

Source visual truth: `artifacts/design/ui-context/profile-selected-quiet-index.png` (1536×1024 generated board; desktop x0–1116, phone x1124–1536). The generated frame ratios are approximate; crops were contained/letterboxed without stretching, so this is a composition/content comparison, not a claim of exact pixel parity.

Implementation: `profile-settings-desktop.png`, `profile-settings-tablet.png`, `profile-settings-fold.png`, `profile-settings-phone.png`, and final `profile-settings-window.png`, all under `artifacts/design/ui-context/`.

Viewports: 1440×1024, 1024×1194, 854×769 and 389×843 CSS px. Browser zoom measured 1.17, deviceScaleFactor 1. Explicit screenshot clips and captureBeyondViewport=false produced rasters 1685×1198, 1198×1397, 999×900, 456×987. No horizontal overflow at any size; scrollY=0. State: local synthetic Алекс, Settings → General, original language/timezone, no save pending. The source phone includes DEBUG; production-like compact mobile chrome intentionally hides this technical banner, consistent with earlier pages.

Full-view comparison evidence: `profile-comparison-desktop.png`, `profile-comparison-phone.png`. Focused field/typography comparison: `profile-comparison-detail.png`. These boards put source and implementation in the same image input and were opened and reviewed. Additional states: `profile-personal-phone.png`, `profile-notifications-phone.png`.

Fidelity surfaces:
- Fonts: supplied Cormorant Garamond headings and system sans fields retained; monograms centered. Compact 12–14px labels/body match existing application density; phone editable values are 16px. This is intentionally smaller than the generated board’s oversized chrome.
- Layout: two top underline tabs, left identity/index with divider on desktop, horizontal subsection navigation at ≤760px, max600px form. Open velvet retained. Phone Save is full-width for touch; refresh/logout are available below it. The desktop form does not stretch into unused viewport space.
- Tokens: original ivory, gold, muted, rose and border tokens; plain navigation has no glass/button fill. Action buttons keep the existing translucent dark treatment.
- Assets: existing crest and velvet pixels reused, no new raster approximations; Tabler library icons. The mock’s erroneous active Relations icon and lingering Sessions icon in main navigation are corrected: Profile is active and Sessions/Notifications exist only inside Settings.
- Content: actual language/timezone fields, name/self-description in the Profile tab, labels do not grant authority, existing privacy notice retained. No invented identity/upload/password features.

Findings: no actionable P0/P1/P2 visual differences. The visible differences listed above are intentional constraints from the existing app and the user’s navigation request. No P0/P1/P2 visual fix iteration was required. Functional QA caught a transient success message reset by a prop watcher; success is now set after nextTick and confirmed visibly. Keyboard focus is moved after the tab update and verified on the selected Profile tab.

Primary interactions checked: both forms submitted unchanged values and received Saved; draft remained across subsection switches and was restored without saving; old #notifications link opened Settings/Notifications; sessions list rendered; revoke-current confirmation opened and Cancel left the session intact; keyboard arrows changed tab and focus; mobile More excludes standalone notifications/sessions. No notification channel change, message delivery, or actual revocation was performed. Browser error log: empty. Typecheck and 26 Vitest pass. Native device/build validation skipped by explicit no-build constraint.

Implementation checklist: complete for browser scope. Residual gap: native Android runtime and real-device testing are not covered.

final result: passed

## 2026-10-17 — Separate personal profile and administrator settings

This revision supersedes the earlier Profile/Settings tab structure at the user's explicit request. The user's screenshot of the empty sidebar bottom is the placement reference; personal profile belongs to the avatar, space Settings belongs to the sidebar bottom. The user further specified independent administrator roles, automatic first-user bootstrap, and appoint/transfer actions. Earlier concept imagery is style grounding, not a pixel target for this changed information architecture.

Source: supplied `Снимок экрана — 2026-10-17 в 23.00.49.png` (374×278 sidebar crop; original temporary path supplied in the request). Implementation evidence under `artifacts/design/ui-context/`: `administration-window.png`, `profile-separated-window.png`, `administration-desktop.png`, `administration-tablet.png`, `administration-fold.png`, `administration-phone.png`, `profile-separated-desktop.png`, `profile-separated-phone.png`, `administration-denied-phone.png`, `administration-transfer-dialog.png`.

Combined inputs actually opened: `administration-sidebar-comparison.png` puts the supplied placement crop beside the rendered lower sidebar. `administration-profile-comparison.png` shows the separated routes together as a flow/composition check, not a claim that they are the same screen. No full-screen target was supplied for the new administrator list; it reuses existing Vowen tokens and rows. Images were contained, not stretched; the small user crop is qualitative placement evidence only.

Viewports: administration at 1440×1024 / 1024×1194 / 854×769 / 389×843 CSS px; profile at 1440×1024 and 389×843. Browser zoom 1.17, deviceScaleFactor 1; raster sizes 1685×1198 / 1198×1397 / 999×900 / 456×987. Explicit clips, captureBeyondViewport=false, scrollY=0. No horizontal overflow. Desktop settings link top≈935 within sidebar bottom≈1000 at the 1440×1024 viewport; it remains at the sidebar bottom at tablet/Fold sizes. Phone uses More instead of a sidebar.

Required surfaces reviewed:
- Typography: Cormorant headings, system sans controls, compact body/labels and 16px phone inputs retained. Role labels now wrap horizontally instead of three empty-height rows.
- Layout/spacing: personal tabs contain data, notifications and sessions. No Profile entry in the main menu, no personal controls in space Settings. All real buttons retain ≥44px height. Settings uses divided member rows; phone actions move below each identity instead of overflowing. The profile Save action is visible above the persistent phone menu at the tested size.
- Colors/tokens: original gold/ivory/muted colors, open velvet, selected rose navigation. No glass fill added to tabs. Settings highlight appears at the lower rail position.
- Assets: original crest/texture, Tabler icons, centered text monograms. No replacement raster/vector drawings.
- Copy: actual active participant names, explicit distinction between appointing another admin and surrendering one's own role. Administrator status does not imply personal-data or relationship access.

Iteration: initial personal form used vertically stacked role labels and two nearby separators, pushing Save down at the normal window size. Treated as P2 density drift; changed only the personal role fieldset to a wrapping row and retained one footer separator. Re-captured `profile-separated-window.png` / `profile-separated-phone.png`; Save is visible and no overflow remains. Administrative list required no P0/P1/P2 visual fixes.

Interaction evidence: personal avatar in Settings and Rituals opens Profile; ordinary participant can access personal data/notifications; direct #settings displays no access without member list; ordinary mobile More contains no Settings/Profile links. Both appoint/transfer dialogs show the target and different consequences, then Cancel leaves roles unchanged. Server integration tests perform the real grant/transfer/repeat/concurrency flows on vowen_test; no existing design-user rights were changed through the browser. Browser error log empty. Admin Settings remains open for review as Алекс, the first provisioned member.

No actionable P0/P1/P2 findings remain for browser scope. Native Android is source-only and not covered by this visual pass; no builds, commits or deployment.

final result: passed
