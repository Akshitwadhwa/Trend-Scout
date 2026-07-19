from app.workflow import Workflow


def item(index: int, source_type: str = "web") -> dict:
    return {
        "id": str(index),
        "url": f"https://example.com/{index}",
        "author_username": "https://feed.example.com/rss",
        "created_at": f"2026-07-19T0{index}:00:00+00:00",
        "source_type": source_type,
    }


def test_web_selection_keeps_a_small_diverse_batch_from_one_feed():
    workflow = Workflow.__new__(Workflow)

    selected = workflow._select_items([item(index) for index in range(1, 7)])

    assert len(selected) == 4


def test_x_selection_still_limits_one_post_per_author():
    workflow = Workflow.__new__(Workflow)

    selected = workflow._select_items([item(1, "x"), item(2, "x")])

    assert len(selected) == 1
