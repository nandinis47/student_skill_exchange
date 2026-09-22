"""
Migration 4 — Groups, Profile Pictures, Message enhancements
"""
import os
import mysql.connector, datetime

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'student_skill_exchange')
)
cur = conn.cursor()

# ── 1. Profile picture & avatar columns on students ──────────
for col, defn in [
    ('profile_pic',  'VARCHAR(500) DEFAULT NULL'),
    ('avatar_key',   'VARCHAR(50) DEFAULT NULL'),
    ('cover_color',  "VARCHAR(20) DEFAULT '#1a73e8'"),
]:
    try:
        cur.execute(f'ALTER TABLE students ADD COLUMN {col} {defn}')
        conn.commit(); print(f'+ Column: students.{col}')
    except: print(f'~ {col} exists')

# ── 2. Groups table ───────────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS chat_groups (
    group_id    INT AUTO_INCREMENT PRIMARY KEY,
    group_name  VARCHAR(100) NOT NULL,
    description TEXT,
    group_icon  VARCHAR(500) DEFAULT NULL,
    created_by  INT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES students(id) ON DELETE CASCADE
)""")
conn.commit(); print('+ Table: chat_groups')

# ── 3. Group members ──────────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS group_members (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    group_id   INT NOT NULL,
    student_id INT NOT NULL,
    role       ENUM('admin','member') DEFAULT 'member',
    joined_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id)   REFERENCES chat_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uq_gm (group_id, student_id)
)""")
conn.commit(); print('+ Table: group_members')

# ── 4. Group messages ─────────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS group_messages (
    msg_id       INT AUTO_INCREMENT PRIMARY KEY,
    group_id     INT NOT NULL,
    sender_id    INT NOT NULL,
    message      TEXT,
    message_type ENUM('text','image','video','audio','document','link','sticker','poll','location') DEFAULT 'text',
    file_url     VARCHAR(500),
    file_name    VARCHAR(255),
    poll_data    JSON,
    timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id)  REFERENCES chat_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES students(id) ON DELETE CASCADE
)""")
conn.commit(); print('+ Table: group_messages')

# ── 5. Enhance messages table ─────────────────────────────────
for col, defn in [
    ('reply_to_id',  'INT DEFAULT NULL'),
    ('is_deleted',   'TINYINT(1) DEFAULT 0'),
    ('edited_at',    'DATETIME DEFAULT NULL'),
    ('poll_data',    'JSON'),
    ('location_lat', 'DECIMAL(10,8)'),
    ('location_lng', 'DECIMAL(11,8)'),
]:
    try:
        cur.execute(f'ALTER TABLE messages ADD COLUMN {col} {defn}')
        conn.commit(); print(f'+ Column: messages.{col}')
    except: print(f'~ {col} exists')

# ── 6. Message reactions ──────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS message_reactions (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    student_id INT NOT NULL,
    emoji      VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uq_react (message_id, student_id)
)""")
conn.commit(); print('+ Table: message_reactions')

# NOTE: Sample group seeding (CS Study Group with fake users 1-4)
# has been intentionally removed. Groups are created by real users
# through the app interface.

cur.close(); conn.close()
print('\nMigration 4 complete!')
