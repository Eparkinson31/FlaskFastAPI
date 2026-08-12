"""
Archivist Agent Loop

The core reasoning loop that handles user messages, routes them through
the LLM, parses actions (via native tool calling or ReAct tags), executes
them, and iterates until a final response is produced.

This is the "small agent": each turn the LLM may emit one or more tool calls
(Python functions in handlers.py). We run them, feed the results back, and let
the model decide what to do next — read the wiki, search it, or write to it.
"""

import re
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import ollama

from src.core.config import Config

logger = logging.getLogger(__name__)

# --- ReAct Parser ---

ACTION_PATTERN = re.compile(
    r"<action>([\w]+)</action>\s*<params>(.*?)</params>",
    re.DOTALL,
)


@dataclass
class ParsedAction:
    name: str
    params: dict[str, Any]


def parse_react_response(text: str) -> tuple[str, list[ParsedAction]]:
    """Parse a ReAct-style response into prose and actions."""
    actions = []
    for match in ACTION_PATTERN.finditer(text):
        name = match.group(1)
        try:
            params = json.loads(match.group(2))
        except json.JSONDecodeError:
            params = {"raw": match.group(2).strip()}
        actions.append(ParsedAction(name=name, params=params))

    prose = ACTION_PATTERN.sub("", text).strip()
    return prose, actions


def parse_native_response(message) -> tuple[str, list[ParsedAction]]:
    """Parse a native tool-calling response from Ollama.

    The ollama library returns message objects with attributes,
    not plain dicts.
    """
    actions = []
    tool_calls = getattr(message, "tool_calls", None) or []
    for tc in tool_calls:
        fn = tc.function
        actions.append(ParsedAction(
            name=fn.name,
            params=fn.arguments if isinstance(fn.arguments, dict) else {},
        ))

    prose = getattr(message, "content", "") or ""
    return prose, actions


# --- Mode Detection ---

async def detect_mode(model: str, host: str, forced: str = "auto") -> str:
    """Determine whether to use native tool calling or ReAct.

    Small local models sometimes do not advertise the "tools" capability. When
    that happens we fall back to ReAct mode, where the model asks for tools by
    printing <action>/<params> tags that we parse out of its plain-text reply.
    """
    if forced != "auto":
        return forced

    try:
        client = ollama.AsyncClient(host=host)
        info = await client.show(model)
        # info may be a dict or object depending on ollama version
        caps = info.get("capabilities", []) if isinstance(info, dict) else getattr(info, "capabilities", [])
        if caps and "tools" in caps:
            logger.info(f"Model {model} supports native tool calling")
            return "native"
    except Exception as e:
        logger.warning(f"Could not detect capabilities for {model}: {e}")

    logger.info(f"Model {model} will use ReAct mode")
    return "react"


# --- Tool Schema Builder ---

