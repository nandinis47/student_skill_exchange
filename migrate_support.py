"""
Migration for Support Requests Table
Adds support_requests table to student_skill_exchange database.
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS support_requests (
        request_id   INT AUTO_INCREMENT PRIMARY KEY,
        student_id  INT NOT NULL,
        category    VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        status      ENUM('Open', 'In Progress', 'Resolved') DEFAULT 'Open',
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    print("+ Table support_requests created successfully.")

    cur.close()
    conn.close()
    print("[SUCCESS] Migration completed successfully!")
except Exception as e:
    print(f"[ERROR] Error running migration: {e}")
