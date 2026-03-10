# gui/database.py
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import threading


class Database:
    _local = threading.local()

    def __init__(self, db_name: str = "wg_manager.db"):
        self.db_name = db_name
        self._init_connection()

    def _init_connection(self):
        """Инициализирует соединение с БД для текущего потока"""
        self.conn = sqlite3.connect(
            self.db_name,
            check_same_thread=False,
            timeout=30.0
        )
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 0
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS ip_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            ips TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile_ip_lists (
            profile_id INTEGER NOT NULL,
            ip_list_id INTEGER NOT NULL,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (profile_id, ip_list_id),
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (ip_list_id) REFERENCES ip_lists(id) ON DELETE CASCADE
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS wg_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL UNIQUE,
            private_key TEXT DEFAULT '',
            address TEXT DEFAULT '10.7.0.18/32',
            dns TEXT DEFAULT '1.1.1.1',
            mtu TEXT DEFAULT '1420',
            public_key TEXT DEFAULT '',
            endpoint TEXT DEFAULT '',
            keepalive TEXT DEFAULT '21',
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            action TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS platforms_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS dns_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dns_name TEXT NOT NULL UNIQUE,
            servers TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            source_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_dns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            servers TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

    def create_profile(self, name: str) -> Optional[int]:
        try:
            self.cursor.execute("INSERT INTO profiles (name) VALUES (?)", (name,))
            profile_id = self.cursor.lastrowid
            self.cursor.execute("INSERT INTO wg_settings (profile_id) VALUES (?)", (profile_id,))
            self.log_action(profile_id, f"Создан профиль '{name}'")
            self.conn.commit()
            return profile_id
        except sqlite3.IntegrityError:
            return None

    def get_all_profiles(self) -> List[Tuple]:
        self.cursor.execute("SELECT id, name, created_at, updated_at, is_active FROM profiles ORDER BY updated_at DESC")
        return self.cursor.fetchall()

    def get_active_profile(self) -> Optional[Tuple]:
        self.cursor.execute("SELECT id, name FROM profiles WHERE is_active = 1")
        return self.cursor.fetchone()

    def set_active_profile(self, profile_id: int):
        self.cursor.execute("UPDATE profiles SET is_active = 0")
        self.cursor.execute("UPDATE profiles SET is_active = 1, updated_at = ? WHERE id = ?",
                           (datetime.now().isoformat(), profile_id))
        self.conn.commit()

    def delete_profile(self, profile_id: int):
        self.cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        self.conn.commit()

    def rename_profile(self, profile_id: int, new_name: str) -> bool:
        try:
            self.cursor.execute("UPDATE profiles SET name = ?, updated_at = ? WHERE id = ?",
                               (new_name, datetime.now().isoformat(), profile_id))
            self.log_action(profile_id, f"Переименован в '{new_name}'")
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def create_ip_list(self, name: str, ips: str) -> Optional[int]:
        try:
            self.cursor.execute("INSERT INTO ip_lists (name, ips) VALUES (?, ?)", (name, ips))
            list_id = self.cursor.lastrowid
            self.conn.commit()
            return list_id
        except sqlite3.IntegrityError:
            return None

    def update_ip_list(self, list_id: int, name: str, ips: str):
        self.cursor.execute("UPDATE ip_lists SET name = ?, ips = ?, updated_at = ? WHERE id = ?",
                           (name, ips, datetime.now().isoformat(), list_id))
        self.conn.commit()

    def delete_ip_list(self, list_id: int):
        self.cursor.execute("DELETE FROM ip_lists WHERE id = ?", (list_id,))
        self.conn.commit()

    def delete_ip_list_by_name(self, name: str):
        self.cursor.execute("DELETE FROM ip_lists WHERE name = ?", (name,))
        self.conn.commit()

    def get_all_ip_lists(self) -> List[Tuple]:
        self.cursor.execute("SELECT id, name, ips, created_at FROM ip_lists ORDER BY name")
        return self.cursor.fetchall()

    def get_ip_list(self, list_id: int) -> Optional[Tuple]:
        self.cursor.execute("SELECT id, name, ips FROM ip_lists WHERE id = ?", (list_id,))
        return self.cursor.fetchone()

    def get_ip_list_by_name(self, name: str) -> Optional[Tuple]:
        self.cursor.execute("SELECT id, name, ips FROM ip_lists WHERE name = ?", (name,))
        return self.cursor.fetchone()

    def add_ip_list_to_profile(self, profile_id: int, list_id: int) -> bool:
        try:
            self.cursor.execute("INSERT INTO profile_ip_lists (profile_id, ip_list_id) VALUES (?, ?)",
                               (profile_id, list_id))
            self.cursor.execute("UPDATE profiles SET updated_at = ? WHERE id = ?",
                               (datetime.now().isoformat(), profile_id))
            self.log_action(profile_id, f"Добавлен IP список ID {list_id}")
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_ip_list_from_profile(self, profile_id: int, list_id: int):
        self.cursor.execute("DELETE FROM profile_ip_lists WHERE profile_id = ? AND ip_list_id = ?",
                           (profile_id, list_id))
        self.cursor.execute("UPDATE profiles SET updated_at = ? WHERE id = ?",
                           (datetime.now().isoformat(), profile_id))
        self.log_action(profile_id, f"Удалён IP список ID {list_id}")
        self.conn.commit()

    def get_profile_ip_lists(self, profile_id: int) -> List[Tuple]:
        self.cursor.execute("""
        SELECT il.id, il.name, il.ips
        FROM ip_lists il
        JOIN profile_ip_lists pil ON il.id = pil.ip_list_id
        WHERE pil.profile_id = ?
        ORDER BY il.name
        """, (profile_id,))
        return self.cursor.fetchall()

    def get_available_ip_lists_for_profile(self, profile_id: int) -> List[Tuple]:
        self.cursor.execute("""
        SELECT id, name, ips FROM ip_lists
        WHERE id NOT IN (
            SELECT ip_list_id FROM profile_ip_lists WHERE profile_id = ?
        )
        ORDER BY name
        """, (profile_id,))
        return self.cursor.fetchall()

    def get_wg_settings(self, profile_id: int) -> Optional[Tuple]:
        self.cursor.execute("SELECT * FROM wg_settings WHERE profile_id = ?", (profile_id,))
        return self.cursor.fetchone()

    def save_wg_settings(self, profile_id: int, settings: Tuple):
        self.cursor.execute("""
        UPDATE wg_settings SET
            private_key = ?, address = ?, dns = ?, mtu = ?,
            public_key = ?, endpoint = ?, keepalive = ?
        WHERE profile_id = ?
        """, (*settings, profile_id))
        self.cursor.execute("UPDATE profiles SET updated_at = ? WHERE id = ?",
                           (datetime.now().isoformat(), profile_id))
        self.log_action(profile_id, "Обновлены настройки WG")
        self.conn.commit()

    def log_action(self, profile_id: Optional[int], action: str):
        self.cursor.execute("INSERT INTO history (profile_id, action) VALUES (?, ?)",
                           (profile_id, action))
        self.conn.commit()

    def get_history(self, profile_id: Optional[int] = None, limit: int = 50) -> List[Tuple]:
        if profile_id:
            self.cursor.execute("""
            SELECT action, timestamp FROM history
            WHERE profile_id = ?
            ORDER BY timestamp DESC LIMIT ?
            """, (profile_id, limit))
        else:
            self.cursor.execute("""
            SELECT action, timestamp FROM history
            ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        return self.cursor.fetchall()

    def clear_history(self, profile_id: int):
        self.cursor.execute("DELETE FROM history WHERE profile_id = ?", (profile_id,))
        self.conn.commit()

    def save_platforms_to_cache(self, platforms: Dict[str, str]):
        now = datetime.now().isoformat()
        self.cursor.execute("DELETE FROM platforms_cache")
        for name, url in platforms.items():
            self.cursor.execute(
                "INSERT OR REPLACE INTO platforms_cache (service_name, url, updated_at) VALUES (?, ?, ?)",
                (name, url, now)
            )
        self.cursor.execute("INSERT OR REPLACE INTO cache_meta (key, value, updated_at) VALUES (?, ?, ?)",
                           ('platforms_cached', now, now))
        self.conn.commit()

    def get_platforms_from_cache(self, max_age_hours: int = 24) -> Optional[Dict[str, str]]:
        meta = self.cursor.execute(
            "SELECT value, updated_at FROM cache_meta WHERE key = 'platforms_cached'"
        ).fetchone()
        if not meta:
            return None
        cached_time = datetime.fromisoformat(meta[1])
        if datetime.now() - cached_time > __import__('datetime').timedelta(hours=max_age_hours):
            return None
        rows = self.cursor.execute("SELECT service_name, url FROM platforms_cache").fetchall()
        return {name: url for name, url in rows}

    def clear_platforms_cache(self):
        self.cursor.execute("DELETE FROM platforms_cache")
        self.cursor.execute("DELETE FROM cache_meta WHERE key = 'platforms_cached'")
        self.conn.commit()

    def save_dns_to_cache(self, dns_db: Dict[str, List[str]]):
        now = datetime.now().isoformat()
        self.cursor.execute("DELETE FROM dns_cache")
        for name, servers in dns_db.items():
            self.cursor.execute(
                "INSERT OR REPLACE INTO dns_cache (dns_name, servers, updated_at) VALUES (?, ?, ?)",
                (name, ','.join(servers), now)
            )
        self.cursor.execute("INSERT OR REPLACE INTO cache_meta (key, value, updated_at) VALUES (?, ?, ?)",
                           ('dns_cached', now, now))
        self.conn.commit()

    def get_dns_from_cache(self, max_age_hours: int = 24) -> Optional[Dict[str, List[str]]]:
        meta = self.cursor.execute(
            "SELECT value, updated_at FROM cache_meta WHERE key = 'dns_cached'"
        ).fetchone()
        if not meta:
            return None
        cached_time = datetime.fromisoformat(meta[1])
        if datetime.now() - cached_time > __import__('datetime').timedelta(hours=max_age_hours):
            return None
        rows = self.cursor.execute("SELECT dns_name, servers FROM dns_cache").fetchall()
        return {name: servers.split(',') for name, servers in rows}

    def clear_dns_cache(self):
        self.cursor.execute("DELETE FROM dns_cache")
        self.cursor.execute("DELETE FROM cache_meta WHERE key = 'dns_cached'")
        self.conn.commit()

    def save_custom_service(self, name: str, source: str, source_type: str) -> bool:
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO custom_services (name, source, source_type) VALUES (?, ?, ?)",
                (name, source, source_type)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_all_custom_services(self) -> Dict[str, Dict[str, str]]:
        rows = self.cursor.execute("SELECT name, source, source_type FROM custom_services").fetchall()
        return {row[0]: {'source': row[1], 'type': row[2]} for row in rows}

    def delete_custom_service(self, name: str):
        self.cursor.execute("DELETE FROM custom_services WHERE name = ?", (name,))
        self.conn.commit()

    def save_custom_dns(self, name: str, servers: List[str]) -> bool:
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO custom_dns (name, servers) VALUES (?, ?)",
                (name, ','.join(servers))
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_all_custom_dns(self) -> Dict[str, List[str]]:
        rows = self.cursor.execute("SELECT name, servers FROM custom_dns").fetchall()
        return {row[0]: row[1].split(',') for row in rows}

    def delete_custom_dns(self, name: str):
        self.cursor.execute("DELETE FROM custom_dns WHERE name = ?", (name,))
        self.conn.commit()

    def set_setting(self, key: str, value: str):
        now = datetime.now().isoformat()
        self.cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now)
        )
        self.conn.commit()

    def get_setting(self, key: str, default: str = '') -> str:
        row = self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def close(self):
        try:
            self.conn.close()
        except:
            pass