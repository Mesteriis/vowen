import re

from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.wiki.editorial import load_editorial


def test_russian_editorial_corpus_has_complete_articles_and_resolvable_links():
    corpus = load_editorial()
    assert corpus.language == "ru" and corpus.version == 1
    assert len(corpus.articles) == 49
    assert len({article.key for article in corpus.articles}) == 49
    assert len({article.title for article in corpus.articles}) == 49
    for article in corpus.articles:
        assert article.section in corpus.sections
        assert len(article.body.split()) >= 170
        assert len(re.findall(r"^## ", article.body, re.M)) >= 3
        assert re.search(r"[А-Яа-яЁё]", article.summary)
        for kind in ("practice", "device", "pose"):
            available = {row["extra"]["code"] for row in fixture_rows(kind + "s")}
            codes = getattr(article, kind + "_codes")
            assert len(codes) == len(set(codes))
            assert set(codes) <= available


def test_every_editorial_article_has_checked_sources_and_preserved_links():
    import json
    from datetime import date
    from importlib.resources import files

    from vowen.modules.wiki.editorial_refresh import load_editorial_baselines

    corpus = load_editorial()
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "v1")
    review = json.loads(root.joinpath("source-review.json").read_text("utf-8"))
    assert review["version"] == 1
    assert date.fromisoformat(review["checked_on"]) == date(2026, 10, 22)
    records = review["sources"].values()
    assert all(r["publisher"] and r["scope"] and r["access"] == "full_text" for r in records)
    urls = {r["url"] for r in records}
    covered = {key for r in records for key in r["article_keys"]}
    assert covered == {a.key for a in corpus.articles}
    baselines = load_editorial_baselines()
    assert len(baselines) == 33
    assert {b.article.key for b in baselines} < covered
    for article in corpus.articles:
        assert article.sources
        assert any(s.url in urls for s in article.sources)
        assert "## Источники и пояснения" in article.body
        assert any(f"]({s.url})" in article.body for s in article.sources)
        baseline = next((b for b in baselines if b.article.key == article.key), None)
        if baseline is None:
            continue
        assert baseline.article.title == article.title
        assert baseline.article.summary == article.summary
        assert baseline.article.practice_codes == article.practice_codes
        assert baseline.article.pose_codes == article.pose_codes
        assert baseline.article.device_codes == article.device_codes
