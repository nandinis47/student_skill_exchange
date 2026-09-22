"""
Migration for User Settings Table
Adds user_settings table to student_skill_exchange database.
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

    # Create user_settings table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        student_id             INT PRIMARY KEY,
        notif_requests        TINYINT(1) DEFAULT 1,
        notif_messages        TINYINT(1) DEFAULT 1,
        notif_sessions        TINYINT(1) DEFAULT 1,
        notif_smart_matches   TINYINT(1) DEFAULT 1,
        request_permissions   VARCHAR(30) DEFAULT 'everyone',
        profile_visibility    VARCHAR(30) DEFAULT 'public',
        session_duration      INT DEFAULT 60,
        session_availability  VARCHAR(50) DEFAULT 'anytime',
        theme                 VARCHAR(20) DEFAULT 'light',
        created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    print("+ Table user_settings created successfully.")

    cur.close()
    conn.close()
    print("[SUCCESS] Migration completed successfully!")
except Exception as e:
    print(f"[ERROR] Error running migration: {e}")
