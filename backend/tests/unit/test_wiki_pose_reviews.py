import json
import re
from importlib.resources import files

from vowen.modules.references.fixtures import CATALOGUES, fixture_rows
from vowen.modules.wiki.catalogue_articles import catalogue_page_uid
from vowen.modules.wiki.editorial import editorial_uid, load_editorial
from vowen.modules.wiki.pose_articles import load_pose_articles
from vowen.modules.wiki.pose_review import load_pose_reviews, load_reviewed_pose_articles


def test_all_pose_reviews_keep_originals_and_link_existing_typed_references():
    originals = {a.code: a for a in load_pose_articles()}
    reviews = {r.code: r for r in load_pose_reviews()}
    enriched = {a.code: a for a in load_reviewed_pose_articles()}
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "pose-reviews-v1")
    registry = json.loads(root.joinpath("source-review.json").read_text("utf-8"))
    sources = {s["url"]: s for s in registry["sources"]}
    targets = {str(catalogue_page_uid(kind, row["uid"])) for kind in CATALOGUES
               for row in fixture_rows(kind)} | {
        str(editorial_uid("article:" + a.key)) for a in load_editorial().articles
    }
    assert originals.keys() == reviews.keys() == enriched.keys()
    assert len(reviews) == 106 and len(sources) == 26
    total_links = 0
    for code, article in enriched.items():
        original, review = originals[code], reviews[code]
        assert article.body.startswith(original.body.rstrip())
        assert article.summary == original.summary and article.sources == review.sources
        assert len(article.body) < 100000 and review.scope.strip()
        assert len(review.related_pose_codes) == 2
        assert len({(p.kind, p.uid) for p in review.related_references}) == len(
            review.related_references,
        )
        assert any(p.kind == "pose-categories" for p in review.related_references)
        links = set(re.findall(r"#wiki\?page=([0-9a-f-]{36})", article.body))
        assert len(links) == len(review.related_pose_codes) + len(review.related_pages) + len(
            review.related_references,
        )
        assert links <= targets
        total_links += len(links)
        for source in article.sources:
            registered = sources[source.url]
            assert registered["publisher"] and registered["scope"]
            assert registered["checked_on"] == "2026-10-22"
            assert source.url in article.body
    assert total_links == 436


def test_editorial_variants_are_not_presented_as_ancient_or_universal_names():
    reviews = {r.code: r for r in load_pose_reviews()}
    assert "редакцион" in reviews["modern-side-t-shape"].scope
    assert "не норматив" in reviews["slave-kneeling-deep-backbend"].scope
    assert "литературная" in reviews["nadu"].scope
    assert "Codex" in reviews["tower"].scope
    assert reviews["tower"].sources[0].url == reviews["nadu"].sources[0].url
