# ListBot

A Telegram bot for managing named writing prompt lists in group chats. Browse, add, draw, and share lists via an inline keyboard UI — no commands needed for day-to-day use. Quick commands for interacting with a default list are available.

> This project was built with the assistance of AI (Claude by Anthropic).

## Features

- **Named lists per chat** — create as many lists as you need
- **Draw random prompts** — tracks what's already been drawn
- **Inline keyboard UI** — browse and manage lists without memorizing commands
- **Sharing** — share a list with other chats; transfer ownership when needed
- **Stats** — draw counts, contributor breakdown, never-drawn items
- **Localization** — English and German out of the box

## Commands

| Command | Description |
|---|---|
| `/lb` | Open the interactive list panel |
| `/draw [list]` | Draw a random item from a list (default if omitted) |
| `/add <text>` | Add an item to the default list |
| `/cancel` | Cancel a pending add/edit/remove prompt |
| `/help` | Show usage instructions |

## Setup

### Token

Provide your bot token via the `BOT_TOKEN` environment variable, or place it in a `token.txt` file in the project root.

```
BOT_TOKEN=your_token_here
```

### Run directly

```bash
pip install -r requirements.txt
python ListBot.py
```

Requires Python 3.10+.

### Run with Docker Compose

Edit `docker-compose.yml` and set your token, then:

```bash
docker-compose up --build
```

The SQLite database is stored in `./data/` on the host.

## Localization

The bot ships in English and German. Defaults to English.

**Direct run** — use the `--lang` flag:
```bash
python ListBot.py --lang de
```

**Docker Compose** — add `BOT_LANG` to the `environment` section in `docker-compose.yml`:
```yaml
environment:
  - BOT_TOKEN=your_token_here
  - BOT_LANG=de
```

To add a new language, copy `locales/en.json`, translate the values, and save it as `locales/<lang>.json`.

## Requirements

- Python 3.10+
- `python-telegram-bot~=22.7`
