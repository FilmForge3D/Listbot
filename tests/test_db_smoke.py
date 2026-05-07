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


def test_users() -> None:
    """upsert_user stores and updates names; lookup_name returns None for unknowns."""
    db.upsert_user(42, "Alice")
    assert db.lookup_name(42) == "Alice"

    db.upsert_user(42, "Alicia")
    assert db.lookup_name(42) == "Alicia"

    assert db.lookup_name(99) is None


def test_settings() -> None:
    """set_default_list persists the default; get_default_list returns None before it is set."""
    chat_id = 2
    db.add_prompt(chat_id, "main", "x")
    assert db.get_default_list(chat_id) is None

    db.set_default_list(chat_id, "main")
    assert db.get_default_list(chat_id) == "main"

    db.add_prompt(chat_id, "other", "y")
    db.set_default_list(chat_id, "other")
    assert db.get_default_list(chat_id) == "other"


def test_list_rename_and_id() -> None:
    """rename_list updates the name and rejects conflicts; get_list_id returns None for missing lists."""
    chat_id = 3
    db.add_prompt(chat_id, "alpha", "x")
    list_id = db.get_list_id(chat_id, "alpha")
    assert isinstance(list_id, int)
    assert db.get_list_id(chat_id, "missing") is None

    assert db.rename_list(chat_id, "alpha", "beta") is True
    assert db.get_list_id(chat_id, "alpha") is None
    assert db.get_list_id(chat_id, "beta") == list_id

    db.add_prompt(chat_id, "gamma", "y")
    assert db.rename_list(chat_id, "beta", "gamma") is False


def test_prompt_extras() -> None:
    """edit_prompt updates text; get_stats and get_recently_drawn_prompts reflect draw state."""
    chat_id = 4
    db.add_prompt(chat_id, "extras", "original")

    assert db.edit_prompt(chat_id, "extras", 1, "updated") is True
    assert db.get_prompts(chat_id, "extras")[0]["text"] == "updated"

    stats = db.get_stats(chat_id, "extras")
    assert stats is not None
    assert stats["total"] == 1
    assert stats["never_drawn"] == 1

    db.draw_random_prompt(chat_id, "extras")
    assert len(db.get_recently_drawn_prompts(chat_id, "extras")) == 1


def test_shares() -> None:
    """Full share lifecycle: add, query, transfer ownership, remove."""
    owner, guest = 10, 20
    db.add_prompt(owner, "shared", "x")
    list_id = db.get_list_id(owner, "shared")
    assert list_id is not None

    assert db.add_list_share(list_id, guest) is True
    assert db.add_list_share(list_id, guest) is False  # duplicate rejected
    assert guest in db.get_list_shares(list_id)
    assert any(r["list_name"] == "shared" for r in db.get_shared_lists(guest))

    assert db.resolve_list_owner(owner, "shared") == owner
    assert db.resolve_list_owner(guest, "shared") == owner
    assert db.resolve_list_owner(99, "shared") is None

    # after transfer: guest owns, old owner becomes a guest
    assert db.transfer_list_ownership(list_id, guest) is True
    assert db.get_list_id(guest, "shared") == list_id
    assert owner in db.get_list_shares(list_id)

    assert db.remove_list_share(list_id, owner) is True
    assert db.remove_list_share(list_id, owner) is False  # already removed
