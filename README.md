# Assistant Agent

An extensible, database‑agnostic chat agent powered by modern Large Language Models (LLMs). Based on langgraph.
The **Agent** class wraps all plumbing needed to spin up a Retrieval‑Augmented Generation (RAG) chatbot that keeps its history in SQL or NoSQL stores and enriches answers with vector search from **ChromaDB** or **Firebase Firestore**.

---

## ✨ Features

| Capability                 | Details                                                              |
| -------------------------- | -------------------------------------------------------------------  |
| **LLM Provider**           | OpenAI (`gpt‑4o‑mini` by default), more coming soon 🚀               |
| **State Persistence**      | PostgreSQL · MySQL · SQLite · Firstore (NoSQL! not recommended)      |
| **Vector Store**           | ChromaDB · Firestore                                                 |
| **Stateless API**          | Conversation state is reconstructed from the DB via the `thread_id`  |
| **Plug‑and‑Play Config**   | All behaviour is driven by `assistant.agent_config.AgentConfig`      |
| **Environment Validation** | Startup safety check through `load_and_check_env()`                  |

---

## 📦 Requirements

* **Python ≥ 3.10**
* All Python dependencies listed in **`requirements.txt`**

```bash

# (optional) create a virtual env
python -m venv .venv && source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

---

## 🔧 Environment Variables

The agent refuses to start unless every mandatory variable is set.
Use a **`.env_vars`** file at the project root or export them in your shell.

```env
# Core credentials & keys
OPENAI_API_KEY=sk‑...
# === Logging ===
LANGSMITH_API_KEY=... 
# === Database (State + User) ===
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_DB=your_database

# === Vector DB ===
# add provider‑specific keys here
```

> **Tip:** The full list lives in `assistant/required_env_vars.txt`.

Run the pre‑flight checker manually:

```python
from assistant.utils.env_check import load_and_check_env
load_and_check_env()
```

### Database variable pattern

For SQL engines we follow the convention `{DBTYPE}_USER`, `{DBTYPE}_PASSWORD`, `{DBTYPE}_HOST`, `{DBTYPE}_DB`.

```env
# PostgreSQL example
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_DB=your_database
```

For **Firebase Firestore** you typically point `GOOGLE_APPLICATION_CREDENTIALS` to a service‑account JSON and let the agent handle vectorization automatically.

> You don’t have to call `load_and_check_env()` yourself – the Agent does so on first import. It’s shown here for completeness.

---

## 🗄️ Supported Databases

| Category   | Engines                                                      |
| ---------- | --------------------------------------------                 |
| Relational | **PostgreSQL**, **MySQL**, **SQLite**, **Firestore**         |
| Vector     | **ChromaDB**, **Firestore**                                  |

---

## 🚀 Quickstart

```python
from assistant.agent import Agent
from assistant.agent_config import AgentConfig
from assistant.utils.env_check import load_and_check_env

# 1 – validate environment (optional, will be done in agent as well)
load_and_check_env()

# 2 – load default config
agent_config = AgentConfig.as_default()

# 3 – spin up the agent (if no config provided it uses default)
agent = Agent(config=agent_config)

# 4 – chat!
content = {
    "msg": "Hallo, wie kann ich dir helfen?",
    "images": [], # optional
    "barcode": "4016249010201",  # optional
}
user = {"user_id": None, "thread_id": None}
response, thread_id = agent.chat(content=content, user=user)
print(response)
print(thread_id) # you can use it at the next message for move on with the conversation
```

---

## 📚 Tutorial: Building a Chat Session

Below is a minimal, end‑to‑end walkthrough that mirrors the inline examples in the source code’s docstrings.

### 1. Prepare your message

Every call to `agent.chat()` expects a **`content`** dict and a **`user`** dict.

```python
content = {
    "msg": "Hallo, wie kann ich dir helfen?",   # required
    "images": [],                                 # optional list of image bytes/paths
    "barcode": "4016249010201",                  # optional EAN/UPC codes for product lookup
}
user = {
    "user_id": None,    # supply your internal user id or leave None for anonymous
    "thread_id": None,   # None starts a new thread; otherwise reuse an existing id
}
```

### 2. First roundtrip

```python
response, thread_id = agent.chat(content=content, user=user)
print(response["response"])  # → Agent’s answer
print(thread_id)              # → e.g. "anon‑f6b2e2ab‑3f51‑4e23‑8ceb‑7d35c3d35b1a"
```

The **`thread_id`** is a composite key (`{user_id}-{uuid}`) and acts as the primary key for fetching past messages – the Agent itself is stateless.

### 3. Continue the conversation

```python
next_content = {"msg": "Erzähl mir mehr über RAG.", "images": []}
response, _ = agent.chat(content=next_content, user={"user_id": None, "thread_id": thread_id})
print(response["response"])
```

That’s it – the Agent stores each exchange in your configured database, so you can horizontally scale without sticky sessions.

---

## ⚙️ Configuration

`AgentConfig` is a dataclass‑style wrapper that can be initialised in three ways:

1. `AgentConfig.as_default()` – sensible production defaults.
2. `AgentConfig(**kwargs)` – fully programmatic.

Default JSON (as of July 2025):

```json
{
  "name": "DefaultAgent",
  "description": "This is a default agent configuration.",
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini",
  "user_db": "postgres",
  "checkpoint_type": "postgres",
  "rag_db": "chroma"
}
```

---

## 📈 Roadmap

internal currently hehe

---



## 📝 License

Distributed under the **MIT License**.  See `LICENSE` for more information.

---


