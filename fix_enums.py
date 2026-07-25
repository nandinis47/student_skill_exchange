import mysql.connector
conn = mysql.connector.connect(
    host='localhost', user='root', password='system',
    database='student_skill_exchange'
)
cur = conn.cursor()

# Fix messages.message_type ENUM to include sticker, poll, location
cur.execute("""
ALTER TABLE messages
MODIFY COLUMN message_type
  ENUM('text','image','video','audio','document','link','sticker','poll','location')
  DEFAULT 'text'
""")
conn.commit()
print("Fixed messages.message_type ENUM")

# Also fix location columns if not present
for col, defn in [
    ('location_lat', 'DECIMAL(10,8)'),
    ('location_lng', 'DECIMAL(11,8)'),
    ('reply_to_id',  'INT DEFAULT NULL'),
    ('is_deleted',   'TINYINT(1) DEFAULT 0'),
    ('edited_at',    'DATETIME DEFAULT NULL'),
]:
    try:
        cur.execute(f'ALTER TABLE messages ADD COLUMN {col} {defn}')
        conn.commit()
        print(f'  + {col}')
    except:
        print(f'  ~ {col} exists')

cur.close()
conn.close()
print("Done")
