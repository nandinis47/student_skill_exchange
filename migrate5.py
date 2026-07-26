"""Migration 5 — Pin/Mute/Archive/Block/Notifications/Forward"""
import mysql.connector
conn = mysql.connector.connect(host='localhost',user='root',password='system',database='student_skill_exchange')
cur = conn.cursor()

# Chat preferences (pin, mute, archive, block)
cur.execute("""
CREATE TABLE IF NOT EXISTS chat_prefs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT NOT NULL,
    other_id    INT NOT NULL,
    is_pinned   TINYINT(1) DEFAULT 0,
    is_muted    TINYINT(1) DEFAULT 0,
    is_archived TINYINT(1) DEFAULT 0,
    is_blocked  TINYINT(1) DEFAULT 0,
    blocked_at  DATETIME DEFAULT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (other_id)   REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uq_pref (student_id, other_id)
)"""); conn.commit(); print('+ Table: chat_prefs')

# Notifications table
cur.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    notif_id    INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT NOT NULL,
    type        ENUM('message','group_msg','exchange','badge','mention','system') DEFAULT 'message',
    title       VARCHAR(200),
    body        TEXT,
    icon        VARCHAR(10) DEFAULT '🔔',
    is_read     TINYINT(1) DEFAULT 0,
    action_url  VARCHAR(300),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
)"""); conn.commit(); print('+ Table: notifications')

# Add forward_from to messages
for col, defn in [
    ('forward_from_id', 'INT DEFAULT NULL'),
    ('is_forwarded',    'TINYINT(1) DEFAULT 0'),
    ('is_pinned',       'TINYINT(1) DEFAULT 0'),
    ('voice_duration',  'INT DEFAULT NULL'),
]:
    try:
        cur.execute(f'ALTER TABLE messages ADD COLUMN {col} {defn}')
        conn.commit(); print(f'+ Column: messages.{col}')
    except: print(f'~ {col} exists')

# Add voice_note to message_type ENUM
try:
    cur.execute("""ALTER TABLE messages MODIFY COLUMN message_type
        ENUM('text','image','video','audio','document','link','sticker','poll','location','voice_note')
        DEFAULT 'text'""")
    conn.commit(); print('+ ENUM updated with voice_note')
except Exception as e: print(f'~ {e}')

# Group admin features
for col, defn in [
    ('who_can_send', "ENUM('all','admins_only') DEFAULT 'all'"),
    ('who_can_edit', "ENUM('all','admins_only') DEFAULT 'admins_only'"),
]:
    try:
        cur.execute(f'ALTER TABLE chat_groups ADD COLUMN {col} {defn}')
        conn.commit(); print(f'+ Column: chat_groups.{col}')
    except: print(f'~ {col} exists')

# Seed sample notifications
for sid in [1,2,3]:
    try:
        cur.execute("""INSERT INTO notifications (student_id,type,title,body,icon,action_url)
            VALUES (%s,'message','New message','You have a new message','💬','/messages.html')""", (sid,))
        conn.commit()
    except: pass
print('+ Sample notifications seeded')

cur.close(); conn.close()
print('Migration 5 complete!')
