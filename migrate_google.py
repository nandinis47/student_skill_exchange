"""Add google_sub column to students for Google OAuth linking"""
import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'student_skill_exchange')
)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE students ADD COLUMN google_sub VARCHAR(128) DEFAULT NULL UNIQUE")
    conn.commit()
    print("✓ Column added: students.google_sub")
except Exception as e:
    print(f"~ Already exists or error: {e}")

# Index for fast Google sub lookups
try:
    cur.execute("CREATE INDEX idx_google_sub ON students(google_sub)")
    conn.commit()
    print("✓ Index created: idx_google_sub")
except Exception as e:
    print(f"~ Index: {e}")

cur.close()
conn.close()
print("Done")
