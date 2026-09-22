"""Add google_sub column to students for Google OAuth linking"""
import mysql.connector

conn = mysql.connector.connect(
    host='localhost', user='root', password='system',
    database='student_skill_exchange'
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
