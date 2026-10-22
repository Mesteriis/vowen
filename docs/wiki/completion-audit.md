# Приёмка покрытия справочников — 22.10.2026

Объект: все текущие 438 fixture-записей всех 17 справочников, их русские
описания и отдельные опубликованные Wiki-материалы. Данные пользовательских
дневников/анкет не импортируются. Новые пользовательские справочные записи
не получают автоматически написанную полную статью: для них есть редактор.

## Сверка требований

| Требование | Подтверждение | Результат |
|---|---|---|
| Все 17 видов и все записи | `coverage-current.json`: 438 записей, 438 статей, gaps пуст; проверяются все строки CATALOGUES | Пройдено |
| Русские определения в самих справочниках | v21 / description_refresh; точное сравнение всех полей 438 записей через API | Пройдено |
| Соответствие записи и статьи | reader API: 438 точных тел/аннотаций/источников; reference-links: 438 соответствий и открытых целей | Пройдено |
| Релевантные пояснения без искусственного объёма | отдельные тексты catalogues-v1, practice/device/pose-reviews-v1; тематические проверки фикстур | Пройдено |
| Источники, издатель, область, дата | source-review.json четырёх корпусов: 56/30/51/26 записей источников; тесты сверяют URL статей с реестрами | Пройдено |
| Отделение редакционных вариантов от исторических/медицинских заявлений | source-review method/scope/excluded и явные ограничения в статьях; словари подтверждают термины, документы производителей — конкретные модели | Пройдено |
| Осмысленные связи между статьями | 1598 переходов / 445 разных публичных целей; реальные typed reference targets, тематические сравнения, категории и обзоры | Пройдено |
| Публичность и существование целей | все цели открыты через API обычного участника; archive/draft/401/403 и неверный kind покрыты регрессиями | Пройдено |
| Явный безопасный импорт | admin + транзакции + точные fingerprints; повтор, история, ручные правки, архив, неверные связи и гонки проверены на PostgreSQL | Пройдено |
| Web: прямые ссылки, якоря и защита URL | browser desktop/mobile; фокус статьи, внутренний переход, возврат; Web regression tests | Пройдено |
| Android: внутренние ссылки и переход из справочника | JUnit parser/navigation + Compose Workspace→settings→reference→article→Markdown link; phone/tablet API36 | Пройдено |

## Проверки конечного среза

- `uv run --project backend python scripts/check_wiki_coverage.py`: exit0,
  structural_complete=true. Сам по себе этот аудит не доказывает качество источников;
  дополнен реестрами/тематическими проверками и live API-аудитом.
- `pytest backend/tests/unit/test_wiki*.py backend/tests/integration/test_wiki*.py
  backend/tests/contract/test_wiki.py backend/tests/unit/test_reference_descriptions.py
  backend/tests/integration/test_reference_description_refresh.py -q`: **104 passed,
  130.37 s**, отдельная PostgreSQL `vowen_profile_test`; preview БД не очищается.
- Web Vitest: **59 passed / 15 files**. Web typecheck и scoped lint прошли в предыдущем
  срезе; продуктовый Web-код после них не менялся.
- Android `:app:testDebugUnitTest :app:assembleDebug --write-locks`: **BUILD SUCCESSFUL**,
  **30 unit tests**, 0 failures/errors. Первоначальный missing dependency lock был
  исправлен; CommonMark0.24.0 и разрешённые конфигурации зафиксированы.
- `:app:connectedDebugAndroidTest` с class `org.vowen.app.WikiReferenceScreenTest`:
  **2 passed** при 390×844 и **2 passed** при 1200×1600 / density160, Android API36.
  Проверены обе ветки навигации Workspace и внутренний Markdown-переход.
  Сетевая доставка подменена тестовым interceptor, UI/state/DTO настоящие.
- Скриншоты обоих размеров просмотрены; это функциональные Compose-тесты под
  MaterialTheme, не оценка соответствия фирменному оформлению.
- Исходный размер QA-эмулятора восстановлен, запущенный эмулятор остановлен.

## Доказательства

Локальные ignored-артефакты в `artifacts/deployment/wiki-20261022/`:

- `all-reference-wiki-acceptance.json`: точные 438 материалов и все 1598 ссылок;
- `reference-wiki-navigation-acceptance.json`: все 438 mapping-ответов и Web;
- `android-wiki-acceptance.json`, `android-wiki-{phone,tablet}-tests.xml` и PNG;
- `reference-descriptions-acceptance.json`, `{practice,device,pose}-reviews-*-acceptance.json`
  и `pose-reviews-acceptance.json`: сохранность, обновление и повтор импорта.

Цель покрытия текущих справочников выполнена в репозитории и локальной preview.
Это не удалённый deploy, не полный CI всего продукта, не проверка живого Telegram,
не release Android и не испытание на физическом устройстве. Коммитов/push нет.
