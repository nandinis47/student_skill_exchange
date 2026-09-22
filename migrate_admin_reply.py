"""
Migration for Admin Reply column on support_requests table.
"""
import os
import mysql.connector

try:
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "student_skill_exchange")
    )
    cur = conn.cursor()

    try:
        cur.execute("ALTER TABLE support_requests ADD COLUMN admin_reply TEXT DEFAULT NULL")
        conn.commit()
        print("+ Column: support_requests.admin_reply added")
    except Exception as e:
        print(f"~ admin_reply column check: {e}")

    cur.close()
    conn.close()
    print("[SUCCESS] Support tickets migration completed successfully!")
except Exception as e:
    print(f"[ERROR] Migration failed: {e}")
