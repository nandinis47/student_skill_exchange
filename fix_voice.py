import mysql.connector
conn = mysql.connector.connect(
    host='localhost', user='root', password='system',
    database='student_skill_exchange'
)
cur = conn.cursor()
# Extend file_url to MEDIUMTEXT so audio base64 won't truncate
cur.execute("ALTER TABLE messages MODIFY COLUMN file_url MEDIUMTEXT")
conn.commit()
print("✓ messages.file_url → MEDIUMTEXT")
cur.close()
conn.close()
