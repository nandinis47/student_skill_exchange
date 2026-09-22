import os
import mysql.connector
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'student_skill_exchange')
)
cur = conn.cursor()

# Check current ENUM
cur.execute("SHOW COLUMNS FROM messages LIKE 'message_type'")
row = cur.fetchone()
print('Current:', row[1])  # column type

# Update to include all types
cur.execute("""ALTER TABLE messages MODIFY COLUMN message_type
    ENUM('text','image','video','audio','document','link','sticker','poll','location','voice_note')
    DEFAULT 'text'""")
conn.commit()
print('Updated ENUM to include: video, sticker, location, poll, voice_note')

cur.close()
conn.close()
