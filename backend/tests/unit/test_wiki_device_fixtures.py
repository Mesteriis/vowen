import re

from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.wiki.device_articles import load_device_articles


def test_all_devices_have_distinct_russian_articles():
    articles = load_device_articles()
    expected = {row["extra"]["code"]: row["name"] for row in fixture_rows("devices")}
    assert len(articles) == len(expected) == 62
    assert {article.code for article in articles} == expected.keys()
    assert len({article.body for article in articles}) == 62
    for article in articles:
        assert article.title == expected[article.code]
        assert len(article.body.split()) >= 100
        assert len(re.findall(r"^## ", article.body, re.M)) >= 3
        assert 50 < len(article.summary) <= 600
        assert "Краткая справочная карточка" not in article.body
