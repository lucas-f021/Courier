# Courier

AI-powered productivity agent that connects your Gmail, Google Workspace, and Slack into a single conversational interface. Ask it to check your email, manage your calendar, search your Drive, and more — through Slack or a local web UI.

## Features

- **Gmail** — search, read, send emails, draft replies, poll for new emails automatically
- **Google Calendar** — check availability, create/update/delete events
- **Google Drive & Docs** — search files, read document contents
- **Google Meet** — pull meeting transcripts for follow-up context
- **Slack** — two-way conversations via @mentions and DMs (Socket Mode)
- **Web UI** — browser-based chat interface on `localhost:5000`
- **Triple AI Backend** — use Anthropic Claude, OpenAI GPT, or Ollama (local, free)
- **Semantic Memory** — ChromaDB vector search for context-aware responses
- **14 Built-in Tools** — the agent calls tools autonomously based on your request
- **C Base64 Decoder** — custom C library for decoding email bodies via ctypes

## Quickstart

### Prerequisites

- Python 3.10+
- GCC (for compiling the C decoder)
- A Google account

### 1. Clone and install

```bash
git clone https://github.com/lucas-f021/Courier.git
cd Courier/ai-agent
pip install -r requirements.txt
```

### 2. Compile the C decoder

**Windows:**
```bash
gcc -O2 -shared -o base64.dll base64.c
```

**Linux / macOS:**
```bash
gcc -O2 -shared -fPIC -o b64decode.so base64.c
```

### 3. Google Cloud setup (required)

This is the most involved step. You need a Google Cloud project with OAuth credentials.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services > Library** and enable:
   - **Gmail API** (required)
   - **Google Calendar API** (optional)
   - **Google Drive API** (optional)
   - **Google Docs API** (optional)
   - **Google Meet REST API** (optional)
4. Navigate to **APIs & Services > OAuth consent screen**
   - Choose **External** user type
   - Fill in the app name and your email
   - Add scopes: `gmail.modify`, and optionally `calendar`, `drive.readonly`, `documents.readonly`, `meetings.space.readonly`
   - Add your Google account as a test user
5. Navigate to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth client ID**
   - Application type: **Desktop app**
   - Download the JSON and save it as `credentials.json` in the `ai-agent/` directory

On first run, a browser window will open for OAuth authorization. This generates `token.json` automatically.

> **Note:** If you enable additional Google APIs later, delete `token.json` and re-run to reauthorize with the new scopes.

### 4. Choose an AI backend (pick one)

**Option A: Ollama (free, runs locally)**

Install [Ollama](https://ollama.com), then pull a model:
```bash
ollama pull qwen3.5:9b
```

In `main.py`, set:
```python
USE_LOCAL_MODEL = True
```

**Option B: OpenAI GPT (cloud API)**

Get an API key from [OpenAI](https://platform.openai.com/) and add it to your `.env`.

In `main.py`, set:
```python
USE_OPENAI_MODEL = True
```

**Option C: Anthropic Claude (cloud API)**

Get an API key from [Anthropic](https://console.anthropic.com/) and add it to your `.env`.

In `main.py`, set:
```python
USE_LOCAL_MODEL = False
USE_OPENAI_MODEL = False
```

### 5. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Only if using Claude | Anthropic API key |
| `OPENAI_API_KEY` | Only if using OpenAI | OpenAI API key |
| `OPENAI_MODEL` | No (defaults to `gpt-4o`) | OpenAI model name |
| `OLLAMA_BASE_URL` | No (defaults to `http://localhost:11434/v1`) | Ollama server URL |
| `OLLAMA_MODEL` | No (defaults to `qwen3.5:9b`) | Ollama model name |
| `SLACK_BOT_TOKEN` | Only if using Slack mode | Slack bot token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Only if using Slack mode | Slack app-level token (`xapp-...`) |
| `SLACK_CHANNEL_ID` | Only if using Slack mode | Default Slack channel for notifications |

### 6. Choose a UI mode

In `main.py`:

```python
USE_WEB_UI = False   # Slack mode (default)
USE_WEB_UI = True    # Web UI mode — opens browser chat at http://127.0.0.1:5000
```

**Slack mode** requires a Slack app with Socket Mode enabled. See [Slack setup](#slack-setup-optional) below.

**Web UI mode** requires no additional setup — just set the flag and run.

### 7. Run

```bash
cd ai-agent
python main.py
```

## Slack Setup (optional)

1. Create a new app at [api.slack.com/apps](https://api.slack.com/apps)
2. Enable **Socket Mode** (App Settings > Socket Mode) and generate an app-level token with `connections:write` scope
3. Add these **Bot Token Scopes** under OAuth & Permissions:
   - `channels:read`, `channels:history`, `chat:write`
   - `im:read`, `im:history`, `im:write`
   - `app_mentions:read`
4. Install the app to your workspace
5. Invite the bot to your channel: `/invite @YourBotName`
6. Copy the bot token and app token to your `.env`

## Tools

The agent has 14 tools it can call autonomously:

| Tool | Description |
|------|-------------|
| `search_emails` | Search Gmail by query |
| `read_email` | Read the full body of an email |
| `draft_reply` | Save an email reply as a draft |
| `send_email` | Send a new email immediately |
| `check_calendar` | List upcoming calendar events |
| `create_event` | Create a new calendar event |
| `update_event` | Modify an existing event |
| `delete_event` | Delete a calendar event |
| `check_availability` | Check free/busy time slots |
| `search_drive` | Search Google Drive by keyword |
| `read_doc` | Read a Google Doc's contents |
| `get_transcripts` | Fetch Google Meet transcripts |
| `post_to_slack` | Post a message to Slack |
| `set_reminder` | Set a timed reminder |

## Project Structure

```
ai-agent/
├── main.py                 # Entry point — config flags, polling loop
├── base64.c                # C Base64 decoder
├── Dockerfile
├── requirements.txt
├── .env.example
├── agent/
│   ├── ai_agent.py         # AI agent loop, 14 tools, triple backend
│   └── vector_memory.py    # ChromaDB semantic memory
├── integrations/
│   ├── gmail.py            # Gmail API + C decoder bridge
│   ├── calendar_client.py  # Google Calendar API
│   ├── drive_client.py     # Google Drive + Docs API
│   ├── meet_client.py      # Google Meet API
│   ├── slack_client.py     # Slack Web API helpers
│   └── slack_listener.py   # Slack Socket Mode listener
└── ui/
    └── web_server.py       # Flask web chat interface
```

## Docker

```bash
docker build -t courier .
docker run -it \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/token.json:/app/token.json \
  -v $(pwd)/.env:/app/.env \
  -p 5000:5000 \
  courier
```

> If using Ollama from inside Docker, set `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1` in your `.env`.

## How It Works

1. **Poll** — checks Gmail every 5 minutes for new emails
2. **Deduplicate** — skips already-processed emails (tracked in SQLite)
3. **Memory** — retrieves semantically similar past context from ChromaDB
4. **AI** — sends the email + context to Claude or Ollama with tool definitions
5. **Act** — the model calls tools (draft reply, check calendar, post to Slack, etc.)
6. **Listen** — simultaneously listens for Slack messages or web chat input
