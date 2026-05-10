# Plan: Media/File Prompt Support

## DB changes (v1.0 — schema only) ✓

**`db/schema.py`** — recreate `prompts` table with:
- `text TEXT` → nullable (was `NOT NULL`)
- add `media_file_id TEXT` (nullable)
- add `media_type TEXT` (nullable, one of `photo/video/audio/document/animation`)
- add `CHECK (text IS NOT NULL OR media_file_id IS NOT NULL)`

---

## Function changes (v1.1 — actual use)

**`db/prompts.py`**
- `add_prompt` — add optional `media_file_id`/`media_type` params
- `edit_prompt` — accept optional media fields alongside text
- `remove_prompt` — return `media_file_id`/`media_type` in result dict
- `get_stats` — guard `most_drawn["text"]` for `None`

**`actions.py` / handlers**
- `do_draw` — branch on `media_type` to call the right PTB send method with `text` as caption
- Add/reply flows — detect media in incoming messages and pass file_id to `add_prompt`

> **Possible further v1.1 scope** — Telegram `file_id`s are tied to the bot instance and can expire;
> if multi-bot or backup/restore scenarios arise, storing `file_unique_id` alongside `file_id`
> for deduplication may be needed. Also consider whether `edit_prompt` should allow replacing
> media (requires re-upload UX) or only text edits initially.