# Proper JSON Schema definitions for each action so the model knows
# what parameters to pass.
TOOL_SCHEMAS: dict[str, dict] = {
    "wiki_read": {
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {"type": "string", "description": "Wiki page path, e.g. 'wiki/pubs/the-black-friar.md'"}
        },
    },
    "wiki_write": {
        "type": "object",
        "required": ["path", "content"],
        "properties": {
            "path": {"type": "string", "description": "Wiki page path to write"},
            "content": {"type": "string", "description": "Full markdown content including frontmatter"},
        },
    },
    "wiki_update": {
        "type": "object",
        "required": ["path", "section", "content"],
        "properties": {
            "path": {"type": "string", "description": "Wiki page path"},
            "section": {"type": "string", "description": "Section heading to update (without ##)"},
            "content": {"type": "string", "description": "New content for the section"},
        },
    },
    "wiki_search": {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results (default 5)"},
        },
    },
    "wiki_list": {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Filter by directory, e.g. 'wiki/pubs'"},
            "type": {"type": "string", "description": "Filter by page type, e.g. 'pub'"},
        },
    },
    "wiki_index": {
        "type": "object",
        "properties": {},
    },
    "read_file": {
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {"type": "string", "description": "File path relative to vault root"},
        },
    },
    "write_file": {
        "type": "object",
        "required": ["path", "content"],
        "properties": {
            "path": {"type": "string", "description": "Output file path (within outputs/)"},
            "content": {"type": "string", "description": "File content"},
        },
    },
    "list_dir": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: vault root)"},
        },
    },
    "run_python": {
        "type": "object",
        "required": ["code"],
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
        },
    },
    "draft_email": {
        "type": "object",
        "required": ["to", "subject", "body"],
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body text"},
        },
    },
    "render_md": {
        "type": "object",
        "required": ["filename", "content"],
        "properties": {
            "filename": {"type": "string", "description": "Output filename"},
            "content": {"type": "string", "description": "Markdown content"},
        },
    },
    "datetime_now": {
        "type": "object",
        "properties": {},
    },

    # --- Profile tools (STUDENT EXERCISE) ---
    # The schemas are wired up here so the model knows what arguments to send.
    # You implement the matching handlers in handlers.py.
    "profile_read": {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string", "description": "Profile name/slug, e.g. 'alice'"},
        },
    },
    "profile_write": {
        "type": "object",
        "required": ["name", "content"],
        "properties": {
            "name": {"type": "string", "description": "Profile name/slug"},
            "content": {"type": "string", "description": "Full markdown content for the profile page"},
        },
    },
    "profile_list": {
        "type": "object",
        "properties": {},
    },
}

# This merges the function descriptions from the handlers.py with the schemas above
# to create a tool list for the model 

def build_tools_list(descriptions: dict[str, str]) -> list[dict]:
    """Build Ollama-compatible tools list with proper JSON schemas."""
    tools = []
    for name, desc in descriptions.items():
        schema = TOOL_SCHEMAS.get(name, {"type": "object", "properties": {}})
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": schema,
            },
        })
    return tools


# --- System Prompt ---

def build_system_prompt(
    schema: str,
    wiki_index: str,
    mode: str,
    action_descriptions: dict[str, str],
) -> str:
    """Build the system prompt for the agent."""
    base = f"""You are Archivist, a personal wiki assistant. You maintain a
knowledge wiki and produce artifacts (documents, emails, scripts) on request.

## Wiki Schema
{schema}

## Current Wiki Index
{wiki_index}

## Guidelines
- Read the wiki before answering questions — your knowledge comes from the wiki.
- When you modify wiki pages, always update frontmatter timestamps.
- When producing documents or emails, check the wiki for relevant context first.
- Be concise in your responses. The human values efficiency.
- Use British English.
- If a question can be answered from the wiki, use wiki_search or wiki_read first.
- If the user asks about something not in the wiki, answer from general knowledge
  but suggest adding it to the wiki.

## Ingest Instructions
When the user asks to ingest a source:

1. Read the source using read_file().
2. Create new wiki pages using wiki_write() if they do not exist.
3. Update existing wiki pages using wiki_update().
4. Update index.md if new pages are added.
5. Append an entry to log.md.
6. Do NOT simply summarise the file.
7. Continue calling tools until the wiki has been updated.
8. Only then provide a summary of the changes made.
"""

    if mode == "react":
        actions_list = "\n".join(
            f"- {name} — {desc}"
            for name, desc in action_descriptions.items()
        )
        base += f"""
## Available Actions

To use an action, output it in this exact format:

<action>ACTION_NAME</action>
<params>{{"key": "value"}}</params>

After each action, you will receive the result and can continue.
Chain multiple actions as needed. When done, respond normally without tags.

Actions:
{actions_list}
"""

    return base


# --- Agent Loop ---

# Tells info about what happened in the agent loop, including the final text, actions taken, and model/mode used.
@dataclass
class AgentResponse:
    """The final response from the agent loop."""
    text: str
    actions_taken: list[dict] = field(default_factory=list)
    model_used: str = ""
    mode_used: str = ""
    iterations: int = 0

