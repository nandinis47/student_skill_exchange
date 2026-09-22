"""
Migration for Admin Authorization & Overview Support
Adds is_admin column to students table and sets admin status for admin account.
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
    cur = conn.cursor(dictionary=True)

    # 1. Add is_admin column to students
    try:
        cur.execute("ALTER TABLE students ADD COLUMN is_admin TINYINT(1) DEFAULT 0")
        conn.commit()
        print("+ Column: students.is_admin added")
    except Exception as e:
        print(f"~ is_admin column check: {e}")

    # 2. Check if an admin user exists, or elevate/create an admin user
    cur.execute("SELECT * FROM students WHERE is_admin = 1")
    admin = cur.fetchone()

    if not admin:
        # Check if student with ID 1 or admin email exists
        cur.execute("SELECT * FROM students ORDER BY id ASC LIMIT 1")
        first_user = cur.fetchone()
        if first_user:
            cur.execute("UPDATE students SET is_admin = 1 WHERE id = %s", (first_user['id'],))
            conn.commit()
            print(f"+ Granted is_admin = 1 to user ID {first_user['id']} ({first_user['email']})")

    cur.close()
    conn.close()
    print("[SUCCESS] Admin migration completed successfully!")
except Exception as e:
    print(f"[ERROR] Migration failed: {e}")
