# ListBot – Improvement Plan
_Extracted from test session 2026-04-27_

---

## Bugs

### 1. Remove button does nothing
**Reported by:** Cora — "Bei mir passiert nix, wenn ich auf remove tippe"
The `remove:` callback has no handler in `button_handler`. Needs a ForceReply flow identical to Edit, asking for a position number.

### 2. Panel shows as "reply to deleted message"
**Reported by:** Kai — "dass das eine antwort auf deleted message ist ist komisch"
The bot sends the `/lb` panel as a reply to the `/lb` command, which then gets deleted. This leaves the panel visually linked to a ghost message. Fix: send the panel as a fresh message, not a reply.

---

## UX Improvements

### 3. Show prompt author in draw message
**Requested by:** Mantel Mann — "Ich fänds glaube ich schön, wenn die Person, von dem der Prompt kam, auch in der /draw-Message gelistet ist."
**Confirmed by:** Kai — "gute idee"
Draw messages currently show who drew but not who added the prompt. Add the `added_by_name` field from the DB to the draw output.
_Example:_ `🎲 Mantel Mann drew from Prompts:`
`gemeinsam dumm sein` _(added by ||Lena||)_

### 4. Default list indicator in the list selection panel
**Reported by:** Kai — "nen default indicator fehlt auch"
The main `/lb` panel shows all lists but gives no visual cue which one is the default. Add a marker (e.g. ⭐) next to the default list button.

### 5. Delete panel after draw
**Suggested by:** Mantel Mann — "die zweite kleinere Nachricht zu haben und die Menünachricht zu löschen, die ist Bulky und nimmt Platz weg"
**Confirmed by:** Kai — "klingt logisch"
After a draw action via the panel, delete the panel message and send only the standalone draw message. The user can open `/lb` again for the next draw.
The same action goes for all comands that have a distinct end to the procedure. Namely Edit, Remove, Add

### 6. Blockquote formatting for drawn prompt
**Suggested by:** Mantel Mann — "Vielleicht den Prompt sogar in ne Quote setzen"
Format the prompt text in draw messages using Telegram's blockquote style instead of italic, to make it visually distinct.

### 7. Rework add confirmation message formatting
**Suggested by:** Mantel Mann:
> `✅ Cora` _(bold)_ `added` _(italic)_ `to #1234 Prompts` _(italic)_`:` Prompt ohne Italics
Currently the prompt text is italic and the position is inline. Proposed: name bold, action italic, prompt plain text.

---

## Larger Features

### 8. Stats snapshot / year-end recap
**Discussed by:** Cora, Mantel, Kai
The stats view shows live cumulative numbers but there's no way to record a point-in-time snapshot for comparison (e.g. stats on Jan 1 vs Dec 31). Kai noted the data is there (prompt, adder, time added, times drawn, time last drawn) but no snapshot mechanism exists yet.
Possible approach: a `/snapshot` command or scheduled export that saves the current stats to a JSON file or a `snapshots` DB table with a timestamp.

### 9. Distinct names for users
**Current Situation:** The Imported Prompts are stored by First Name, the new ones by Full Name.
**Proposed change:** Store By user ID and store the First Name of User. Update when changed. Requires a reimport of the db with adjusted impoter script.