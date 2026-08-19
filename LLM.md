# Archivist — London Pubs LLM Wiki Agent (fixed reference)

This is a corrected, re-structured version of the FastAPI "Archivist" backend.
It is a **small LLM agent** that runs locally against **Ollama**. The agent can
**read** the pub wiki (the "database") and **write new entries** to it by making
**Python tool calls** — it never touches the filesystem directly; it asks for a
tool by name, the server runs the matching Python function, and the result is
fed back to the model so it can decide what to do next.

The knowledge base follows the **Karpathy "LLM wiki" pattern**: a folder of
markdown files with YAML frontmatter, a master `index.md`, an ingest `log.md`,
and a `schema.md` that tells the agent how pages must be structured.

---

## 1. Folder structure

```
fix/
├── README.md               ← you are here
├── requirements.txt        ← Python dependencies for the backend
├── config/
│   └── config.yaml         ← all settings: models, routing, paths, ports
├── src/                    ← the Python package (run everything as `python -m src.*`)
│   ├── __init__.py
│   ├── main.py             ← FastAPI server: /health, /chat, /wiki, /search …
│   ├── chat.py             ← terminal chat client (easiest way to test the agent)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       ← loads config.yaml, resolves which model to use, path helpers
│   │   ├── search.py       ← SQLite FTS5 full-text index over the wiki (the searchable DB)
│   │   └── agent.py        ← THE AGENT LOOP: call model → parse tool calls → run → repeat
│   └── actions/
│       ├── __init__.py
│       └── handlers.py     ← the tools: wiki_read / wiki_write / wiki_search / … + profile_* stubs
└── vault/                  ← the wiki itself (the data)
    ├── schema.md           ← the "operating contract": how pub/area/concept pages must look
    ├── wiki/
    │   ├── index.md        ← master navigation + statistics (agent keeps this updated)
    │   └── log.md          ← chronological ledger of every ingest
    ├── raw/
    │   └── 2026-07-24-historic-pubs-in-london.md   ← an unstructured source to ingest
    └── profiles/           ← user profile pages (created by the handler you implement)
```

### How a request flows

```
you ──▶ src/main.py (/chat)  or  src/chat.py
            │
            ▼
     src/core/agent.py  run_agent_loop()
            │   builds the system prompt (schema + wiki index)
            │   asks the Ollama model what to do
            ▼
     model replies with one or more TOOL CALLS
            │
            ▼
     src/actions/handlers.py  runs the matching Python function
            │   (wiki_read reads a file, wiki_write saves a page,
            │    wiki_search queries the SQLite index in search.py …)
            ▼
     result string is fed back to the model → loop repeats
            │
            ▼
     model stops calling tools → final answer returned to you
```

**Native vs ReAct mode:** if the model advertises the `tools` capability, the
agent uses Ollama's native tool-calling. If it does not (common for very small
models), it falls back to **ReAct mode**, where the model asks for a tool by
printing `<action>name</action><params>{...}</params>` tags that `agent.py`
parses out of the plain-text reply. Same handlers either way.

---

## 2. What was broken, and what this version fixes

| # | Problem in the original | Fix in this version |
|---|--------------------------|----------------------|
| 1 | Files were flattened into one folder, but imports/paths were half-changed, so nothing lined up. | Restored the proper package layout: `src/core`, `src/actions`, `config/config.yaml`. Run with `python -m src.main`. |
| 2 | `config.index_path` / `log_path` pointed at `vault/index.md` (root), but the files live in `vault/wiki/`. The agent got an **empty wiki index** and `wiki_index()` crashed. | `config.py` now resolves them to `vault/wiki/index.md` and `vault/wiki/log.md`, matching `schema.md`. |
| 3 | Native tool-result messages had no `name`, so some Ollama builds ignored tool output and the agent looped. | `agent.py` now sends `{"role": "tool", "name": <tool>, "content": ...}`. |
| 4 | Routing sent ingest to a 32B remote model that most machines have not pulled. | `remote.enabled: false` in `config.yaml`, so remote routes safely fall back to `local.default`. |
| 5 | No dependency list; `ollama` / `pyyaml` may be missing. | Added `requirements.txt`. |

> Note: the original Flask app (`app.py` / `ai.py` / `data/`) is intentionally
> **not** part of this reference. That was a separate venue-data service and had
> its own unrelated bugs. This folder is only the Karpathy LLM-wiki agent.

---

## 3. How to run

From **inside the `fix/` folder** (the folder that contains `src/` and `config/`):

```bash
# 1. Install dependencies (use your virtual environment)
pip install -r requirements.txt

# 2. Make sure Ollama is running and you have pulled a tool-capable model.
#    Edit config/config.yaml -> models.local.default to match what you have.
ollama list
ollama pull qwen3:8b        # for example

# 3a. Easiest: talk to the agent in the terminal
python -m src.chat

# 3b. Or run the HTTP server
python -m src.main
#   then, in another terminal:
#   curl http://127.0.0.1:8420/health
#   curl -X POST http://127.0.0.1:8420/chat -H "Content-Type: application/json" \
#        -d '{"message":"Which pubs are in the wiki so far?"}'
```

**First things to try** (these exercise reading *and* writing the wiki):
- "List the wiki pages." → agent calls `wiki_list` / `wiki_index`.
- "Ingest `raw/2026-07-24-historic-pubs-in-london.md` into the wiki." → agent
  should `read_file` the source, then `wiki_write` new pub pages and update
  `index.md` / `log.md` (see the Ingest Instructions in `agent.py`).

