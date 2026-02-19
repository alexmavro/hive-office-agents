# Available Tools

## File Operations

### read_file
Read the contents of a file.
```
read_file(path: str) -> str
```

### write_file
Create or overwrite a file. Parent directories are created automatically.
```
write_file(path: str, content: str) -> str
```

### edit_file
Edit a file by replacing a specific text string with another.
```
edit_file(path: str, old_text: str, new_text: str) -> str
```

### list_dir
List contents of a directory.
```
list_dir(path: str) -> str
```

---

## Shell Execution

### exec
Execute a shell command and return stdout + stderr.
```
exec(command: str, working_dir: str = None) -> str
```

- **Timeout:** 60 seconds (configurable)
- **Blocked:** `rm -rf`, `format`, `dd`, `shutdown`, fork bombs
- **Output:** truncated at 10,000 characters
- **Access:** full root shell — you can install packages, call APIs, write scripts

**Pattern — call any external API via Python:**
```bash
exec("""python3 - <<'EOF'
import httpx, os, json
resp = httpx.post(
    "https://api.example.com/endpoint",
    headers={"Authorization": f"Bearer {os.environ['SOME_KEY']}"},
    json={"param": "value"},
)
print(resp.text)
EOF""")
```

**Available API keys (set in environment):**
- `GEMINI_API_KEY` — Google Gemini + Imagen 3 image generation
- Check `~/.hive/config.json` for other configured providers

**Image generation via Gemini Imagen 3:**
```bash
exec("""python3 - <<'EOF'
import httpx, os, base64, json

api_key = os.environ.get("GEMINI_API_KEY") or open("/root/.hive/config.json").read()
# ... parse key from config if needed

resp = httpx.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict",
    params={"key": api_key},
    json={
        "instances": [{"prompt": "YOUR PROMPT HERE"}],
        "parameters": {"sampleCount": 1}
    },
    timeout=60,
)
data = resp.json()
img_b64 = data["predictions"][0]["bytesBase64Encoded"]
with open("/tmp/generated.png", "wb") as f:
    f.write(base64.b64decode(img_b64))
print("Image saved to /tmp/generated.png")
EOF""")
```

**Send image via Telegram Bot API:**
```bash
exec("""python3 - <<'EOF'
import httpx, json

TOKEN = open("/root/.hive/config.json").read()  # parse from config
# OR: read from env via subprocess: subprocess.check_output(["..."])

resp = httpx.post(
    f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
    data={"chat_id": "CHAT_ID_HERE"},
    files={"photo": open("/tmp/generated.png", "rb")},
    timeout=30,
)
print(resp.text)
EOF""")
```

---

## Web Access

### web_search
Search the web using Brave Search API.
```
web_search(query: str, count: int = 5) -> str
```
Returns titles, URLs, and snippets. Requires `tools.web.search.apiKey` in config.

### web_fetch
Fetch and extract main content from a URL.
```
web_fetch(url: str, extractMode: str = "markdown", maxChars: int = 50000) -> str
```
Content extracted using readability. Supports markdown or plain text output.

---

## Communication

### message
Send a message to the user's channel (Telegram, etc.).
```
message(content: str, channel: str = None, chat_id: str = None) -> str
```
Text only. To send images, use the Telegram Bot API via `exec`.

---

## Background Tasks

### spawn
Spawn a subagent to handle a task in the background.
```
spawn(task: str, label: str = None) -> str
```
The subagent completes the task and reports back when done. Use for long-running or isolated work.

---

## Scheduled Jobs (Cron)

### cron
Schedule recurring or one-time tasks.
```
cron(action: str, ...) -> str
```

**Actions:**
- `add` — schedule a new job
- `list` — list scheduled jobs
- `remove` — remove a job by ID

**Example — daily reminder at 09:00 Berlin time:**
```
cron(action="add", name="morning", message="Good morning!", cron_expr="0 9 * * *", tz="Europe/Berlin")
```

**Example — every 2 hours:**
```
cron(action="add", name="water", message="Drink water!", every_seconds=7200)
```

---

## Memory & Learning

### report_task
Signal meaningful events so you learn from them.
```
report_task(status: str, summary: str, details: str = None) -> str
```

**Status values:**
- `success` — task completed, approach worth remembering
- `failure` — task failed after 3+ attempts
- `correction` — user corrected your understanding
- `decision` — significant architectural or approach decision made
- `pattern` — same approach has worked multiple times
- `skill_created` — new reusable capability added to skills/

Not calling `report_task` means you don't learn. Call it.

---

## Skills

Skills are reusable capability packages stored in `~/.hive/workspace/skills/<name>/`.
Each skill has a `SKILL.md` describing what it does and how to use it.

To use a skill: `read_file("~/.hive/workspace/skills/<name>/SKILL.md")`

To create a skill:
1. `write_file("~/.hive/workspace/skills/<name>/SKILL.md", "...")` — describe the skill
2. Write any supporting scripts or data files alongside it
3. Call `report_task(status="skill_created", ...)`
