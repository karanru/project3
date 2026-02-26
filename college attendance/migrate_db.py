import sqlite3
import os

db_path = os.path.join('instance', 'attendance.db')
if not os.path.exists(db_path):
    db_path = 'attendance.db'

print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE leave_request ADD COLUMN request_type VARCHAR(20) DEFAULT 'Leave'")
    conn.commit()
    print("Column 'request_type' added successfully.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Column 'request_type' already exists.")
    else:
        print(f"Error: {e}")
finally:
    conn.close()
