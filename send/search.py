"""
Wiki Search Index (SQLite FTS5)

Maintains a full-text search index over all wiki markdown files.
Rebuilds on startup, watches for changes, and provides search queries.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime

import yaml

logger = logging.getLogger(__name__)


class WikiSearch:
    """Full-text search over wiki markdown files using SQLite FTS5."""

    def __init__(self, db_path: str | Path, wiki_path: str | Path):
        self.db_path = Path(db_path)
        self.wiki_path = Path(wiki_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Create the FTS5 virtual table if it doesn't exist."""
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS wiki_pages
            USING fts5(
                path,
                title,
                type,
                tags,
                content,
                updated,
                tokenize='trigram'
            );

            CREATE TABLE IF NOT EXISTS page_meta (
                path TEXT PRIMARY KEY,
                mtime REAL,
                hash TEXT
            );
        """)
        self.conn.commit()

    def rebuild(self):
        """Full rebuild of the search index from wiki files."""
        logger.info("Rebuilding wiki search index...")
        self.conn.execute("DELETE FROM wiki_pages")
        self.conn.execute("DELETE FROM page_meta")

        count = 0
        for md_file in self.wiki_path.rglob("*.md"):
            rel_path = str(md_file.relative_to(self.wiki_path.parent))
            self._index_file(md_file, rel_path)
            count += 1

        self.conn.commit()
        logger.info(f"Indexed {count} wiki pages")

    def _index_file(self, file_path: Path, rel_path: str):
        """Index a single markdown file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return

        # Parse YAML frontmatter
        title, page_type, tags, updated = "", "", "", ""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict):
                        title = fm.get("title", "")
                        page_type = fm.get("type", "")
                        tags = " ".join(fm.get("tags", []))
                        updated = str(fm.get("updated", ""))
                except yaml.YAMLError:
                    pass
                content = parts[2]  # Body without frontmatter

        mtime = file_path.stat().st_mtime

        # Upsert: delete old entry if exists, then insert
        self.conn.execute("DELETE FROM wiki_pages WHERE path = ?", (rel_path,))
        self.conn.execute(
            "INSERT INTO wiki_pages (path, title, type, tags, content, updated) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rel_path, title, page_type, tags, content, updated),
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO page_meta (path, mtime) VALUES (?, ?)",
            (rel_path, mtime),
        )

    def update_if_changed(self, file_path: Path):
        """Re-index a file only if it has changed since last index."""
        rel_path = str(file_path.relative_to(self.wiki_path.parent))
        current_mtime = file_path.stat().st_mtime

        row = self.conn.execute(
            "SELECT mtime FROM page_meta WHERE path = ?", (rel_path,)
        ).fetchone()

        if row is None or row["mtime"] < current_mtime:
            self._index_file(file_path, rel_path)
            self.conn.commit()
            return True
        return False

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search wiki pages, return matches with snippets.

        Args:
            query: Search query (FTS5 syntax supported)
            limit: Maximum results

        Returns:
            List of {path, title, type, snippet, updated}
        """
        try:
            rows = self.conn.execute(
                """
                SELECT path, title, type, updated,
                       snippet(wiki_pages, 4, '>>>', '<<<', '...', 40) as snippet
                FROM wiki_pages
                WHERE wiki_pages MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError as e:
            # If FTS5 query syntax is invalid, try a simple contains
            logger.warning(f"FTS5 query failed, trying simple match: {e}")
            rows = self.conn.execute(
                """
                SELECT path, title, type, updated,
                       substr(content, 1, 200) as snippet
                FROM wiki_pages
                WHERE content LIKE ?
                ORDER BY updated DESC
                LIMIT ?
                """,
                (f"%{query}%", limit),
            ).fetchall()

        return [dict(row) for row in rows]

    def list_pages(
        self,
        directory: str | None = None,
        page_type: str | None = None,
    ) -> list[dict]:
        """List wiki pages, optionally filtered.

        Args:
            directory: Filter by directory (e.g., "wiki/projects")
            page_type: Filter by type (e.g., "project")

        Returns:
            List of {path, title, type, updated}
        """
        query = "SELECT path, title, type, updated FROM wiki_pages WHERE 1=1"
        params: list = []

        if directory:
            query += " AND path LIKE ?"
            params.append(f"{directory}%")

        if page_type:
            query += " AND type = ?"
            params.append(page_type)

        query += " ORDER BY updated DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self.conn.close()
