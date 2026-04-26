# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Listbot** is a project for managing and analyzing writing prompt lists via Telegram:

1. **ListBot.old.py** — A Telegram bot (v0.1.6) that manages multiple persistent lists in group chats, supporting add/remove/draw/edit operations with separate draw tracking. Works up to Python Telegram Bot 13.14

2. **ListBot.py** — The Modern recreation of the old project.

3. **Nachricht extrahieren/extract_telegram.py** — A modern utility for extracting and deduplicating messages from Telegram Chats that have the Bot as part of them. It will be used to migrate the database from the old Bot to the new.

## Project Structure

```
Listbot/
├── ListBot.old.py                  # Original Telegram bot (version 0.1.6, archived)
├── ListBot.py                      # Modern recreation of the bot
├── Nachricht extrahieren/          # Modern message extraction subdirectory
│   ├── extract_telegram.py         # Primary extraction/analysis script for migration
│   ├── result.json                 # Sample Telegram export input
│   ├── ergebnis.json               # Example output
│   └── venv/                       # Python 3.12 virtual environment
├── .gitignore                      # Gitignore
└── CLAUDE.md                       # This file
```

## Migration Strategy

The project is transitioning from the legacy bot to a modern implementation:

1. **Export**: Use `extract_telegram.py` to extract ListBot messages from Telegram group exports
2. **Transform**: Parse the extracted data to reconstruct the writing prompt lists
3. **Load**: Migrate the lists into the new ListBot.py's database format

The extraction tool handles deduplication and message parsing to ensure data integrity during the migration.

## Component 1: ListBot.old.py (Legacy Bot)

**Status**: Archived/legacy. Uses deprecated `python-telegram-bot` API (`Updater`, `CommandHandler` from `telegram.ext`).

### Key Architecture

- **Chat-scoped persistence**: Lists stored per chat ID in `./lists/` directory using Python pickle format
- **Three independent lists**: Primary, list2, list3 (suffix-based file naming)
- **Drawn tracking**: Separate pickle files track "drawn" entries with archival (`.drawn_old` backups)
- **Command-driven**: 19 slash commands tripled for 3 lists (/add, /add2, /add3, etc.)
- **Message deletion**: Automatically deletes user commands and bot confirmations to keep chats clean

### Core Patterns

- **List loading**: Wrapped in try-except to gracefully handle missing lists
- **Message splitting**: Commands parsed by whitespace with validation (e.g., `/add item name`)
- **Drawn state**: Stores indices; must sync with list file (deleting list item #5 doesn't auto-update drawn list)
- **Message length limits**: Breaks output at 3584 chars (Telegram limit), continues with "Use '/list N' to continue"
- **Pickle protocol**: Lists stored as Python lists (serialized with pickle). Not human-readable or portable.

### Command Groups

| Command Class | Purpose | Variants |
|---|---|---|
| `/add{,2,3}` | Add item to list | 3 lists |
| `/grupp{,2,3}` | German "group" variant (same as add) | 3 lists |
| `/list{,2,3}` | Show full list or subset by start number | 3 lists |
| `/list{,2,3} drawn` | Show only drawn entries | 3 lists |
| `/draw{,2,3} [count]` | Draw N random entries (default 1) | 3 lists |
| `/remove{,2,3} {number\|drawn}` | Remove single item or all drawn | 3 lists |
| `/undraw{,2,3} {number\|all}` | Clear draw marker from entries | 3 lists |
| `/edit{,2,3} number newtext` | Replace list entry | 3 lists |
| `/reset{,2,3}` | Archive and clear list (requires confirmation) | 3 lists |
| `/help` | Bot instructions | 1 |
| `/getid` | Return chat ID | 1 |

### Hardcoded Bot Token

⚠️ **Security note**: Line 1780 contains a plaintext Telegram bot token. This is archived code; treat as exposed.

## Component 2: extract_telegram.py (Modern Utility)

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

## Component 3: ListBot.py (Modern Bot)

**Status**: Under development. Modern recreation of ListBot.old.py using current `python-telegram-bot` library (v20+).

### Goals

- Maintain feature parity with legacy bot (add/remove/draw/edit/list operations)
- Support three independent lists per chat (primary, list2, list3)
- Use modern async/await patterns instead of deprecated `Updater`
- Improve data storage (move from pickle to a more maintainable format)
- Clean command handlers and reduce code duplication

### Expected Improvements

- **Modern library support**: Uses current `python-telegram-bot` v20+ with async handlers
- **Type hints**: Full type annotations for clarity and IDE support
- **Database**: Likely uses SQLite or JSON instead of pickle (TBD)
- **Refactoring**: Single parameterized handler instead of tripled functions
- **Better error handling**: Structured exception handling vs. bare `except:` blocks

### Data Migration Path

Lists exported via `extract_telegram.py` will be transformed into the new bot's database format:
1. Extract messages using `extract_telegram.py` → JSON output
2. Parse `/add` commands and `/grupp` messages to reconstruct list state
3. Load into ListBot.py's data store (format TBD)

## Running the Tools

### ListBot.old.py (Legacy)

Requires `python-telegram-bot` library version 13.14 or earlier (modern versions removed `Updater`):

```bash
# Install old version if needed
pip install "python-telegram-bot>=13.0,<14.0"

# Run
python ListBot.old.py
```

Bot will start polling for Telegram updates and serve commands until interrupted.

### ListBot.py (Modern)

Currently under development. Once complete, will use modern `python-telegram-bot` v20+:

```bash
# Will require (once implemented)
pip install python-telegram-bot>=20.0

# Run (TBD)
python ListBot.py
```

Expects modern async bot initialization with `Application` class and async command handlers.

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

## Development Safeguards

⚠️ **Critical constraints for all future work:**

### Off-Limits
- **ListBot.old.py**: Do NOT edit. This is archived legacy code preserved for reference and migration purposes only.

### Confirmation Required
- **Creating new files**: Always ask the user before creating a new file. Describe what the file will contain and why it is needed.
- **Large changes**: Any change exceeding ~30 net new lines requires explicit user approval before writing.

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

❌ **Bad**: Editing ListBot.old.py

## Development Notes

### Character Encoding

Both scripts explicitly use UTF-8 (necessary for German text in messages and code comments).

### Code Style Observations

- **ListBot.old.py**: Early-2020s style; bare `except:`, string concatenation, no type hints, inline variable comments
- **extract_telegram.py**: Modern Python; type hints with union syntax (`|`), f-strings, clean structure

### Pickle Security

ListBot stores state in pickle files (`.../lists/{chat_id}`). Pickle can execute arbitrary code; only load from trusted sources.

### Redundant Functions

ListBot has significant code duplication across variants 1/2/3. The triple-variant pattern (list, list2, list3) could be refactored into a parameterized handler, but is preserved as-is in the legacy code.

## Python Version

- **VirtualEnv**: Python 3.12.10 (configured in `venv/pyvenv.cfg`)
- **ListBot.old.py**: Compatible with Python 2.7-3.9 (old `telegram.ext` API era); requires `python-telegram-bot` 13.x
- **ListBot.py**: Target Python 3.10+ with `python-telegram-bot` 20+
- **extract_telegram.py**: Requires Python 3.10+ (uses `X | Y` union type syntax)