---

## 4. Your task: the profile handlers

The agent should also be able to **read and write user profiles**, the same way
it reads and writes wiki pages. Three handlers have been **wired up but left
blank** for you in `src/actions/handlers.py`:

- `profile_read(name)` — return a profile page's text
- `profile_write(name, content)` — create/overwrite a profile page
- `profile_list()` — list all profiles

They are already registered in `handlers` / `descriptions` and already have JSON
schemas in `agent.py` (`TOOL_SCHEMAS`), so the agent **already knows they
exist** — you only need to implement the bodies. Store each profile as a
markdown file under `vault/profiles/` using `self.config.profiles_path`.

**How:** copy the body of the matching wiki handler and adapt it —
`profile_read` ⟵ `wiki_read`, `profile_write` ⟵ `wiki_write`,
`profile_list` ⟵ `list_dir`. Use `_is_safe_profile_path` (already provided) so
the model can never write outside `vault/profiles/`.

---

## 5. Comprehension check — fill this in and send it back

> Answer in your own words. Short is fine, but be specific and refer to the
> actual files/functions. This is to confirm you understand *why* the wiring
> works, not just that it runs.

**A. Trace the fix.**
1. What exact path did `config.index_path` resolve to in the broken version, and
   what does it resolve to now? Name one concrete symptom the bug caused.
   _Your answer:_ index.md and log.md to live INSIDE the wiki/ folder (see vault/schema.md
     section 1 — the schema mandates that layout). The original code looked for
    them at the vault root (vault/index.md), which does not exist, so the agent
    was handed an empty wiki index and the wiki_index() tool crashed. This was already fixed in the version given. 

2. In `main.py` and `chat.py`, why must you run the app with `python -m src.main`
   from the `fix/` folder rather than `python src/main.py` from inside `src/`?
   (Hint: look at the `import` lines and where `config/config.yaml` is loaded from.)
   _Your answer:_ Whatever folder your run from becomes the base folder and where its starts from. 

**B. The agent loop (`src/core/agent.py`).**
3. Describe one full iteration of `run_agent_loop`: what goes into `client.chat`,
   how the reply is turned into `ParsedAction`s, and what decides whether the
   loop continues or returns.
   _Your answer:_  During the first loop Ollama evalautes the prompt. 
   Which includes descriptions of actions or tools. Ollama can reply with either
   a request to run tools (actions) or just a final answer. If ollama replies 
   with a request to run tools the loop will run the tools. The results of the tool calls
   are added to the converstation with ollama and ollama is called again repeating the loop.

4. What is the difference between **native** mode and **ReAct** mode, and how
   does `detect_mode` choose? Why does a "small agent" make ReAct mode matter?
   _Your answer:_  Native can call tools and reAct can't. ReAct small agents can reduce hallucinations.

5. Why does the tool result need `"name": action.name`? Predict what you would
   observe if you deleted that key again.
   _Your answer:_  In agent.py in the run agent loop (the main loop) when tools are called we need to 
   give the results of the tools back to ollama in the conversation. If we don't name what tool was called
   with the results ollama will not know what were talking about. Ollama would be unable to answer the questions 
   correctly. 

**C. Reading vs. the database (`src/core/search.py`).**
6. There are two ways the agent can find information in the wiki: `wiki_read`
   and `wiki_search`. What does each actually do under the hood, and when would
   the agent prefer one over the other?
   _Your answer:_  In the handlers.py wiki read reads a wiki pagae. Wiki search 
   searches the wiki pages and calls search.py which creates a small database 
   of all of the wiki pages and enables full text indexing and searching.

7. After the agent calls `wiki_write` to add a new pub page, what has to happen
   for that page to show up in future `wiki_search` results? Which line makes
   that happen?
   _Your answer:_ The handlers.py wiki write function must call the wiki search update function 
   so that the full text index of pages gets updated with the changed wiki text. 

**D. Safety.**
8. Give one concrete `path` value that `_is_safe_wiki_path` would **reject**, and
   explain what attack/mistake that check is preventing.
   _Your answer:_ An attack can occur by using something like ../../etc/passwd.
   The path.resolve call trys to solve it. 

**E. Your implementation (the profile handlers).**
9. List **every** place you had to touch to make `profile_write` work end-to-end,
   and say what each change is responsible for. (There are more than one — think
   about the handler, the registry, and the schema.)
   _Your answer:_ It's in handlers.py it had to be added to the tool map and the the tool descriptions map. It also had to be added as a function. In agent.py it had to be added to the tools schema 
   so that the ollama would know how to call it. 

10. **(Harder)** You ask the agent, *"Save a profile for Alice who likes
    riverside pubs, then recommend her a pub from the wiki."* Walk through the
    sequence of tool calls you'd expect the agent to make, in order, and name the
    handler behind each one.
    _Your answer:_  First a profile read for Alice to see if she has an account.(Profile Read) Next step 
    would be a creating a or updatea profile (Profile write). After that a wiki search with the term river
    side (wiki search). 

11. **(Debugging)** A classmate says: "The agent reads pages fine but never
    writes anything — it just describes what it *would* write." Give **two**
    different plausible causes (one about the model/mode, one about wiring or the
    prompt) and how you'd check each.
    _Your answer:_  In reAct mode it can't call tools which are needed for updated pages. The schemea should be included in the prompt and should be a valid schema and desciptive enough for ollama
    to understand. 
