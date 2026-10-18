# Заболевания, состояния и аллергены

Дата сверки терминов: 2026-10-18. Два самостоятельных справочника без данных о здоровье конкретных участников: `reference_health_conditions` (23 записи), `reference_allergens` (16 записей). Стандартные поля uid/name/description/icon/url/extra; icon/url пока null по требованию владельца. extra содержит только code и aliases. Никаких степеней тяжести, диагнозов пользователя, допустимых практик, медицинских назначений или результатов анализов не создаётся.

## Предметный охват

Заболевания: нарушения свёртывания крови; дыхательные, сердечно-сосудистые, неврологические, обменные, костно-соединительнотканные и кожные заболевания; ПТСР/паническое расстройство; ВИЧ, гепатиты B/C, генитальный герпес, ВПЧ, сифилис, гонорея, хламидийная инфекция. Отбор для тематики продукта — редакционное решение, а не медицинская шкала противопоказаний. Наличие записи в справочнике не означает, что заболевание есть у участника, передаётся конкретным способом или запрещает конкретную практику. Состояния здоровья не связываются автоматически с практиками, девайсами или материалами.

Аллергены: белки натурального латекса, никель, кобальт, хроматы, тиурамы, карбаматы резины, MBT, отдушки, изотиазолиноны MI/MCI, формальдегид, канифоль, акрилаты/метакрилаты, эпоксидные смолы, ланолин, каин-смесь, хлоргексидин. Актуальный контекст продукта — материалы аксессуаров, контакт кожи с изделиями, наружные средства и средства очистки. Каталог не утверждает, что конкретное изделие содержит перечисленное вещество. Белки латекса и добавки резины разделены; раздражение кожи не считается автоматически аллергией. Отдельных записей «здоров», «без аллергии» или «безопасно» нет.

## Медицинские источники

Использованы нейтральные названия и краткие пересказы, без рекомендаций по лечению или проведению BDSM-практик:

- [NHS: haemophilia](https://www.nhs.uk/conditions/haemophilia/) и [von Willebrand disease](https://www.nhs.uk/conditions/von-willebrand-disease/).
- [NHS: asthma](https://www.nhs.uk/conditions/asthma/), [epilepsy](https://www.nhs.uk/conditions/epilepsy/), [diabetes](https://www.nhs.uk/conditions/diabetes/), [peripheral neuropathy](https://www.nhs.uk/conditions/peripheral-neuropathy/).
- [NHS: osteoporosis](https://www.nhs.uk/conditions/osteoporosis/causes/) и [Ehlers–Danlos syndromes](https://www.nhs.uk/conditions/ehlers-danlos-syndromes/).
- [NHS: high blood pressure](https://www.nhs.uk/conditions/high-blood-pressure/) и [arrhythmia](https://www.nhs.uk/conditions/arrhythmia/).
- [NHS: atopic eczema](https://www.nhs.uk/conditions/atopic-eczema/), [psoriasis](https://www.nhs.uk/conditions/psoriasis/), [contact dermatitis](https://111.wales.nhs.uk/Encyclopaedia/c/article/contactdermatitis).
- [NHS: PTSD](https://www.nhs.uk/mental-health/conditions/ptsd-post-traumatic-stress-disorder/) и [panic disorder](https://www.nhs.uk/mental-health/conditions/panic-disorder/).
- [NHS: STIs](https://www.nhs.uk/conditions/sexually-transmitted-infections-stis/), [HIV](https://www.nhs.uk/conditions/hiv-and-aids/), [hepatitis B](https://www.nhs.uk/conditions/hepatitis-b/), [hepatitis C](https://www.nhs.uk/conditions/hepatitis-c/).
- [University Hospitals Sussex: перечень контактных аллергенов и отличие аллергии от раздражения](https://www.uhsussex.nhs.uk/resources/patch-testing/).
- [Cambridge University Hospitals: белки латекса и добавки резины](https://www.cuh.nhs.uk/patient-information/information-for-patients-with-latex-allergy/).
- [European Academy of Dermatology and Venereology: контактные аллергены](https://eadv.org/wp-content/uploads/2023/04/EADV-Contact-Derm_1-Contact-Dermatitis.pdf).
- [East London NHS: chlorhexidine allergy](https://www.elft.nhs.uk/sites/default/files/2022-03/Clinical%20Alert%20no%209%20-%20Chlorhexidine.pdf).

## Реализация и проверки

Активные фикстуры v9, стабильные UUIDv5, отдельные неизменяемые снимки Alembic 0037. Миграция добавляет две таблицы, не изменяя существующие справочники или персональные данные. Seed добавляет недостающее и не перезаписывает правки. Откат удаляет новые таблицы; изменённые записи перед ним нужно сохранить отдельно.

GET /references/health-conditions и /references/allergens требует аутентификации, POST в общие справочники не добавлен. Web и Android исходники показывают оба набора с поиском по именам/aliases. Клиентские типы и OpenAPI обновлены. Приватные профили/анкеты в этой задаче не меняются.

Проверено 16 backend unit/PostgreSQL/API/contract тестов, 6 Vitest поиска, Web typecheck, scoped mypy/ruff; реальный 0037→0036→0037 на vowen_test. Тесты проверяют схему, 401/405, число/уникальность/пустые URL, сохранность пользовательских правок, отсутствие полей медицинского допуска/персональных диагнозов. Браузер: 23/16 записей, поиск ПТСР/латекс, телефон 389 CSS px без overflow. Снимки health-conditions-search.png, allergen-catalogue.png, allergens-phone.png.

Design-база обновлена до 0037 после закрытой резервной копии; основная vowen и удалённые базы не менялись. Без сборок и коммитов. Android source-only, без проверки на устройстве.
