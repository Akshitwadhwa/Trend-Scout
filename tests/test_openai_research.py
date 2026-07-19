from app.openai_research import OpenAIWebResearcher


def test_background_response_without_an_id_is_returned_directly():
    researcher = OpenAIWebResearcher.__new__(OpenAIWebResearcher)
    researcher.timeout = 30

    payload = {"status": "completed", "output_text": '{"items": []}'}

    assert researcher._wait_for_completion(payload) == payload
