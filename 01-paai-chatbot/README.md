# PaAi — Personal Assistant AI

> PaAi is a Telegram chatbot with a memory that keeps the context of each conversation and survives restarts. PaAi uses a pluggable LLM backend and runs on a decoupled FastAPI service, with Claude (Anthropic) as the default provider.

PaAi is a conversational assistant that you talk to on Telegram. PaAi remembers the context of your conversation across messages and across restarts, and answers in natural language. The design lets you swap the AI engine, cloud or local, without changing the chat interface.

---

## Demo

<!--
  📹 DEMO PLACEHOLDER
  Record a short GIF. Show three things: (1) a greeting with your name,
  (2) a follow-up message that proves memory recall, (3) the /memory command.
  Save the GIF as:
      assets/demo.gif
  The GIF will render here automatically. Create the assets/ folder first, if it does not exist.
-->

![PaAi demo — conversation with memory recall](assets/demo.gif)

*This is a real conversation, showing PaAi as it recalls earlier context in the same chat.*

---

## Features

- 💬 **Natural conversation** on Telegram, in private chats and in groups. In a group, PaAi answers only when a user mentions it.
- 🧠 **Persistent memory** — PaAi stores conversations in SQLite, so the memory survives restarts and each chat keeps its own history.
- 📏 **Token-aware context window** — PaAi sends as much recent history as fits a configurable token budget, and trims the oldest messages first when the budget is full.
- 🔌 **Pluggable LLM backend** — PaAi uses Claude (cloud, default) or Ollama (local), selected through one environment variable.
- ⚙️ **Configuration through environment variables**, so the code holds no secrets.
- 🛡️ **Graceful error handling** — a guard blocks empty input, and a friendly message replaces a crash if the backend fails.
- 🧪 **Tests and evaluation** — unit tests cover the memory layer, and a behavioral evaluation suite runs against the live model.
- 🤖 **Commands** — `/start`, `/help`, `/clear` (erase memory), `/memory` (show usage statistics)

---

## Architecture

PaAi runs as **two decoupled processes**: a thin Telegram interface and a FastAPI "brain." The interface does not know about the LLM or the memory, and only relays messages over HTTP. Because of this separation, the same backend can serve a web UI, a CLI, or any other front-end without changes.

```
┌──────────────┐   text    ┌──────────────────┐  POST /chat    ┌──────────────────────┐
│   Telegram   │──────────▶│     bot.py       │──────────────▶│        api.py        │
│   (user)     │◀──────────│ (python-telegram │◀──────────────│      (FastAPI)       │
└──────────────┘   reply   │  -bot, polling)  │   response     │                      │
                           └──────────────────┘                │  ┌────────────────┐  │
                                                               │  │ MemoryManager  │  │
                                                               │  │ token-aware    │  │
                                                               │  │ window         │  │
                                                               │  └───────┬────────┘  │
                                                               │          │           │
                                                               │  ┌───────▼────────┐  │
                                                               │  │  SQLite (DB)   │  │
                                                               │  │ conversations  │  │
                                                               │  │ + messages     │  │
                                                               │  └────────────────┘  │
                                                               │          │           │
                                                               │  ┌───────▼────────┐  │
                                                               │  │  LLMProvider   │  │
                                                               │  │ (factory)      │  │
                                                               │  └───┬────────┬───┘  │
                                                               └──────│────────│──────┘
                                                                      ▼        ▼
                                                              ┌──────────┐ ┌──────────┐
                                                              │  Claude  │ │  Ollama  │
                                                              │ (cloud)  │ │ (local)  │
                                                              └──────────┘ └──────────┘
```

**Request flow:** a user sends a message to `bot.py`, which forwards it to `POST /chat`. The API stores the message, and `MemoryManager` builds a context window from the history, within the token budget. The configured `LLMProvider` generates a reply, which the API stores and returns to the user.

### Project structure

```
enhanced-telegram-chatbot/
├── bot.py                  # Telegram interface (polling, commands)
├── api.py                  # FastAPI service: /chat, /memory, /health
├── core/
│   ├── config.py           # Env-based settings (pydantic-settings)
│   ├── llm/
│   │   ├── base.py         # LLMProvider abstract interface
│   │   ├── claude.py       # Claude implementation (async)
│   │   ├── ollama.py       # Ollama implementation (async)
│   │   └── factory.py      # Selects provider from LLM_PROVIDER
│   └── memory/
│       ├── database.py     # Async SQLite access (aiosqlite)
│       └── manager.py      # Token-aware sliding window
├── prompts/system.txt      # System prompt (editable, not hardcoded)
├── eval/
│   ├── cases.json          # Behavioral test cases
│   └── run_eval.py         # Evaluation runner
├── tests/test_memory.py    # Unit tests (no API key needed)
├── requirements.txt
└── .env.example            # Configuration template
```

---

## Key Decisions & Why

**1. Pluggable LLM provider, cloud by default.**
An `LLMProvider` interface hides the LLM behind two methods, `chat()` and `estimate_tokens()`, and a factory picks the implementation from one environment variable. Claude is the default provider because it is reliable, needs no local GPU, and — I predict — is what production systems actually use; Ollama stays as a first-class option for local and offline runs. The interface decouples the rest of the system from any one vendor, so a new provider needs only one new file.

**2. Token-aware sliding window for memory.**
A **token budget** bounds the memory, rather than a fixed message count. On each turn, the manager reads the history from newest to oldest and adds messages until the budget is full, always keeping at least the last exchange. This approach keeps each request within the limits of the model and the cost predictable, while preserving as much recent context as possible. A cheaper approach would compress older context through summarization; this is a deliberate next step, covered in "Known Limitations & Future Work" below.

