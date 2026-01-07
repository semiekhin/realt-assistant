"""
Работа с базой данных SQLite
"""
import sqlite3
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import json

from config import DB_PATH
from db.models import Property, PropertyFile, User


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            state TEXT DEFAULT '',
            state_data TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            developer TEXT,
            completion_date TEXT,
            price_min INTEGER,
            price_max INTEGER,
            price_per_sqm_min INTEGER,
            price_per_sqm_max INTEGER,
            apartment_types TEXT,
            area_min REAL,
            area_max REAL,
            payment_options TEXT,
            installment_terms TEXT,
            mortgage_info TEXT,
            installment_min_pv REAL,
            installment_max_months INTEGER,
            installment_markup REAL,
            commission TEXT,
            description TEXT,
            features TEXT,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS property_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER,
            user_id INTEGER NOT NULL,
            file_id TEXT,
            file_name TEXT,
            file_type TEXT,
            file_path TEXT,
            extracted_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (property_id) REFERENCES properties(id),
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[DB] Initialized: {DB_PATH}")


# === Users ===

def get_or_create_user(telegram_id: int, username: str = "", 
                       first_name: str = "", last_name: str = "") -> User:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    
    if row:
        user = User(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"] or "",
            first_name=row["first_name"] or "",
            last_name=row["last_name"] or "",
            state=row["state"] or "",
            state_data=row["state_data"] or "",
            created_at=row["created_at"]
        )
    else:
        cursor.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, username, first_name, last_name))
        conn.commit()
        
        user = User(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
    
    conn.close()
    return user


def update_user_state(telegram_id: int, state: str, state_data: dict = None):
    conn = get_connection()
    cursor = conn.cursor()
    data_json = json.dumps(state_data or {}, ensure_ascii=False)
    cursor.execute("UPDATE users SET state = ?, state_data = ? WHERE telegram_id = ?", (state, data_json, telegram_id))
    conn.commit()
    conn.close()


def get_user_state(telegram_id: int) -> tuple[str, dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT state, state_data FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        state = row["state"] or ""
        data = json.loads(row["state_data"]) if row["state_data"] else {}
        return state, data
    return "", {}


def clear_user_state(telegram_id: int):
    update_user_state(telegram_id, "", {})


# === Properties ===

def create_property(user_id: int, name: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO properties (user_id, name) VALUES (?, ?)", (user_id, name))
    property_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return property_id


def update_property(property_id: int, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()
    set_parts = []
    values = []
    for key, value in kwargs.items():
        set_parts.append(f"{key} = ?")
        values.append(value)
    set_parts.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(property_id)
    query = f"UPDATE properties SET {', '.join(set_parts)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()


def get_property(property_id: int) -> Optional[Property]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _row_to_property(row)
    return None


def get_user_properties(user_id: int) -> List[Property]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_property(row) for row in rows]


def delete_property(property_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM property_files WHERE property_id = ?", (property_id,))
    cursor.execute("DELETE FROM properties WHERE id = ?", (property_id,))
    conn.commit()
    conn.close()


def _row_to_property(row) -> Property:
    return Property(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"] or "",
        address=row["address"] or "",
        developer=row["developer"] or "",
        completion_date=row["completion_date"] or "",
        price_min=row["price_min"],
        price_max=row["price_max"],
        price_per_sqm_min=row["price_per_sqm_min"],
        price_per_sqm_max=row["price_per_sqm_max"],
        apartment_types=row["apartment_types"] or "",
        area_min=row["area_min"],
        area_max=row["area_max"],
        payment_options=row["payment_options"] or "",
        installment_terms=row["installment_terms"] or "",
        mortgage_info=row["mortgage_info"] or "",
        installment_min_pv=row["installment_min_pv"],
        installment_max_months=row["installment_max_months"],
        installment_markup=row["installment_markup"],
        commission=row["commission"] or "",
        description=row["description"] or "",
        features=row["features"] or "",
        raw_data=row["raw_data"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )


# === Property Files ===

def save_property_file(user_id: int, property_id: int, file_id: str,
                       file_name: str, file_type: str, file_path: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO property_files (user_id, property_id, file_id, file_name, file_type, file_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, property_id, file_id, file_name, file_type, file_path))
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id


def update_file_extracted_text(file_id: int, text: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE property_files SET extracted_text = ? WHERE id = ?", (text, file_id))
    conn.commit()
    conn.close()


def get_property_files(property_id: int) -> List[PropertyFile]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM property_files WHERE property_id = ?", (property_id,))
    rows = cursor.fetchall()
    conn.close()
    return [PropertyFile(
        id=row["id"],
        property_id=row["property_id"],
        user_id=row["user_id"],
        file_id=row["file_id"] or "",
        file_name=row["file_name"] or "",
        file_type=row["file_type"] or "",
        file_path=row["file_path"] or "",
        extracted_text=row["extracted_text"] or "",
        created_at=row["created_at"]
    ) for row in rows]


def get_pending_files(user_id: int) -> List[PropertyFile]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM property_files 
        WHERE user_id = ? AND property_id IS NULL
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [PropertyFile(
        id=row["id"],
        property_id=row["property_id"],
        user_id=row["user_id"],
        file_id=row["file_id"] or "",
        file_name=row["file_name"] or "",
        file_type=row["file_type"] or "",
        file_path=row["file_path"] or "",
        extracted_text=row["extracted_text"] or "",
        created_at=row["created_at"]
    ) for row in rows]


def get_file_by_id(file_id: int) -> Optional[PropertyFile]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM property_files WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return PropertyFile(
            id=row["id"],
            property_id=row["property_id"],
            user_id=row["user_id"],
            file_id=row["file_id"] or "",
            file_name=row["file_name"] or "",
            file_type=row["file_type"] or "",
            file_path=row["file_path"] or "",
            extracted_text=row["extracted_text"] or "",
            created_at=row["created_at"]
        )
    return None


def attach_files_to_property(user_id: int, property_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE property_files 
        SET property_id = ? 
        WHERE user_id = ? AND property_id IS NULL
    """, (property_id, user_id))
    conn.commit()
    conn.close()


init_db()
