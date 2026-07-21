from app.cloud_drafts import CloudDraftWriter, DraftInbox


def test_cloud_draft_writer_reads_raw_responses_message():
    writer = CloudDraftWriter.__new__(CloudDraftWriter)
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"drafts":[{"text":"A useful post","title":"Release"}]}',
                    }
                ],
            }
        ]
    }

    assert writer._parse(payload) == [{"text": "A useful post", "title": "Release"}]


def test_draft_inbox_keeps_recent_batches(tmp_path):
    inbox = DraftInbox(tmp_path / "draft-inbox.json")

    saved = inbox.save_batch([{"text": "First draft"}])

    assert saved["batches"][0]["drafts"] == [{"text": "First draft"}]
