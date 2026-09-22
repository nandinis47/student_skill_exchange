import os
import mysql.connector
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'student_skill_exchange')
)
cur = conn.cursor()
# Extend file_url to MEDIUMTEXT so audio base64 won't truncate
cur.execute("ALTER TABLE messages MODIFY COLUMN file_url MEDIUMTEXT")
conn.commit()
print("✓ messages.file_url → MEDIUMTEXT")
cur.close()
conn.close()
