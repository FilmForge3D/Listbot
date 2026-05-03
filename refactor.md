# Listbot Refactor Plan

A step-by-step guide to restructuring the project. Each step is independently committable; the bot stays runnable between steps. Work through them at your own pace.

## Goal

Move from the current flat layout to a grouped-by-responsibility layout, splitting the monolithic `ListBot.py` into focused modules. No `src/` wrapper — the bot is an application, not a library.

## Target layout

```
Listbot/
├── pyproject.toml                  # deps + ruff/mypy config
├── README.md
├── CLAUDE.md
├── refactor.md                     # this file (delete when done)
├── Dockerfile
├── docker-compose.yml
├── example.token.txt
├── token.txt                       # gitignored
├── listbot.db                      # gitignored
├── .gitignore
│
├── main.py                         # entry point: `python main.py`
├── config.py                       # load_token(), DATA_DIR
├── messaging.py                    # _notify, _force_reply_msg, _send_force_reply, _cleanup_reply_messages
├── text.py                         # _first_name etc.
├── actions.py                      # _do_draw
│
├── i18n/
│   ├── __init__.py                 # exports load_locale, t
│   ├── strings.py
│   └── locales/
│       ├── en.json
│       └── de.json
│
├── db/
│   ├── __init__.py                 # re-exports public API
│   ├── connection.py               # get_connection(), DB_PATH
│   ├── schema.py                   # init_db()
│   ├── lists.py
│   ├── prompts.py
│   ├── users.py
│   ├── shares.py
│   └── settings.py
│
├── ui/
│   ├── __init__.py
│   └── views.py                    # _render_lists_view, _render_list_view, _render_share_panel
│
├── handlers/
│   ├── __init__.py                 # register_handlers(application)
│   ├── commands.py                 # /draw /add /lb /help /cancel
│   ├── callbacks.py                # button_handler
│   └── replies.py                  # reply_handler
│
├── tests/
│   └── test_db_smoke.py            # one round-trip test
│
└── migration/                      # renamed from "Nachricht extrahieren"
    ├── extract_telegram.py
    ├── import_json.py
    └── samples/
        ├── result.json
        └── ergebnis.json
```

---

## Step 1 — Add `pyproject.toml`

**Why**: Centralises dependencies and tooling config (ruff, mypy). Replaces `requirements.txt`.

**Action**:
1. Create `pyproject.toml` with:
   - `[project]` block: name, python version (>=3.10), dependencies (copy from `requirements.txt`)
   - `[tool.ruff]`: line length, target Python version
   - `[tool.mypy]`: strict mode, target Python version
