from app.openai_research import OpenAIWebResearcher


def test_background_response_without_an_id_is_returned_directly():
    researcher = OpenAIWebResearcher.__new__(OpenAIWebResearcher)
    researcher.timeout = 30

    payload = {"status": "completed", "output_text": '{"items": []}'}

    assert researcher._wait_for_completion(payload) == payload


def test_research_prompt_targets_a_small_distinct_release_set(monkeypatch):
    settings = type(
        "Settings",
        (),
        {
            "enable_openai_research": True,
            "openai_api_key": "test-key",
            "openai_research_model": "gpt-5",
            "openai_research_timeout_seconds": 30,
        },
    )()
    researcher = OpenAIWebResearcher(settings)
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "completed", "output_text": '{"items": []}'}

    def fake_post(*_args, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr("app.openai_research.requests.post", fake_post)

    assert researcher.research("AI releases") == []
    assert captured["reasoning"] == {"effort": "low"}
    assert "at most four distinct" in captured["input"]


def test_reads_json_from_raw_responses_api_output_items():
    researcher = OpenAIWebResearcher.__new__(OpenAIWebResearcher)
    payload = {
        "output": [
            {"type": "web_search_call", "id": "ws_123"},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"items": []}'},
                ],
            },
        ]
    }

    assert researcher._items_from_response(payload) == []
