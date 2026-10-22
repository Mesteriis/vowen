import re

from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.wiki.pose_articles import load_pose_articles


def test_every_pose_has_a_distinct_article_preserving_the_known_description():
    articles = load_pose_articles()
    references = {r["extra"]["code"]: r for r in fixture_rows("poses")}
    assert len(articles) == 106
    assert {a.code for a in articles} == references.keys()
    assert len({a.body for a in articles}) == 106
    for article in articles:
        reference = references[article.code]
        assert article.title == reference["name"]
        assert reference["description"] in article.body
        assert len(article.body.split()) >= 80
        assert len(re.findall(r"^## ", article.body, re.M)) == 3
        assert "Краткая справочная карточка" not in article.body
        assert 0 < len(article.summary) <= 600
    unknown = next(a for a in articles if a.code == "slave-side-ball")
    assert "назначение не подтверждены" in unknown.body
    assert "традиц" in unknown.body.lower()