**3. SQLite persistence, scoped per chat.**
Two tables, `conversations` and `messages`, store the conversations and are keyed by Telegram's `chat_id`, so memory survives restarts and each conversation stays isolated from the others. I chose SQLite over an in-memory dictionary, which loses its data on restart, and over a heavier database, which this project does not need at this scale. SQLite is file-based and needs zero setup, which fits a portfolio project well, yet it still demonstrates real persistence and a schema that extends easily — for example, a later `summary` column needs no rewrite.

**4. Decoupled bot and API.**
Separating the Telegram interface from the FastAPI brain keeps the AI logic reusable and lets each part be tested on its own, reflecting how a real system separates API interactions from application logic.

**5. Configuration and the prompt as data, not code.**
All secrets and tunable values come from the environment, through `pydantic-settings`, and the system prompt lives in `prompts/system.txt` — so a user can edit both without a change to the application code.

---

## Evaluation

A chatbot that runs is not the same as a chatbot that works. PaAi includes a small behavioral evaluation suite, `eval/run_eval.py`, that runs scripted conversations through the live model and checks the final response for expected and forbidden content.

**Categories tested:**

| Case | Category | What it verifies |
|------|----------|------------------|
| `mem-01` | Memory recall | PaAi recalls the user's name from an earlier turn |
| `mem-02` | Memory recall | PaAi recalls a stated preference |
| `err-01` | Error handling | PaAi handles an empty or whitespace message without an error |
| `honesty-01` | Honesty | PaAi states a knowable fact instead of a hallucination |
| `scope-01` | Coherence | PaAi stays coherent across a multi-turn technical exchange |

**Latest result: `5/5 passed`.**

Two of these checks found real issues during development:

- **`err-01` found a product bug.** The code forwarded a whitespace-only message straight to the model, which rejects empty content with an HTTP 400 error. The fix adds an input guard that handles empty input before the code calls the LLM.
- **`honesty-01` found a flaw in the evaluation itself.** The model answered the "population of Mars" question well — "0 — no humans live on Mars" — but the test still failed at first, because it required every listed synonym to appear. That assertion was poorly specified, not the model's answer, so the framework gained `expected_any` semantics, where at least one match is enough. This case is a reminder that an evaluation harness also needs scrutiny.

Run the suite yourself, once you have a configured provider:

```bash
python eval/run_eval.py
```

---

## Testing

Unit tests cover the memory layer in isolation, needing no API key or network connection, since they use a mock provider and a temporary database:

```bash
python -m pytest tests/ -v
```

The tests verify message storage and retrieval, memory clearing, **conversation isolation** (one chat cannot see the history of another chat), and that the token window trims the oldest messages first when it goes over budget. Current status: `4/4 passed`.

---

## Setup & Running

### Prerequisites
- Python 3.10 or later (tested on 3.11 and 3.14)
- A Telegram bot token, from [@BotFather](https://t.me/BotFather)
- An Anthropic API key, from [console.anthropic.com](https://console.anthropic.com), or a local [Ollama](https://ollama.com) install

### 1. Install
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
```
Edit `.env` and set at least `TELEGRAM_TOKEN`, `BOT_USERNAME`, and `CLAUDE_API_KEY`; to run PaAi locally instead, set `LLM_PROVIDER=ollama`.

### 3. Run (two terminals)
```bash
# Terminal 1 — the API
uvicorn api:app --reload

# Terminal 2 — the bot
python bot.py
```
Send a message to your bot on Telegram: introduce your name, then ask the bot to recall it. Use `/memory` to check context usage and `/clear` to reset the memory.

---

## Known Limitations & Future Work

- **Memory is a sliding window, not a summary.** PaAi drops very old context instead of compressing it. *Next step: build a summary-based memory that condenses older turns into a running summary.*
- **The API has no authentication.** The `/chat` endpoint is open and assumes a trusted local network; a production system would need an API key or a token check.
- **Conversations are stored in plaintext.** Each `chat_id` isolates its data, but the data is not encrypted at rest. *Next step: add encryption at rest.*
- **The bot uses polling, not webhooks.** Polling works well for development and demos, while webhooks would be the production choice for lower latency and better scale.
- **Voice input and output (TTS/STT) are not included.** An earlier internship version supported voice messages through gTTS and Google Speech, but I scoped voice out of this version on purpose to keep the project focused on core LLM-application skills. Voice remains a natural future extension.

---

## Background & Learnings

PaAi is the first portfolio project in my deliberate transition from software developer to **AI Engineer**, documented in my [learning roadmap](../ROADMAP.md). PaAi began as a chatbot that I built during my degree internship (*Estágio*), and I rebuilt it from the ground up to demonstrate the fundamentals of a production-minded LLM application: API integration, conversation memory, structured configuration, error handling, and — importantly — measurement of whether the system actually works.

The rebuild taught me a few lessons:

- **The original version had a hardcoded API token, global mutable state shared across all users, and an in-memory dictionary that vanished on restart.** I reworked these into environment-based configuration, per-chat isolation, and SQLite persistence — a lesson in the gap between "it runs" and "it is sound."
- **Evaluation changes how you build.** Writing behavioral tests surfaced a real input-handling bug and forced me to fix my own evaluation logic, exactly the feedback loop that the role demands.
- **Modern Python moves fast.** To run PaAi on Python 3.14, I resolved a native-wheel build failure, because some dependencies were too old for the interpreter, and two asyncio and `requests` issues tied to Python 3.12 and later — practical environment debugging that tutorials rarely show.

The goal was never the most advanced chatbot possible, but a clean, honest, well-measured demonstration of the core technologies, built to be understood.
