import pytest

import db
import db.connection


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH to a temp file and initialise the schema."""
    monkeypatch.setattr(db.connection, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_prompt_round_trip():
    """Full happy-path flow: create list → add → get → draw → remove → delete."""
    chat_id = 1
    list_name = "smoke"

    pos = db.add_prompt(chat_id, list_name, "Test prompt")
    assert pos == 1

    names = db.get_list_names(chat_id)
    assert list_name in names

    prompts = db.get_prompts(chat_id, list_name)
    assert len(prompts) == 1
    assert prompts[0]["text"] == "Test prompt"

    drawn = db.draw_random_prompt(chat_id, list_name)
    assert drawn is not None
    assert drawn["text"] == "Test prompt"

    removed = db.remove_prompt(chat_id, list_name, 1)
    assert removed is not None
    assert removed["text"] == "Test prompt"

    assert db.get_prompts(chat_id, list_name) == []

    deleted = db.delete_list(chat_id, list_name)
    assert deleted is True
    assert list_name not in db.get_list_names(chat_id)
