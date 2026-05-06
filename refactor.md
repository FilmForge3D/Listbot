# Refactor Plan

A function-by-function pass over the bot codebase. Walk through this at your own pace; each step is a discrete unit of work with its own commit.

**Out of scope:** `migration/` (moving to private branch — leave messy).

---

## Workflow per function

1. **Audit** — read the function; note issues.
2. **Verdict** — pick one: `keep` / `cleanup` / `decompose` / `rewrite`.
3. **Style pass** — apply CLAUDE.md style rules (types, comments, docstrings, imports).
4. **Decompose** if needed — extract helpers (only with prior approval if >30 net new lines or new file).
5. **Summary** — one line written into this file under the function's row.
6. **Commit** — single function per commit, message format: `refactor(<file>): <function> — <verdict>`.

CLAUDE.md rules to honor: max 50 LOC per edit, 100 LOC per function, one function per commit, ask before new files.

---

## Phase -1 — Review the style guide itself

Before touching code, audit `CLAUDE.md` for inconsistencies, gaps, or rules that include poor design standards.

- [ ] Read CLAUDE.md end-to-end against common best practices for python code
- [ ] Propose changes to CLAUDE.md in order to make the code 1. human-readable 2. AI-readable

Define:

- [ ] Naming conventions
- [ ] Comment conventions
- [ ] Structural conventions
- [ ] Other

---

## Phase 0 — Review the code against the style guide

Before making changes to the code, audit the current code base against `CLAUDE.md`.

- [ ] Read CLAUDE.md end-to-end against current code state
- [ ] Note rules that are violated everywhere (signal: rule is wrong or code is wrong)
- [ ] Note rules missing for patterns that recur (e.g., `with get_connection() as conn:` boilerplate, `_get_list_id_or_none` helper candidate)
- [ ] Decide: amend CLAUDE.md, or carry rules into the refactor as-is
- [ ] Commit: `docs(claude.md): refresh style guide ahead of refactor pass`

---

## Phase 1 — Leaf modules (trivial)

