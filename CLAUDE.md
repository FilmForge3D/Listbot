# CLAUDE.md

Listbot is a Telegram bot for managing writing prompt lists in group chats.

**Modules**:
- `config.py` — `load_token()`, `DATA_DIR`
- `messaging.py` — `notify`, `send_force_reply`, `cleanup_reply_messages`
- `text.py` — `first_name`
- `actions.py` — `do_draw`
- `db/` — `init_db`, `get_connection`; lists: `get_list_names`, `get_list_id`, `rename_list`, `delete_list`; prompts: `add_prompt`, `remove_prompt`, `edit_prompt`, `get_prompts`, `draw_random_prompt`, `get_recently_drawn_prompts`, `get_stats`; shares: `add_list_share`, `remove_list_share`, `get_list_shares`, `get_shared_lists`, `resolve_list_owner`, `transfer_list_ownership`; users: `upsert_user`, `lookup_name`; settings: `get_default_list`, `set_default_list`
- `i18n/` — `load_locale`, `t`
- `ui/views.py` — `render_lists_view`, `render_list_view`, `render_share_panel`
- `handlers/` — see **Handlers** below

**Stack**: `python-telegram-bot~=22.7`, SQLite, Docker. Token from `BOT_TOKEN` env var → `token.txt` fallback. DB auto-created on first run at `/app/data/listbot.db`.

**Handlers**: `draw_command`, `add_command`, `show_panel`, `cancel_command`, `help_command` in `commands.py`; `button_handler` in `callbacks.py`; `reply_handler` in `replies.py`. All registered via `handlers/__init__.py`.

**Migration tooling** (`migration/`) moves to a private branch — one-time use, not relevant to general users.

## Git Workflow

- **Commit on command**: Commit immediately when the user says "commit" — no confirmation needed.
- **Stage selectively**: Only stage files relevant to the feature being committed.
- **Suggest message**: Suggest a commit message after completing a task.

## AI Collaboration Rules

⚠️ These rules govern Claude's behavior:

- **Single notification per action**: Consolidate all bot output into one message — never send multiple where one suffices.
- **Ask before creating files**: Describe the file and why it's needed before creating it.
- **Large changes (>~30 net lines)**: Get explicit user approval before writing.
- **One new function per session/commit**.
- **Module split**: Ask before splitting a concern into a new module.
- **Edit limit**: Max 50 lines per Edit call; one function per call.
- **Refactoring**: Follow `refactor.md`. Ask to create one if it doesn't exist; a single function may be refactored without a plan.

## Code Style

Python 3.10+ throughout: type hints, f-strings, `async/await`, `X | Y` unions.

**Type hints** — Annotate every signature including `-> None`. Use `X | None`, never `Optional[X]`. Use `TypedDict` over `dict[str, Any]` when the shape is stable. No `TypeAlias`/`Protocol` unless reused in 3+ places.

**Imports** — stdlib → third-party → local, one blank line between groups (ruff manages order). Module-level: `import db` / `import i18n as lang`. Direct: `from messaging import notify`. Within `db/`: `from db.connection import get_connection`.

**Naming** — `snake_case` functions/vars, `CamelCase` classes, `SCREAMING_SNAKE_CASE` constants. Booleans: `is_`/`has_`/`can_` prefix. Throwaway: `_` for anonymous positions, `_name` for named-but-ignored params (e.g. `lambda _s, _t, owner: owner`). Drop leading `_` when a helper moves to its own module; keep it only for genuinely private helpers.

**`__init__.py`** — Explicit `__all__` (one name per line, alphabetical). Consumers import from the package root only, never from submodules directly.

**Function ordering** — Public first (matching `__all__`), private helpers after; callees before callers within each group.

**Function length** — Target 30 lines, hard ceiling 100. Every function independently testable.

**Docstrings** — One-line minimum for all functions. State WHAT (contract), not HOW.

**Comments** — Guide logic flow; never explain what code does at expression level. Always note non-obvious WHY.

**Error handling**
- DB: raise on programmer error; return `None` on expected absence (no row found).
- Handlers: catch `telegram.error.TelegramError` and log; never swallow silently. No bare `except`.
- **Telegram optional guards**: Narrow `update.callback_query`, `update.message`, and `query.data` with `if x is None: return` at the top of every handler — PTB stubs mark all as optional, and mypy flags all downstream usages without this guard.

**Async** — No blocking I/O in the event loop (`db/` SQLite is a known pragmatic exception). Sequential `await` over `asyncio.gather` unless concurrency is the goal. Never suppress `asyncio.CancelledError`.

**Encoding** — All files UTF-8.

## Python Version

- VirtualEnv: Python 3.12.10
- Bot: requires Python 3.10+; `python-telegram-bot~=22.7`