# The main call to have ollama evaluate a user message/prompt. 
# Ollama will return a response that may contain tool calls (actions) or just plain text.
# If Ollama returns response with tool calls (actions) we will execute those actions, 
# add the results to the conversation history(stored in messages) and call ollama again with the updated conversation history.
#if ollama returns a response without tool calls (actions) we will return the final response to the user in the form of an AgentResponse object.
async def run_agent_loop(
    user_message: str,
    config: Config,
    action_handlers: dict[str, Any],
    action_descriptions: dict[str, str],
    schema: str,
    wiki_index: str,
    conversation_history: list[dict] | None = None,
    task_type: str = "default",
) -> AgentResponse:
    """Execute the agent loop for a user message."""
    # Resolve model and host
    print(f"Resolving model route for task_type: {task_type}")
    route = config.resolve_model_route(task_type)
    model = route.model
    host = route.host
    print(f"Resolved model route: {model} @ {host}")
    if task_type == "wiki_ingest":
        model = "qwen3:32b-q4_K_M"
        print(f"override: {model} @ {host}")
    # Detect mode
    mode = await detect_mode(model, host, forced=config.llm.mode)
    logger.info(f"Using model={model}, mode={mode}")

    # Build system prompt
    system_prompt = build_system_prompt(
        schema=schema,
        wiki_index=wiki_index,
        mode=mode,
        action_descriptions=action_descriptions,
    )

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # Build tools list (native mode only)
    tools = build_tools_list(action_descriptions) if mode == "native" else None

    # Create client
    client = ollama.AsyncClient(host=host)

    actions_taken = []
    max_iterations = config.llm.max_iterations

    for iteration in range(max_iterations):
        logger.info(f"Agent loop iteration {iteration + 1}")

        # Call LLM the main loop 
        chatarguments = {
            "model": model,
            "messages": messages,
            "options": {"temperature": config.llm.temperature},
        }
        if tools:
            chatarguments["tools"] = tools

        response = await client.chat(**chatarguments)

        # The ollama library returns a ChatResponse object
        message = response.message

        # Parse response based on mode
        if mode == "native":
            prose, actions = parse_native_response(message)
        else:
            content = getattr(message, "content", "") or ""
            prose, actions = parse_react_response(content)

        # If no actions, we're done
        if not actions:
            final_text = getattr(message, "content", prose) or prose
            return AgentResponse(
                text=final_text,
                actions_taken=actions_taken,
                model_used=model,
                mode_used=mode,
                iterations=iteration + 1,
            )

        # Add assistant message to history
        # Convert to dict format for the messages list
        msg_dict = {"role": "assistant", "content": getattr(message, "content", "") or ""}
        if mode == "native" and hasattr(message, "tool_calls") and message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in message.tool_calls
            ]
        messages.append(msg_dict)

        # Execute tools and feed results back t
        for action in actions:
            handler = action_handlers.get(action.name)
            if handler is None:
                result = f"Error: Unknown action '{action.name}'"
                logger.warning(f"Unknown action: {action.name}")
            else:
                try:
                    result = await handler(**action.params)
                    logger.info(f"Action {action.name} succeeded")
                except TypeError as e:
                    # Parameter mismatch — try passing as single dict
                    try:
                        result = await handler(action.params)
                    except Exception:
                        result = f"Error: {action.name} got unexpected parameters: {e}"
                        logger.error(f"Action {action.name} param error: {e}")
                except Exception as e:
                    result = f"Error executing {action.name}: {e}"
                    logger.error(f"Action {action.name} failed: {e}")
            last_action = {
                "action": action.name,
                "params": action.params,
                "result_preview": str(result)[:300],
            }
            print(f"Action taken: {last_action}")
            actions_taken.append(last_action)

            # Feed result back to LLM
            if mode == "native":
                # FIX: include the tool "name" so Ollama can associate this
                # result with the call that produced it. Without it, some Ollama
                # builds silently ignore the tool output and the model loops or
                # hallucinates that nothing happened.
                messages.append({
                    "role": "tool",
                    "name": action.name,
                    "content": str(result),
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Result of {action.name}:\n{result}",
                })

    # Hit max iterations
    logger.warning(f"Hit max iterations ({max_iterations})")
    return AgentResponse(
        text="I've reached the maximum number of steps. Here's what I've done so far.",
        actions_taken=actions_taken,
        model_used=model,
        mode_used=mode,
        iterations=max_iterations,
    )
