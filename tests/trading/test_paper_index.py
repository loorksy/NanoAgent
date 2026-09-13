from nanobot.trading.paper import paper_actions_index, record_paper_action


def test_paper_actions_index_tracks_latest_action(tmp_path, monkeypatch):
    ledger = tmp_path / "paper_ledger.jsonl"
    monkeypatch.setattr("nanobot.trading.paper._LEDGER", ledger)
    record_paper_action("rec-1", "approve")
    record_paper_action("rec-2", "reject")
    index = paper_actions_index()
    assert index["rec-1"] == "approve"
    assert index["rec-2"] == "reject"
