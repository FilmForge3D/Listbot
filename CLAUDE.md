# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Listbot** is a Telegram bot for managing writing prompt lists in group chats, plus tooling to migrate data from the legacy bot.

1. **main.py** — Entry point. Parses args, loads locale, initialises DB, builds the Application, registers handlers, starts polling.

2. **db/** — SQLite data layer split by entity: `connection`, `schema`, `lists`, `prompts`, `users`, `shares`, `settings`.

3. **i18n/** — Localization package (`strings.py` + `locales/en.json`, `locales/de.json`). English + German.

4. **migration/extract_telegram.py** — Extracts and deduplicates ListBot messages from Telegram chat exports (used for migration from the legacy bot).

5. **migration/import_json.py** — Imports extracted prompt data into the ListBot SQLite database.

## Project Structure

```
Listbot/
├── main.py                         # Entry point (python-telegram-bot 22.x)
├── config.py                       # load_token(), DATA_DIR
├── messaging.py                    # notify, force_reply_msg, send_force_reply, cleanup_reply_messages
├── text.py                         # first_name
├── actions.py                      # do_draw
│
├── i18n/
│   ├── __init__.py                 # exports load_locale, t
│   ├── strings.py
│   └── locales/
│       ├── en.json                 # English strings
│       └── de.json                 # German strings
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
│   └── views.py                    # render_lists_view, render_list_view, render_share_panel
│
├── handlers/
│   ├── __init__.py                 # register_handlers(application)
│   ├── commands.py                 # /draw /add /lb /help /cancel
│   ├── callbacks.py                # button_handler
│   └── replies.py                  # reply_handler
│
├── Dockerfile                      # Container image definition
├── docker-compose.yml              # Compose deployment config
├── pyproject.toml                  # Dependencies + ruff/mypy config
├── requirements.txt                # pip-compatible dep list
├── example.token.txt               # Token file template
├── token.txt                       # Bot token (gitignored)
├── listbot.db                      # SQLite database (gitignored)
├── Listbot.code-workspace          # VS Code workspace
├── migration/                      # Migration tooling (moving to private branch)
│   ├── extract_telegram.py
│   ├── import_json.py
│   ├── result.json
│   └── ergebnis.json
├── venv/                           # Python 3.12 virtual environment
├── .gitignore
└── CLAUDE.md
```

## Repository Plans

The bot (`main.py`, `config.py`, `messaging.py`, `text.py`, `actions.py`, `db/`, `i18n/`, `ui/`, `handlers/`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`) will be made **public**. The migration tooling (`migration/`) will be moved to a **private branch**, as it was only ever used for a single deployment and is not relevant to general users.

## Migration Strategy

The legacy bot stored data in pickle files. Migration pipeline:

1. **Export**: Use `extract_telegram.py` to extract ListBot messages from Telegram group JSON exports
2. **Transform**: Script deduplicates and parses `/add`/`/grupp` commands to reconstruct list state
3. **Load**: Use `import_json.py` to insert extracted prompts into `listbot.db`

## Component 1: extract_telegram.py (Migration — Extraction)

**Status**: Active. Modern Python 3.12 script for message analysis.

### Core Functions

- **`match_listbot(text)`** — Pattern matching for ListBot messages (5 regex patterns: "drew", "added", "gruppt", legacy formats)
- **`get_text(message)`** — Extracts plain text from Telegram's entity-based text format
- **`load_json_tolerant(path)`** — Loads JSON with optional auto-repair via `json_repair` library
- **`extract_messages(input_path, bot_name)`** — Main logic:
  - Filters message-type entries (skips service messages like joins)
  - Collects ListBot matches and slash commands
  - **Deduplication**: Removes ListBot "added/grouped" messages if `/add` command exists within 5 message IDs prior
- **`print_section(title, messages)`** — Formats console output with timestamps and IDs

### Deduplication Heuristic

The 5-message window (`MSG_WINDOW`) assumes bot responses occur within a few messages of the triggering `/add` command. Prevents double-counting bot confirmations when both the command and bot message are present in exports.

### Dependencies

- **Standard library**: `json`, `re`, `argparse`, `pathlib`
- **Optional**: `json-repair` (graceful fallback if missing; warns user to install)

### Telegram Export Format

Input follows Telegram's official export JSON:
- Top-level: `name`, `type`, `id`, `messages` array
- Each message: `id`, `type` ("message" or "service"), `date`, `date_unixtime`, `from`, `text`
- **Text variants**: Can be string or list of mixed strings and entity objects (Telegram's rich-text format)

## Component 2: import_json.py (Migration — Import)

Reads the JSON output from `extract_telegram.py` and upserts prompts into `listbot.db` via `database.py`. Handles user deduplication (keeps the longest name per user ID).

## Component 3: Bot (Active)

**Status**: Active. Full-featured bot using `python-telegram-bot~=22.7` with async handlers.

### Architecture

- **Entry point**: `main.py` — builds the `Application`, registers handlers, starts polling
- **UI layer**: Inline keyboards (`InlineKeyboardMarkup`) for list/prompt browsing; `ForceReply` for text input (`ui/views.py`)
- **Data layer**: All persistence goes through `db/` (SQLite, `listbot.db`)
- **Localization**: All user-visible strings via `i18n/` (`strings.py` + `locales/*.json`)
- **Token loading**: `config.py` — `BOT_TOKEN` env var → `token.txt` fallback
- **Deployment**: Docker (`Dockerfile` + `docker-compose.yml`); database stored in `/app/data/`

### Key Handlers

| Handler | Purpose |
|---|---|
| `button_handler` | Dispatches all inline keyboard callbacks (list nav, draw, add, edit, remove, rename, delete, share) |
| `reply_handler` | Handles `ForceReply` responses for text input (new item, edit text, list rename, share target) |
| `draw_command` | `/draw [list]` — draws a random prompt from the specified or default list |
| `add_command` | `/add [list] text` — adds a prompt directly via command |
| `show_panel` | `/list` — opens the list-selection panel |
| `cancel_command` | `/cancel` — aborts any pending ForceReply action |
| `help_command` | `/help` — posts usage instructions in-thread |

### Notable Patterns

- **Single message per action**: All output consolidated into one message/edit to avoid multiple notifications
- **Thread awareness**: Passes `message_thread_id` through to keep replies in the correct forum topic
- **Shared lists**: Lists can be shared to other chats; ownership transfer supported

## Running the Tools

### Bot (main.py)

```bash
pip install -r requirements.txt

# Run directly
python main.py

# Run via Docker
docker-compose up --build
```

Token is read from `BOT_TOKEN` env var or `token.txt`. The database is created automatically on first run.

### extract_telegram.py

```bash
# Activate venv
venv\Scripts\activate

# Basic usage
python migration/extract_telegram.py

# With options
python migration/extract_telegram.py input.json --bot-name "MyBot" --output-json out.json --quiet
```

**Arguments**:
- `input` (positional, default: `result.json`) — Path to Telegram export
- `--bot-name NAME` — Bot's display name (default: `ListBot`)
- `--output-json FILE` — Save results as JSON
- `--quiet, -q` — Suppress console output

## Git Workflow

- **Commit on command**: When the user says "commit", create a git commit immediately — no confirmation needed. The user has already reviewed and verified the feature before issuing the command.
- **Keep changes synced**: Stage and commit only the files relevant to the feature being committed.
- **Suggest commit message**: Suggest a commit message when everything is done. The user can copy and paste it into the aktive commit or write their own.

## AI Collaboration Rules

⚠️ **These rules govern Claude's behavior, not general coding conventions:**

### Bot Behavior Rules
- **Single notification per action**: Any message sent by the bot must result in at most one notification to other chat users. Do not send multiple messages where one would suffice; consolidate all output into a single reply.

### Confirmation Required
- **Creating new files**: Always ask the user before creating a new file. Describe what the file will contain and why it is needed.
- **Large changes**: Any change exceeding ~30 net new lines requires explicit user approval before writing. Large changes are not unwanted — they just need the user to confirm the plan first, so the implementation stays focused and reviewable.

### New Functions
- **One at a time**: Implement only one new function per session/commit
- **Module split**: When a concern is large enough to stand alone (e.g., database, config, utilities), split it into its own module rather than growing a single file. Ask before doing so.

### Code Edits
- **Change limit**: Maximum 50 lines of continued code per edit (including unchanged context for readability)
- **One function per edit**: Only modify one function per Edit tool call
- **Rationale**: Keeps changes focused, reviewable, and debuggable

### Refactoring
- **Stick to the Plan**: There will always be a `refactor.md` file guiding any refactoring work. If the user asks for refactoring and no such file exists, ask for confirmation to create one. A single function may be refactored without a written plan.

### Examples

✅ **Good**: Adding a single helper function for list validation (45 lines)
```python
def validate_list_item(item: str, max_length: int = 255) -> tuple[bool, str]:
    """Validate a list item string."""
    # implementation (< 45 lines)
```

❌ **Bad**: Editing two functions or adding 200+ lines in one change

## Development Notes

### Character Encoding

All files use UTF-8 (necessary for German locale strings and code comments).

### Code Style

All bot modules use Python 3.10+ style: type hints, f-strings, `async/await`, union types (`X | Y` not `Optional[X]`).

**Type hints**
- Annotate every function signature, including `-> None` on void functions.
- Use `X | None`, never `Optional[X]`.
- Use `TypedDict` over `dict[str, Any]` when the shape of a dict is known and stable.
- Do not introduce `TypeAlias` or `Protocol` unless a type is reused in three or more places.

**Imports**
- Standard library → third-party → local; one blank line between groups. Within-group order is managed by ruff (`I` ruleset) — do not sort manually.
- Use module-level imports for `db` and `i18n`: `import db` / `import i18n as lang`. Call as `db.foo()` / `lang.t()`.
- Use direct function imports for other local modules: `from messaging import notify`, `from text import first_name`.
- Inside `db/` submodules, import from siblings directly: `from db.connection import get_connection`.

**Naming**
- Modules, functions, variables: `snake_case`; use full words — no abbreviations except universally understood ones (`id`, `url`, `db`)
- Classes: `CamelCase`
- Module-level constants: `SCREAMING_SNAKE_CASE` (e.g., `MSG_WINDOW`, `DB_PATH`)
- Booleans: `is_`, `has_`, or `can_` prefix (e.g., `is_shared`, `has_default`)
- Throwaway variables: single `_` (e.g., `for _ in range(n)`)
- Drop leading underscores when a helper moves to its own module — it is now a public API (`notify`, not `_notify`; `render_lists_view`, not `_render_lists_view`).
- Keep leading underscores only for genuinely private helpers that are not meant to be imported by other modules.

**Package `__init__.py`**
- Re-export the public API explicitly with `__all__`. Consumers always import from the package root (`from db import init_db`), never from submodules directly.
- Define `__all__` as a list of strings, one name per line, alphabetically sorted.

**Function ordering**
- Public functions first (matching `__all__` order), private helpers after.
- Within each group, prefer dependency order: callees before callers where natural.

**Function length**
- Target 30 lines per function; hard ceiling at 100 lines.
- Every function must be independently testable — no hidden state dependencies.

**Docstrings**
- Every private helper (leading underscore, not in `__all__`): one-line docstring.
- Every public function (in `__all__`): one-line minimum; multi-line permitted when the contract, edge cases, or parameters benefit from clarification. Keep it concise.
- Docstrings state WHAT the function does (its contract), not HOW.

**Comments**
- Comments guide a reader through function logic — a brief `# resolve owner before checking shares` is encouraged.
- Never explain what the code does at the expression level (`x += 1  # increment x`).
- Always add a comment when the WHY is non-obvious: a hidden constraint, a workaround, a subtle invariant.

**Error handling**
- DB functions: raise on programmer error (bad `list_id`, constraint violation); return `None` on expected absence (no row found).
- Handlers: catch `telegram.error.TelegramError` and log; never silently swallow exceptions.
- No bare `except`. Catch the narrowest exception type that makes sense.
- No custom exception classes unless the same error type is caught in two or more places.

**Async**
- Never call blocking I/O (file reads, DB) from the event loop without `run_in_executor`. SQLite access in this project is a known pragmatic exception — keep it contained to `db/`.
- Prefer sequential `await` over `asyncio.gather` unless concurrency is the explicit goal.
- Do not suppress `asyncio.CancelledError`.

## Python Version

- **VirtualEnv**: Python 3.12.10 (`venv/pyvenv.cfg`)
- **Bot** (`main.py` + modules): Requires Python 3.10+; `python-telegram-bot~=22.7`
- **extract_telegram.py / import_json.py**: Require Python 3.10+ (union type syntax)
