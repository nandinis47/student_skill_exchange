"""
Migration for Feedback Table
Adds feedback table to student_skill_exchange database.
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
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id   INT AUTO_INCREMENT PRIMARY KEY,
        student_id    INT NOT NULL,
        rating        INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
        category      VARCHAR(100) NOT NULL,
        message       TEXT NOT NULL,
        allow_contact TINYINT(1) DEFAULT 0,
        status        ENUM('Open', 'In Progress', 'Resolved') DEFAULT 'Open',
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    print("+ Table feedback created successfully.")

    cur.close()
    conn.close()
    print("[SUCCESS] Migration completed successfully!")
except Exception as e:
    print(f"[ERROR] Error running migration: {e}")
