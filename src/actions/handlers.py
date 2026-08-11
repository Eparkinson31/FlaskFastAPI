"""
Wiki Action Handlers

Each handler is an async function that takes keyword arguments (from the LLM's
action params) and returns a string result that gets fed back to the LLM.

These are the "Python tool calls" the small agent makes. The agent never
touches the filesystem directly — it asks for a tool by name, we run the
matching method here, and hand the string result back to the model.
"""

import json
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from src.core.config import Config
from src.core.search import WikiSearch

logger = logging.getLogger(__name__)

# Functions that implement tool calls

class ActionRegistry:
    """Registry of all available action handlers."""

    def __init__(self, config: Config, search: WikiSearch):
        self.config = config
        self.search = search

# tool map 
    @property
    def handlers(self) -> dict:
        """Map of action names to handler functions."""
        return {
            "wiki_read": self.wiki_read,
            "wiki_write": self.wiki_write,
            "wiki_update": self.wiki_update,
            "wiki_search": self.wiki_search,
            "wiki_list": self.wiki_list,
            "wiki_index": self.wiki_index,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_dir": self.list_dir,
            "run_python": self.run_python,
            "draft_email": self.draft_email,
            "render_md": self.render_md,
            "datetime_now": self.datetime_now,
            # --- Profile tools (STUDENT EXERCISE) ---
            "profile_read": self.profile_read,
            "profile_write": self.profile_write,
            "profile_list": self.profile_list,
        }

# tool descriptions map
    @property
    def descriptions(self) -> dict:
        """Human-readable descriptions for each action."""
        return {
            "wiki_read": "Read a wiki page by path (e.g., 'wiki/pubs/the-black-friar.md')",
            "wiki_write": "Create or overwrite a wiki page. Params: path, content",
            "wiki_update": "Update a section of an existing wiki page. Params: path, section, content",
            "wiki_search": "Full-text search across wiki pages. Params: query, limit?",
            "wiki_list": "List wiki pages. Params: directory?, type?",
            "wiki_index": "Read the current wiki index",
            "read_file": "Read any file in the vault. Params: path",
            "write_file": "Write a file to outputs/. Params: path, content",
            "list_dir": "List directory contents. Params: path",
            "run_python": "Execute Python code in a sandbox. Params: code",
            "draft_email": "Draft an email. Params: to, subject, body",
            "render_md": "Save formatted markdown to outputs/. Params: filename, content",
            "datetime_now": "Get the current date and time",
            # --- Profile tools (STUDENT EXERCISE) ---
            "profile_read": "Read a user profile by name. Params: name",
            "profile_write": "Create or overwrite a user profile. Params: name, content",
            "profile_list": "List all user profiles",
        }

    # --- Wiki Operations ---

    async def wiki_read(self, path: str) -> str:
        """Read a wiki page."""
        full_path = self.config.vault_path / path
        if not full_path.exists():
            return f"Error: Page not found at {path}"
        if not self._is_safe_path(full_path):
            return "Error: Path outside vault"
        return full_path.read_text(encoding="utf-8")

    async def wiki_write(self, path: str, content: str) -> str:
        """Write a wiki page (create or overwrite)."""
        full_path = self.config.vault_path / path
        if not self._is_safe_wiki_path(full_path):
            return "Error: Can only write to wiki/ directory"

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

        # Re-index the updated file
        # Updates the wiki search database and reindexes the file.
        self.search.update_if_changed(full_path)

        return f"Written: {path} ({len(content)} chars)"

    async def wiki_update(self, path: str, section: str, content: str) -> str:
        """Update a specific section of a wiki page."""
        full_path = self.config.vault_path / path
        if not full_path.exists():
            return f"Error: Page not found at {path}"
        if not self._is_safe_wiki_path(full_path):
            return "Error: Can only write to wiki/ directory"

        existing = full_path.read_text(encoding="utf-8")

        # Find the section header and replace its content
        # Simple approach: find ## Section Header and replace until next ## or EOF
        import re
        pattern = rf"(## {re.escape(section)}\n)(.*?)(?=\n## |\Z)"
        match = re.search(pattern, existing, re.DOTALL)

        if match:
            updated = existing[:match.start(2)] + content + existing[match.end(2):]
            full_path.write_text(updated, encoding="utf-8")
            self.search.update_if_changed(full_path)
            return f"Updated section '{section}' in {path}"
        else:
            return f"Error: Section '{section}' not found in {path}"

    async def wiki_search(self, query: str, limit: int = 5) -> str:
        """Search wiki pages."""
        results = self.search.search(query, limit=limit)
        if not results:
            return "No results found."
        return json.dumps(results, indent=2, default=str)

    async def wiki_list(self, directory: str = None, type: str = None) -> str:
        """List wiki pages."""
        results = self.search.list_pages(directory=directory, page_type=type)
        if not results:
            return "No pages found."
        return json.dumps(results, indent=2, default=str)

    async def wiki_index(self) -> str:
        """Read the wiki index."""
        return self.config.index_path.read_text(encoding="utf-8")

    # --- File Operations ---

    async def read_file(self, path: str) -> str:
        """Read any file in the vault."""
        full_path = self.config.vault_path / path
        if not self._is_safe_path(full_path):
            return "Error: Path outside vault"
        if not full_path.exists():
            return f"Error: File not found at {path}"
        try:
            return full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: {path} is a binary file, cannot read as text"

    async def write_file(self, path: str, content: str) -> str:
        """Write a file to outputs/."""
        full_path = self.config.outputs_path / path
        if not self._is_safe_output_path(full_path):
            return "Error: Can only write to outputs/ directory"

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"Written: outputs/{path} ({len(content)} chars)"

    async def list_dir(self, path: str = ".") -> str:
        """List directory contents."""
        full_path = self.config.vault_path / path
        if not self._is_safe_path(full_path):
            return "Error: Path outside vault"
        if not full_path.is_dir():
            return f"Error: {path} is not a directory"

        entries = []
        for item in sorted(full_path.iterdir()):
            prefix = "d" if item.is_dir() else "f"
            entries.append(f"[{prefix}] {item.name}")
        return "\n".join(entries) if entries else "(empty directory)"

    # --- Code Execution ---

    async def run_python(self, code: str) -> str:
        """Execute Python code in a sandboxed subprocess."""
        try:
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.config.outputs_path),
            )
            output = ""
            if result.stdout:
                output += f"stdout:\n{result.stdout}\n"
            if result.stderr:
                output += f"stderr:\n{result.stderr}\n"
            if result.returncode != 0:
                output += f"Exit code: {result.returncode}\n"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Script timed out (30s limit)"
        except Exception as e:
            return f"Error: {e}"

    # --- Document Generation ---

    async def draft_email(self, to: str, subject: str, body: str) -> str:
        """Draft an email and save to outputs/emails/."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{subject[:30].replace(' ', '_')}.md"
        full_path = self.config.outputs_path / "emails" / filename

        content = f"""---
