"""
Migration 2 - Shared Content + Real-time Chat + Profile Bio
"""
import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'student_skill_exchange')
)
cur = conn.cursor()

# ── 1. Add bio column to students ────────────────────────────
try:
    cur.execute("ALTER TABLE students ADD COLUMN bio TEXT")
    conn.commit()
    print("+ Column: students.bio")
except: print("~ bio already exists")

# ── 2. Add is_online + last_seen to students ─────────────────
for col, defn in [('is_online','TINYINT(1) DEFAULT 0'),('last_seen','DATETIME')]:
    try:
        cur.execute(f"ALTER TABLE students ADD COLUMN {col} {defn}")
        conn.commit()
        print(f"+ Column: students.{col}")
    except: print(f"~ {col} already exists")

# ── 3. Add is_read + message_type + file_url to messages ─────
for col, defn in [
    ('is_read',      'TINYINT(1) DEFAULT 0'),
    ('message_type', "ENUM('text','image','video','audio','document','link') DEFAULT 'text'"),
    ('file_url',     'VARCHAR(500)'),
    ('file_name',    'VARCHAR(255)'),
]:
    try:
        cur.execute(f"ALTER TABLE messages ADD COLUMN {col} {defn}")
        conn.commit()
        print(f"+ Column: messages.{col}")
    except: print(f"~ {col} already exists")

# ── 4. Create shared_content table ───────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS shared_content (
    content_id   INT AUTO_INCREMENT PRIMARY KEY,
    sender_id    INT NOT NULL,
    receiver_id  INT NOT NULL,
    title        VARCHAR(255) NOT NULL,
    content_type ENUM('media','document','link') NOT NULL,
    media_type   ENUM('video','audio','image','pdf','notes','word','presentation','youtube','course','website','resource') DEFAULT NULL,
    file_url     VARCHAR(500),
    file_name    VARCHAR(255),
    file_size    VARCHAR(50),
    description  TEXT,
    shared_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id)   REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES students(id) ON DELETE CASCADE
)
""")
conn.commit()
print("+ Table: shared_content")

# ── 5. Create typing_status table ────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS typing_status (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    typing_to  INT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_typing (student_id, typing_to),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (typing_to)  REFERENCES students(id) ON DELETE CASCADE
)
""")
conn.commit()
print("+ Table: typing_status")

# NOTE: Shared content seeding and bio seeding for fake users (IDs 1-8)
# have been intentionally removed. Genuine users manage their own content
# and bios through the app.

cur.close()
conn.close()
print("\nMigration 2 complete!")
