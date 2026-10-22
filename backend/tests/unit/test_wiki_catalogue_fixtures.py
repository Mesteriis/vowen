from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.wiki.catalogue_articles import catalogue_page_uid, load_catalogue_articles


def test_catalogue_corpus_is_complete_and_has_resolvable_nonself_links():
    articles = load_catalogue_articles()
    kinds = {
        "interaction-formats", "venues", "relationship-types",
        "participant-compositions", "timezones", "practice-categories", "pose-categories",
        "biological-sex", "genders", "role-scenarios", "materials", "body-parts",
        "health-conditions", "allergens",
    }
    assert len(articles) == 177
    assert {a.reference.kind for a in articles} == kinds
    for kind in kinds:
        assert {a.reference.uid for a in articles if a.reference.kind == kind} == {
            r["uid"] for r in fixture_rows(kind)
        }
    for article in articles:
        assert len(article.body.split()) >= 60
        assert article.sources and article.related_pages
        pointers = {(p.kind, p.uid) for p in article.related_references}
        assert len(pointers) == len(article.related_references)
        assert (article.reference.kind, article.reference.uid) not in pointers
        for pointer in article.related_references:
            assert pointer.uid in {r["uid"] for r in fixture_rows(pointer.kind)}
        assert any(s.url in article.body for s in article.sources)
        assert catalogue_page_uid(article.reference.kind, article.reference.uid)


def test_catalogue_sources_have_scopes_and_all_catalogues_have_titles():
    import json
    from importlib.resources import files

    from vowen.modules.references.fixtures import CATALOGUES
    from vowen.modules.wiki.catalogue_articles import CATALOGUE_TITLES

    assert CATALOGUE_TITLES.keys() == CATALOGUES.keys()
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "catalogues-v1")
    review = json.loads(root.joinpath("source-review.json").read_text("utf-8"))
    assert review["checked_on"] == "2026-10-22"
    sources = {s["url"]: s for s in review["sources"]}
    for article in load_catalogue_articles():
        for source in article.sources:
            assert source.url in sources
            assert sources[source.url]["scope"] and sources[source.url]["publisher"]


def test_category_indexes_link_exactly_their_own_members():
    articles = load_catalogue_articles()
    for parent, child in [("practice-categories", "practices"), ("pose-categories", "poses")]:
        for article in articles:
            if article.reference.kind != parent:
                continue
            assert {(p.kind, p.uid) for p in article.related_references} == {
                (child, row["uid"]) for row in fixture_rows(child)
                if row["category_uid"] == article.reference.uid
            }


def test_health_articles_use_specific_sources_and_separate_conditions_from_allergens():
    health = [a for a in load_catalogue_articles()
              if a.reference.kind in {"health-conditions", "allergens"}]
    assert len(health) == 39
    assert len({source.url for a in health for source in a.sources}) == 37
    for article in health:
        assert "не устанавливает диагноз" in article.body
        assert "не назначает лечение" in article.body
        assert any(p.kind == "health-conditions" for p in article.related_references)
        if article.reference.kind == "allergens":
            assert "Аллерген в справочнике и подтверждённая аллергия" in article.body