| File | Function | Verdict | Notes |
|---|---|---|---|
| [config.py:11](config.py#L11) | `load_token` | keep | Clean; no changes needed |
| [text.py:4](text.py#L4) | `first_name` | keep | Clean; no changes needed |
| [i18n/strings.py:10](i18n/strings.py#L10) | `load_locale` | cleanup | Added docstring, replaced print/sys with logger.warning, dropped sys import |
| [i18n/strings.py:21](i18n/strings.py#L21) | `t` | cleanup | Added docstring |

- [x] config.load_token
- [x] text.first_name
- [x] i18n.strings.load_locale
- [x] i18n.strings.t

---

## Phase 2 — Database layer

Heavy boilerplate repetition: `with get_connection() as conn: row = conn.execute("SELECT id FROM lists WHERE chat_id = ? AND list_name = ?", ...).fetchone()`. Watch for a `_resolve_list_id(conn, chat_id, name)` helper opportunity — but **propose before extracting**, since it spans modules.

| File | Function | Verdict | Notes |
|---|---|---|---|
| [db/connection.py:8](db/connection.py#L8) | `get_connection` | keep | Clean; no changes needed |
| [db/schema.py:8](db/schema.py#L8) | `init_db` | cleanup | Narrowed `except Exception` → `OperationalError`; moved `DB_PATH` import to module level; removed redundant `conn.commit()` |
| [db/users.py:4](db/users.py#L4) | `upsert_user` | cleanup | Removed redundant `conn.commit()` (context manager auto-commits) |
| [db/users.py:14](db/users.py#L14) | `lookup_name` | keep | Clean; no changes needed |
| [db/settings.py:4](db/settings.py#L4) | `get_default_list` | keep | Clean; no changes needed |
| [db/settings.py:14](db/settings.py#L14) | `set_default_list` | cleanup | Removed redundant `conn.commit()` |
| [db/lists.py:6](db/lists.py#L6) | `_get_or_create_list` | keep | Clean; leading underscore correct — takes `conn`, not public API |
| [db/lists.py:22](db/lists.py#L22) | `get_list_names` | keep | Clean; no changes needed |
| [db/lists.py:32](db/lists.py#L32) | `rename_list` | cleanup | Fixed SQL spacing (`chat_id=?` → `chat_id = ?`); removed redundant `conn.commit()` |
| [db/lists.py:49](db/lists.py#L49) | `delete_list` | cleanup | Removed redundant `conn.commit()` |
| [db/shares.py:6](db/shares.py#L6) | `add_list_share` | cleanup | Removed redundant `conn.commit()` |
| [db/shares.py:20](db/shares.py#L20) | `remove_list_share` | cleanup | Removed redundant `conn.commit()` |
| [db/shares.py:31](db/shares.py#L31) | `get_list_shares` | keep | Clean; no changes needed |
| [db/shares.py:41](db/shares.py#L41) | `get_shared_lists` | keep | Clean; no changes needed |
| [db/shares.py:53](db/shares.py#L53) | `transfer_list_ownership` | cleanup | Removed redundant `conn.commit()` |
| [db/shares.py:76](db/shares.py#L76) | `resolve_list_owner` | keep | Clean; no changes needed |
| [db/prompts.py:8](db/prompts.py#L8) | `add_prompt` | cleanup | Removed redundant `conn.commit()` |
| [db/prompts.py:25](db/prompts.py#L25) | `get_prompts` | keep | Clean; no changes needed |
| [db/prompts.py:40](db/prompts.py#L40) | `draw_random_prompt` | cleanup | Removed redundant `conn.commit()` |
| [db/prompts.py:71](db/prompts.py#L71) | `get_recently_drawn_prompts` | keep | Clean; no changes needed |
| [db/prompts.py:91](db/prompts.py#L91) | `get_stats` | keep | Clean; no changes needed |
| [db/prompts.py:127](db/prompts.py#L127) | `edit_prompt` | cleanup | Removed redundant `conn.commit()` |
| [db/prompts.py:145](db/prompts.py#L145) | `remove_prompt` | cleanup | Removed redundant `conn.commit()` |

- [x] db.connection.get_connection
- [x] db.schema.init_db
- [x] db.users.upsert_user
- [x] db.users.lookup_name
- [x] db.settings.get_default_list
- [x] db.settings.set_default_list
- [x] db.lists._get_or_create_list
- [x] db.lists.get_list_names
- [x] db.lists.rename_list
- [x] db.lists.delete_list
- [x] db.shares.add_list_share
- [x] db.shares.remove_list_share
- [x] db.shares.get_list_shares
- [x] db.shares.get_shared_lists
- [x] db.shares.transfer_list_ownership
- [x] db.shares.resolve_list_owner
- [x] db.prompts.add_prompt
- [x] db.prompts.get_prompts
- [x] db.prompts.draw_random_prompt
- [x] db.prompts.get_recently_drawn_prompts
- [x] db.prompts.get_stats
- [x] db.prompts.edit_prompt
- [x] db.prompts.remove_prompt

## Phase 2.5 — db.get_list_id

| File | Function | Verdict | Notes |
|---|---|---|---|
| [db/lists.py:22](db/lists.py#L22) | `get_list_id` | new | Added public lookup-only variant; removes raw SQL from `render_share_panel` |

- [x] db.lists.get_list_id

---

## Phase 3 — Messaging & actions

| File | Function | Verdict | Notes |
|---|---|---|---|
| [messaging.py:7](messaging.py#L7) | `notify` | cleanup | Added `Bot` type hint to `bot` parameter |
| [messaging.py:12](messaging.py#L12) | `force_reply_msg` | cleanup | Added `User` type hint to `user` parameter |
| [messaging.py:26](messaging.py#L26) | `send_force_reply` | cleanup | Added `User` type hint; tightened `state` to `dict[str, str \| int]` |
| [messaging.py:56](messaging.py#L56) | `cleanup_reply_messages` | cleanup | Added `Bot` type hint to `bot` parameter |
| [actions.py:7](actions.py#L7) | `do_draw` | cleanup | Added `Bot` type hint to `bot` parameter |

- [x] messaging.notify
- [x] messaging.force_reply_msg
- [x] messaging.send_force_reply
- [x] messaging.cleanup_reply_messages
- [x] actions.do_draw

---

## Phase 4 — UI rendering

| File | Function | Verdict | Notes |
|---|---|---|---|
| [ui/views.py:7](ui/views.py#L7) | `render_lists_view` | cleanup | Extracted `_chunk_buttons` helper; replaced duplicated chunking loops with item-list + helper |
| [ui/views.py:27](ui/views.py#L27) | `render_list_view` | cleanup | Simplified text composition: `header + (f"\n\n{note}" if note else "")` |
| [ui/views.py:71](ui/views.py#L71) | `render_share_panel` | cleanup | Added comment flagging raw SQL as leakage pending `db.get_list_id()` |

- [x] ui.views.render_lists_view
- [x] ui.views.render_list_view
- [x] ui.views.render_share_panel

---

## Phase 5 — Handlers (the big work)

### 5a — Commands (small, easy)

| File | Function | Verdict | Notes |
|---|---|---|---|
| [handlers/commands.py:17](handlers/commands.py#L17) | `draw_command` | keep | Clean; no changes needed |
| [handlers/commands.py:34](handlers/commands.py#L34) | `add_command` | cleanup | Bound `user = from_user`; guarded `.id` accesses behind `if user` check |
| [handlers/commands.py:60](handlers/commands.py#L60) | `show_panel` | keep | Clean; no changes needed |
| [handlers/commands.py:74](handlers/commands.py#L74) | `help_command` | keep | Clean; no changes needed |
| [handlers/commands.py:86](handlers/commands.py#L86) | `cancel_command` | cleanup | Replaced `except Exception: pass` with `except TelegramError` + `logger.warning`; added module logger |

- [x] handlers.commands.draw_command
- [x] handlers.commands.add_command
- [x] handlers.commands.show_panel
- [x] handlers.commands.help_command
- [x] handlers.commands.cancel_command

### 5b — `reply_handler` ⚠️ DECOMPOSE

[handlers/replies.py:11](handlers/replies.py#L11) — ~186 LOC, well over the 100-LOC ceiling.

- [ ] **Plan first** — read top-to-bottom, identify pending-action branches (new item / edit text / list rename / share target / etc.)
- [ ] **Propose** dispatch shape: lookup table of `pending_action → handler_fn`, or per-branch `_handle_<action>` helpers
- [ ] **Get approval** before writing
- [ ] Extract helpers one at a time, each its own commit
- [ ] Final pass: trim `reply_handler` to a thin dispatcher

### 5c — `button_handler` ⚠️ DECOMPOSE

[handlers/callbacks.py:13](handlers/callbacks.py#L13) — ~238 LOC, the worst offender.

- [ ] **Plan first** — enumerate every callback-data prefix the function dispatches on
- [ ] **Propose** structure: route table mapping prefix → coroutine, or `_handle_<action>` helpers grouped by domain (list ops / prompt ops / share ops)
- [ ] **Get approval** before writing
- [ ] Extract helpers one at a time, each its own commit
- [ ] Final pass: `button_handler` becomes routing only

### 5d — Registration

| File | Function | Verdict | Notes |
|---|---|---|---|
| [handlers/__init__.py:20](handlers/__init__.py#L20) | `register_handlers` | | |

- [ ] handlers.__init__.register_handlers

---

## Phase 6 — Entry point

| File | Function | Verdict | Notes |
|---|---|---|---|
| [main.py:20](main.py#L20) | `main` | | |

- [ ] main.main

---

## Phase 7 — Tests

| File | Function | Verdict | Notes |
|---|---|---|---|
| [tests/test_db_smoke.py:8](tests/test_db_smoke.py#L8) | `tmp_db` | | fixture |
| [tests/test_db_smoke.py:14](tests/test_db_smoke.py#L14) | `test_prompt_round_trip` | | expand coverage? separate decision |

- [ ] tests.test_db_smoke.tmp_db
- [ ] tests.test_db_smoke.test_prompt_round_trip

---

## Phase 8 — Final sweep

- [ ] Run ruff / mypy across the project
- [ ] Run the test suite
- [ ] Smoke-test the bot end-to-end (start, /list, draw, add, edit, remove, share)
- [ ] Update CLAUDE.md if any new conventions emerged during the pass
- [ ] Delete this `refactor.md` (or archive it) once Phase 8 is green

---

## Counters

- **Total functions in scope:** 44
- **Phases:** 8
- **Big-ticket items:** `reply_handler`, `button_handler`, possibly `get_stats`
- **Cross-cutting candidates** (propose before doing): shared `_resolve_list_id` helper for the db layer