to: {to}
subject: {subject}
drafted: {datetime.now().isoformat()}
status: draft
---

{body}
"""
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"Email draft saved: outputs/emails/{filename}"

    async def render_md(self, filename: str, content: str) -> str:
        """Save formatted markdown to outputs/."""
        full_path = self.config.outputs_path / "docs" / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"Markdown saved: outputs/docs/{filename}"

    # --- Utility ---

    async def datetime_now(self) -> str:
        """Get current date and time."""
        return datetime.now().isoformat()

    # ------------------------------------------------------------------
    # --- Profile Operations (STUDENT EXERCISE) ---
    #
    # These three handlers are already WIRED UP for you:
    #   * registered in `handlers` and `descriptions` above, and
    #   * given JSON schemas in agent.py (TOOL_SCHEMAS).
    # The bodies are intentionally left blank. Your job is to implement them so
    # the agent can read and write user profiles, exactly the way it reads and
    # writes wiki pages.
    #
    # Store each profile as a markdown file under vault/profiles/, e.g.
    #   vault/profiles/alice.md
    # Use `self.config.profiles_path` for that folder.
    #
    # HOW TO DO IT: copy the body of the matching wiki handler and adapt it.
    #   profile_read   <- model on wiki_read()  (read a file, return its text)
    #   profile_write  <- model on wiki_write() (mkdir parents, write the file)
    #   profile_list   <- model on list_dir()   (list files in profiles_path)
    #
    # Think about: safety (see _is_safe_profile_path below), what to return when
    # the profile does not exist, and the exact string you return to the model.
    # ------------------------------------------------------------------

    async def profile_read(self, name: str) -> str: 
        """Read a user profile page by name (e.g. 'alice')."""
        full_path = self.config.profiles_path / f"{name}.json"
        if not self._is_safe_profile_path(full_path):
            return "Error: Path outside vault"
        if not full_path.exists():
            return f"Error: Profile not found for {name}"
        try:
            return full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: Profile for {name} is a binary file, cannot read as text"


    async def profile_write(self, name: str, content: str) -> str:
        """Create or overwrite a user profile page. Params: name, content."""
        full_path = self.config.profiles_path / f"{name}.json"
        if not self._is_safe_profile_path(full_path):
            return "Error: Path outside vault"
        full_path.write_text(content, encoding="utf-8")
        return f"Written: profiles/{name}.json"


    async def profile_list(self) -> str:
        """List all user profiles."""
        full_path = self.config.profiles_path
        if not full_path.is_dir():
            return "No profiles found."

        entries = []
        for item in sorted(full_path.iterdir()):
            if item.is_file() and item.suffix == ".json":
                entries.append(item.stem)
        return "\n".join(entries) if entries else "No profiles found."

    
    # --- Path Safety ---
    #making sure all of the files that Ollama can request with tools are in the vault folder.

    def _is_safe_path(self, path: Path) -> bool:
        """Check that a path is within the vault."""
        try:
            path.resolve().relative_to(self.config.vault_path.resolve())
            return True
        except ValueError:
            return False

    def _is_safe_wiki_path(self, path: Path) -> bool:
        """Check that a path is within wiki/."""
        try:
            path.resolve().relative_to(
                (self.config.vault_path / "wiki").resolve()
            )
            return True
        except ValueError:
            return False

    def _is_safe_output_path(self, path: Path) -> bool:
        """Check that a path is within outputs/."""
        try:
            path.resolve().relative_to(self.config.outputs_path.resolve())
            return True
        except ValueError:
            return False

    def _is_safe_profile_path(self, path: Path) -> bool:
        """Check that a path is within profiles/.

        Provided for the profile handlers above. Use it in profile_write (and
        profile_read if you like) so the model can never write outside
        vault/profiles/.
        """
        try:
            path.resolve().relative_to(self.config.profiles_path.resolve())
            return True
        except ValueError:
            return False
