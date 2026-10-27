"""
Database Connector Module for DataPulse.
Provides read-only access to source databases, dynamic schema discovery,
safe parameterized querying, and extensible interfaces for MySQL/PostgreSQL.
"""
from abc import ABC, abstractmethod
import os
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class BaseDatabaseConnector(ABC):
    """Abstract base class defining database connection and schema discovery interface."""

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Test if the connection can be established. Returns (is_connected, message)."""
        pass

    @abstractmethod
    def discover_schema(self) -> List[Dict[str, Any]]:
        """
        Discovers tables, columns, data types, primary keys, and row counts dynamically.
        Returns list of table dictionaries:
        [{
            "table_name": str,
            "columns": [{"name": str, "type": str, "nullable": bool, "pk": bool}],
            "row_count": int
        }]
        """
        pass

    @abstractmethod
    def fetch_sample_records(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch sample records safely with parameterized identifiers."""
        pass


class SQLiteConnector(BaseDatabaseConnector):
    """
    Safe read-only SQLite connector.
    Guarantees no modifications to the source database.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).resolve()

    def _get_read_only_connection(self) -> sqlite3.Connection:
        """Opens database connection in URI read-only mode to prevent any writes."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found at path: {self.db_path}")

        # SQLite URI mode for strict read-only access
        uri = f"file:{urllib.parse.quote(str(self.db_path))}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def test_connection(self) -> Tuple[bool, str]:
        """Validates file presence and attempts read-only connection."""
        if not self.db_path.exists():
            return False, f"File does not exist: {self.db_path}"
        try:
            conn = self._get_read_only_connection()
            cur = conn.cursor()
            cur.execute("SELECT sqlite_version()")
            ver = cur.fetchone()[0]
            conn.close()
            return True, f"Connected to SQLite {ver} (Read-Only Mode)"
        except sqlite3.OperationalError as e:
            return False, f"SQLite operational error: {str(e)}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def discover_schema(self) -> List[Dict[str, Any]]:
        """
        Dynamically inspects sqlite_master and PRAGMA table_info.
        Never hardcodes table names. Safely quotes identifiers.
        """
        conn = self._get_read_only_connection()
        cur = conn.cursor()
        tables_meta = []

        try:
            # Query user tables (ignoring internal sqlite_* tables)
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            table_names = [row[0] for row in cur.fetchall()]

            for tbl in table_names:
                # Safely escape table name for PRAGMA / queries using brackets
                safe_table_name = tbl.replace("]", "]]")
                cur.execute(f"PRAGMA table_info([{safe_table_name}])")
                col_rows = cur.fetchall()

                columns = []
                for c in col_rows:
                    columns.append({
                        "name": str(c["name"]),
                        "type": str(c["type"]) if c["type"] else "TEXT",
                        "nullable": not bool(c["notnull"]),
                        "pk": bool(c["pk"])
                    })

                # Fetch row count safely
                try:
                    cur.execute(f"SELECT COUNT(*) FROM [{safe_table_name}]")
                    cnt = cur.fetchone()[0]
                except Exception:
                    cnt = 0

                tables_meta.append({
                    "table_name": tbl,
                    "columns": columns,
                    "row_count": cnt
                })

        finally:
            conn.close()

        return tables_meta

    def fetch_sample_records(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches up to `limit` records safely using bracket quoting.
        Returns list of row dicts.
        """
        conn = self._get_read_only_connection()
        cur = conn.cursor()
        try:
            safe_table_name = table_name.replace("]", "]]")
            cur.execute(f"SELECT * FROM [{safe_table_name}] LIMIT ?", (max(1, min(limit, 500)),))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise RuntimeError(f"Error fetching records from table '{table_name}': {str(e)}")
        finally:
            conn.close()


class ExtensionDatabaseConnector(BaseDatabaseConnector):
    """
    Extensible connector placeholder for enterprise relational databases (MySQL, PostgreSQL).
    Enables future plug-in integrations without code refactoring.
    """

    def __init__(self, db_type: str, connection_uri: Optional[str] = None):
        self.db_type = db_type
        self.connection_uri = connection_uri

    def test_connection(self) -> Tuple[bool, str]:
        return False, f"{self.db_type.upper()} connector extension point available. Configure credentials in enterprise settings."

    def discover_schema(self) -> List[Dict[str, Any]]:
        raise NotImplementedError(f"{self.db_type} schema discovery extension point.")

    def fetch_sample_records(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        raise NotImplementedError(f"{self.db_type} sample extraction extension point.")
