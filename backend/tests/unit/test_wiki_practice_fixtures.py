import re

from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.wiki.practice_articles import load_practice_articles


def test_practice_articles_are_individual_russian_texts_with_known_references():
    articles = load_practice_articles()
    known = {row["extra"]["code"]: row["name"] for row in fixture_rows("practices")}
    assert len(articles) == 93
    assert len({a.code for a in articles}) == 93
    assert len({a.body for a in articles}) == 93
    assert {a.code for a in articles} == known.keys()
    for article in articles:
        assert article.title == known[article.code]
        assert len(article.body.split()) >= 110
        assert len(re.findall(r"^## ", article.body, re.M)) >= 3
        assert 50 < len(article.summary) <= 600
        assert "Краткая справочная карточка" not in article.body
