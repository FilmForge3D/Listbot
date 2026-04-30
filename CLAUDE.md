# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Listbot** is a Telegram bot for managing writing prompt lists in group chats, plus tooling to migrate data from the legacy bot.

1. **ListBot.py** — The active bot. Manages named prompt lists per chat with inline-keyboard UI, SQLite persistence, localization, and Docker deployment support.

2. **database.py** — SQLite data layer (lists, prompts, users, shares).

3. **strings.py** + **locales/** — Localization system (English + German).

4. **Nachricht extrahieren/extract_telegram.py** — Extracts and deduplicates ListBot messages from Telegram chat exports (used for migration from the legacy bot).

5. **Nachricht extrahieren/import_json.py** — Imports extracted prompt data into the ListBot SQLite database.

## Project Structure

```
Listbot/
├── ListBot.py                      # Active Telegram bot (python-telegram-bot 22.x)
├── database.py                     # SQLite data layer
├── strings.py                      # Localization loader
├── locales/
│   ├── en.json                     # English strings
│   └── de.json                     # German strings
├── Dockerfile                      # Container image definition
├── docker-compose.yml              # Compose deployment config
├── requirements.txt                # Python dependencies
├── example.token.txt               # Token file template
├── token.txt                       # Bot token (gitignored)
├── listbot.db                      # SQLite database (gitignored)
├── Listbot.code-workspace          # VS Code workspace
├── Nachricht extrahieren/          # Migration tooling
│   ├── extract_telegram.py         # Extracts messages from Telegram export JSON
│   ├── import_json.py              # Imports extracted data into listbot.db
│   ├── result.json                 # Sample Telegram export input
│   └── ergebnis.json               # Example extraction output
├── venv/                           # Python 3.12 virtual environment
├── .gitignore
└── CLAUDE.md
```

## Repository Plans

The bot (`ListBot.py`, `database.py`, `strings.py`, `locales/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`) will be made **public**. The migration tooling (`Nachricht extrahieren/`) will be moved to a **private branch**, as it was only ever used for a single deployment and is not relevant to general users.

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

## Component 3: ListBot.py (Active Bot)

**Status**: Active. Full-featured bot using `python-telegram-bot~=22.7` with async handlers.

### Architecture

- **Entry point**: `main()` builds the `Application`, registers handlers, starts polling
- **UI layer**: Inline keyboards (`InlineKeyboardMarkup`) for list/prompt browsing; `ForceReply` for text input
- **Data layer**: All persistence goes through `database.py` (SQLite, `listbot.db`)
- **Localization**: All user-visible strings via `strings.py` / `locales/*.json`
- **Token loading**: `BOT_TOKEN` env var → `token.txt` fallback
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

### ListBot.py

```bash
pip install -r requirements.txt

# Run directly
python ListBot.py

# Run via Docker
docker-compose up --build
```

Token is read from `BOT_TOKEN` env var or `token.txt`. The database is created automatically on first run.

### extract_telegram.py

```bash
# Activate venv
venv\Scripts\activate

# Basic usage
python "Nachricht extrahieren/extract_telegram.py"

# With options
python "Nachricht extrahieren/extract_telegram.py" input.json --bot-name "MyBot" --output-json out.json --quiet
```

**Arguments**:
- `input` (positional, default: `result.json`) — Path to Telegram export
- `--bot-name NAME` — Bot's display name (default: `ListBot`)
- `--output-json FILE` — Save results as JSON
- `--quiet, -q` — Suppress console output

## Git Workflow

- **Commit on command**: When the user says "commit", create a git commit immediately — no confirmation needed. The user has already reviewed and verified the feature before issuing the command.
- **Keep changes synced**: Stage and commit only the files relevant to the feature being committed.

## Development Safeguards

⚠️ **Critical constraints for all future work:**

### Bot Behavior Rules
- **Single notification per action**: Any message sent by the bot must result in at most one notification to other chat users. Do not send multiple messages where one would suffice; consolidate all output into a single reply.

### Confirmation Required
- **Creating new files**: Always ask the user before creating a new file. Describe what the file will contain and why it is needed.
- **Large changes**: Any change exceeding ~30 net new lines requires explicit user approval before writing. Large changes are not unwanted — they just need the user to confirm the plan first, so the implementation stays focused and reviewable.

### New Functions
- **Size limit**: Maximum 100 lines per new function
- **Testability**: All new functions must be independently testable
- **One at a time**: Implement only one new function per session/commit
- **Module split**: When a concern is large enough to stand alone (e.g., database, config, utilities), split it into its own module rather than growing a single file. Ask before doing so.

### Code Edits
- **Change limit**: Maximum 50 lines of continued code per edit (including unchanged context for readability)
- **One function per edit**: Only modify one function per Edit tool call
- **Rationale**: Keeps changes focused, reviewable, and debuggable

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

- **ListBot.py / database.py / strings.py**: Modern Python 3.12; type hints, f-strings, async/await, full type annotations
- **extract_telegram.py / import_json.py**: Same modern style; union types (`X | Y`)

## Python Version

- **VirtualEnv**: Python 3.12.10 (`venv/pyvenv.cfg`)
- **ListBot.py**: Requires Python 3.10+; `python-telegram-bot~=22.7`
- **extract_telegram.py / import_json.py**: Require Python 3.10+ (union type syntax)
