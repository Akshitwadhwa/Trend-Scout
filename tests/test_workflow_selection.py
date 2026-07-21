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


def test_cloud_research_is_not_pushed_out_by_newer_rss_timestamps():
    workflow = Workflow.__new__(Workflow)
    cloud = item(1, "openai_web_research")
    cloud["author_username"] = "openai-research"
    cloud["created_at"] = "2026-07-21"
    rss_items = [item(index) for index in range(2, 14)]

    selected = workflow._select_items([cloud, *rss_items])

    assert selected[0]["source_type"] == "openai_web_research"