2. Run `ruff check .` and `mypy .` against current code. Fix any issues that surface (likely a few — unused imports, missing annotations).
3. Update `Dockerfile`: replace `pip install -r requirements.txt` with `pip install .` (or keep `requirements.txt` alongside if you'd rather not change Docker).
4. Delete `requirements.txt` once Docker build is verified.

**Files touched**: new `pyproject.toml`, possibly `Dockerfile`, possibly minor fixes in `.py` files.

**Alternative**: If you'd rather not migrate dependency management, keep `requirements.txt` and use a `ruff.toml` + `mypy.ini` instead. The rest of this plan is independent of this choice.

**Verification**: `python ListBot.py` still starts the bot.

---

## Step 2 — Create `i18n/` package

**Why**: Locales currently live at repo root; grouping them with the loader keeps related code together and makes the `Path(__file__).parent / "locales"` resolution unambiguous.

**Action**:
1. Create directory `i18n/`.
2. Move `strings.py` → `i18n/strings.py`.
3. Move `locales/` → `i18n/locales/`.
4. Create `i18n/__init__.py` that re-exports the public API:
   ```python
   from i18n.strings import load_locale, t

   __all__ = ["load_locale", "t"]
   ```
5. Update import in `ListBot.py`:
   ```python
   from strings import load_locale, t
   ```
   becomes:
   ```python
   from i18n import load_locale, t
   ```

**Gotcha**: `strings.py` resolves locale paths via `Path(__file__).parent / "locales"`. After the move, `__file__` is now `i18n/strings.py`, so `__file__.parent / "locales"` resolves to `i18n/locales/` — which is correct. No code change needed inside `strings.py`.

**Verification**: `python ListBot.py` still starts and serves both languages.

---

## Step 3 — Split `database.py` into a `db/` package

**Why**: `database.py` is ~400 lines mixing five concerns (lists, prompts, users, shares, settings). Splitting by entity makes each file <150 lines and gives each concern a clear home.

**Action**:
1. Create directory `db/`.
2. Move `database.py` → `db/__init__.py` first as a single bulk move. Update the import in `ListBot.py`:
   ```python
   from database import (...)
   ```
   becomes:
   ```python
   from db import (...)
   ```
3. **Verify the bot still runs.** Commit this as a checkpoint before splitting further.
4. Now split `db/__init__.py` into separate modules:
   - `db/connection.py` — `DB_PATH`, `get_connection()`
   - `db/schema.py` — `init_db()`
   - `db/lists.py` — `get_list_names`, `_get_or_create_list`, `rename_list`, `delete_list`
   - `db/prompts.py` — `add_prompt`, `get_prompts`, `edit_prompt`, `remove_prompt`, `draw_random_prompt`, `get_stats`
   - `db/users.py` — `upsert_user`, `lookup_name`
   - `db/shares.py` — `add_list_share`, `remove_list_share`, `get_list_shares`, `get_shared_lists`, `transfer_list_ownership`, `resolve_list_owner`
   - `db/settings.py` — `get_default_list`, `set_default_list`
5. Reduce `db/__init__.py` to just re-export the public API for callers:
   ```python
   from db.connection import get_connection
   from db.schema import init_db
   from db.lists import get_list_names, rename_list, delete_list
   from db.prompts import (
       add_prompt, get_prompts, edit_prompt, remove_prompt,
       draw_random_prompt, get_stats,
   )
   from db.users import upsert_user, lookup_name
   from db.shares import (
       add_list_share, remove_list_share, get_list_shares,
       get_shared_lists, transfer_list_ownership, resolve_list_owner,
   )
   from db.settings import get_default_list, set_default_list
   ```
6. Inside each `db/*.py` module, import `get_connection` from `db.connection`.
7. **Remove the inline `from database import get_connection` calls** in `ListBot.py` (currently at lines ~100, ~384, ~499, ~518, ~537). Replace with a top-level import: `from db import get_connection`.

**Gotcha**: `_get_or_create_list` in `db/lists.py` is used by `add_prompt` in `db/prompts.py`. Either import it across modules, or move it to `db/lists.py` and import from there.

**Verification**: Bot still runs. Add `tests/test_db_smoke.py` here as a guard rail (see Step 9).

---

## Step 4 — Extract `ui/views.py`

**Why**: The three `_render_*` functions in `ListBot.py` are pure (input → text + markup). Pulling them out lets handlers stay focused on dispatch.

**Action**:
1. Create directory `ui/` with empty `__init__.py`.
2. Create `ui/views.py` and move:
   - `_render_lists_view` (currently `ListBot.py:49-74`)
   - `_render_list_view` (currently `ListBot.py:77-95`)
   - `_render_share_panel` (currently `ListBot.py:98-138`)
3. Add necessary imports at the top of `ui/views.py`:
   ```python
   from telegram import InlineKeyboardButton, InlineKeyboardMarkup
   from db import (
       get_list_names, get_shared_lists, get_default_list, get_prompts,
       get_list_shares, get_connection, lookup_name,
   )
   from i18n import t
   ```
4. Remove these functions from `ListBot.py`. Add `from ui.views import _render_lists_view, _render_list_view, _render_share_panel` at the top.
5. Optional: rename to drop the leading underscore (`render_lists_view` etc.) since they're now part of a module's public surface. Update all callers.

**Gotcha**: `_render_share_panel` currently does its own SQL via `from database import get_connection` (inline at line 100). After Step 3 this should already be `from db import get_connection`. Consider moving that SQL into a new `db/shares.py` helper like `get_list_id(owner_chat_id, list_name)` to keep raw SQL out of `ui/`.

**Verification**: Bot still runs; all three panels render correctly.

---

## Step 5 — Extract `messaging.py`, `text.py`, `actions.py`

**Why**: Separates side-effect helpers (Telegram I/O), pure helpers (string parsing), and orchestration. Matches "isolate I/O at the edges" from `Structure.md`.

**Action**:
1. Create `text.py` and move:
   - `_first_name` (currently `ListBot.py:160-163`)
2. Create `messaging.py` and move:
   - `_notify` (currently `ListBot.py:141-143`)
   - `_force_reply_msg` (currently `ListBot.py:146-157`)
   - `_send_force_reply` (currently `ListBot.py:168-194`)
   - `_cleanup_reply_messages` (currently `ListBot.py:197-200`)
3. Create `actions.py` and move:
   - `_do_draw` (currently `ListBot.py:203-215`)
4. Add imports as needed. `actions.py` needs `from messaging import _notify`, `from text import _first_name`, `from i18n import t`, `from db import draw_random_prompt`.
5. Update `ListBot.py` to import from the new modules. Remove the moved code.
6. Optional: drop leading underscores on the functions now that they're public APIs of their modules.

**Verification**: Bot still runs; `/draw`, `/add`, force-reply prompts all behave correctly.

---

## Step 6 — Create `config.py`

**Why**: Token loading is configuration, not bot logic. It also doesn't belong in the entry-point module that we're about to slim down.

**Action**:
1. Create `config.py` and move:
   - `load_token()` (currently `ListBot.py:30-46`)
2. Add a top-level constant if helpful:
   ```python
   import os
   from pathlib import Path
   DATA_DIR = Path(os.environ.get("DATA_DIR", "."))
   ```
   Then in `db/connection.py`:
   ```python
   from config import DATA_DIR
   DB_PATH = DATA_DIR / "listbot.db"
   ```
3. Update `ListBot.py` to `from config import load_token`.

**Verification**: Bot still loads the token and connects to the database correctly.

---

## Step 7 — Split `handlers/`

**Why**: `button_handler` is one giant `elif` chain (~180 lines). Splitting by trigger type (command / callback / reply) gives each file a single responsibility and makes the dispatcher easier to navigate.

**Action**:
1. Create directory `handlers/`.
2. Create `handlers/commands.py` and move:
   - `draw_command` (`ListBot.py:581-593`)
   - `add_command` (`ListBot.py:596-616`)
   - `show_panel` (`ListBot.py:620-628`)
   - `help_command` (`ListBot.py:631-638`)
   - `cancel_command` (`ListBot.py:549-578`)
3. Create `handlers/callbacks.py` and move:
   - `button_handler` (`ListBot.py:218-399`)
4. Create `handlers/replies.py` and move:
   - `reply_handler` (`ListBot.py:402-546`)
5. Create `handlers/__init__.py` with a `register_handlers(application)` function:
   ```python
   from telegram import Update
   from telegram.ext import (
       Application, CommandHandler, CallbackQueryHandler,
       MessageHandler, filters,
   )
   from handlers.commands import (
       draw_command, add_command, show_panel, help_command, cancel_command,
   )
   from handlers.callbacks import button_handler
   from handlers.replies import reply_handler


   def register_handlers(application: Application) -> None:
       """Attach all bot handlers to the application."""
       application.add_handler(CommandHandler("help", help_command))
       application.add_handler(CommandHandler("lb", show_panel))
       application.add_handler(CommandHandler("add", add_command))
       application.add_handler(CommandHandler("draw", draw_command))
       application.add_handler(CommandHandler("cancel", cancel_command))
       application.add_handler(CallbackQueryHandler(button_handler))
       application.add_handler(MessageHandler(
           filters.REPLY & filters.TEXT & ~filters.COMMAND, reply_handler,
       ))
   ```
6. Each handler module imports what it needs from `messaging`, `actions`, `ui.views`, `text`, `db`, `i18n`.

**Gotcha**: `button_handler` is huge. Consider — but don't have to do now — a future cleanup that turns the `elif` chain into a small dispatch table keyed by callback prefix. That's a separate refactor; for now, just move it whole.

**Verification**: Every command, button, and force-reply still works end-to-end.

---

## Step 8 — Collapse `ListBot.py` into `main.py`

**Why**: After Steps 1–7, `ListBot.py` should be ~30 lines: parse args, load locale, init DB, build app, register handlers, poll. Rename to `main.py` to match conventional Python entry-point naming.

**Action**:
1. The remaining content of `ListBot.py` should look like:
   ```python
   #!/usr/bin/env python3
   """Modern Telegram bot for managing writing prompt lists."""

   import argparse
   import logging

   from telegram import Update
   from telegram.ext import Application

   from config import load_token
   from db import init_db
   from handlers import register_handlers
   from i18n import load_locale

   logging.basicConfig(
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
       level=logging.INFO,
   )


   def main() -> None:
       """Start the bot."""
       parser = argparse.ArgumentParser()
       parser.add_argument("--lang", default="", help="Locale to use (default: BOT_LANG env var or 'en')")
       args = parser.parse_args()
       load_locale(args.lang)
       init_db()
       token = load_token()
       application = Application.builder().token(token).build()
       register_handlers(application)
       application.run_polling(allowed_updates=Update.ALL_TYPES)


   if __name__ == "__main__":
       main()
   ```
2. Rename `ListBot.py` → `main.py`.
3. Update `Dockerfile`: change `CMD ["python", "ListBot.py"]` → `CMD ["python", "main.py"]`.
4. Update `docker-compose.yml` if it references `ListBot.py` directly.
5. Update `README.md` and `CLAUDE.md` references.

**Verification**: `python main.py` starts the bot. `docker-compose up --build` starts the bot.

---

## Step 9 — Add `tests/test_db_smoke.py`

**Why**: One round-trip smoke test guards against the `db/` split breaking something silently. Anything beyond that is overkill for a working bot — add tests when changing things, not preemptively.

**Action**:
1. Create `tests/test_db_smoke.py`. Cover one happy-path flow per major db module:
   - Create a list → add a prompt → get prompts → draw → remove → delete list.
   - Use a `tmp_path` fixture for the DB so tests don't touch `listbot.db`.
2. Set `DATA_DIR` env var (or override `DB_PATH`) inside the test to redirect to `tmp_path`.
3. ~50 lines total. No mocks needed — SQLite is fast enough.

**Verification**: `pytest tests/` passes.

---

## Step 10 — Rename `Nachricht extrahieren/` → `migration/`

**Why**: Removes the space (which forces quoting in every CLI invocation), makes the folder's purpose immediately clear, and prepares it cleanly for the private-branch cut described in `CLAUDE.md`.

**Action**:
1. `git mv "Nachricht extrahieren" migration`
2. Optionally move `result.json` and `ergebnis.json` into `migration/samples/`.
3. Update any references in `CLAUDE.md`, `README.md`, or scripts.

**Verification**: `python migration/extract_telegram.py` still runs.

**Note**: This step can also be deferred and done as part of the public/private branch split. Either order is fine.

---

## Step 11 — Cleanup

**Action**:
1. Delete `refactor.md`.
2. Update `CLAUDE.md` to reflect the new layout (the "Project Structure" tree).
3. Update `README.md` if it documents the file layout or run command.
4. Run `ruff check . && ruff format .` and `mypy .` once more.

---

## Notes & gotchas

- **Inline imports**: `ListBot.py` currently has several `from database import get_connection` calls inside functions. These are import-cycle workarounds or mid-refactor leftovers. After Step 3 + Step 4, they can all become top-level imports.
- **Public-vs-private naming**: Many helpers in `ListBot.py` are named with leading underscores (`_render_*`, `_notify`, `_first_name`). After they move to their own modules, they become the module's public API — consider dropping the underscore. Up to you; either is consistent if applied uniformly.
- **Commit cadence**: Each numbered step is a natural commit boundary. Within Step 3, the bulk move (substep 2) and the entity split (substep 4) are also natural to commit separately.
- **CLAUDE.md constraints**: This refactor exceeds the "30 net new lines" rule by a lot in aggregate, but each individual step stays focused. If you ask me to execute a step, I'll work within the per-step boundary.
- **Bot stays running**: Don't stop the production bot during the refactor. Each step keeps the code runnable; restart the bot once at the end (or after Step 8 when the entry point renames).
