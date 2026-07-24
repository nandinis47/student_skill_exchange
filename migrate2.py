"""
Migration 2 - Shared Content + Real-time Chat + Profile Bio
"""
import mysql.connector

conn = mysql.connector.connect(
    host='localhost', user='root', password='system',
    database='student_skill_exchange'
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

# ── 6. Seed sample shared content ────────────────────────────
import datetime
samples = [
    (1, 2, 'Python Basics Cheatsheet',   'document', 'pdf',          None, 'python_cheatsheet.pdf', '245 KB',  'Complete Python syntax reference'),
    (2, 1, 'React Crash Course',          'media',    'video',        'https://www.youtube.com/watch?v=w7ejDZ8SWv8', None, None, 'Great beginner React tutorial'),
    (4, 1, 'ML for Beginners - Google',   'link',     'course',       'https://developers.google.com/machine-learning/crash-course', None, None, 'Free ML course by Google'),
    (1, 3, 'DSA Notes PDF',               'document', 'notes',        None, 'dsa_notes.pdf', '1.2 MB',  'My personal DSA revision notes'),
    (2, 3, 'Web Dev Roadmap',             'link',     'website',      'https://roadmap.sh/frontend', None, None, 'Complete frontend roadmap'),
    (7, 1, 'Node.js Crash Course Video',  'media',    'video',        'https://www.youtube.com/watch?v=fBNz5xF-Kx4', None, None, 'Node.js full tutorial'),
    (4, 6, 'ML Slides - Week 1',          'document', 'presentation', None, 'ml_week1.pptx', '3.4 MB', 'My lecture slides'),
    (8, 6, 'Cloud Computing Intro',       'link',     'youtube',      'https://www.youtube.com/watch?v=M988_fsOSWo', None, None, 'AWS basics explained'),
]
for s in samples:
    try:
        cur.execute("""
            INSERT INTO shared_content
              (sender_id,receiver_id,title,content_type,media_type,file_url,file_name,file_size,description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, s)
        conn.commit()
    except Exception as e:
        print(f"  skip: {e}")
print("+ Shared content seeded")

# ── 7. Sample bios ────────────────────────────────────────────
bios = [
    (1, "Hi! I'm Aarav, a 2nd year CS student passionate about Python and DSA. I love problem-solving and competitive programming. Looking to learn Web Dev and ML from peers!"),
    (2, "Hey, I'm Priya! Web developer in training 🌐 I teach React and HTML/CSS. Always up for a skill exchange. Let's build something cool together!"),
    (3, "Rohan here — Electronics student who loves coding on the side. Learning Python and SQL. Feel free to reach out for an exchange!"),
    (4, "Sneha — 4th year CS, specializing in ML and Data Science. Happy to teach what I know and always eager to keep learning!"),
]
for sid, bio in bios:
    cur.execute("UPDATE students SET bio=%s WHERE id=%s", (bio, sid))
conn.commit()
print("+ Bios seeded")

cur.close()
conn.close()
print("\nMigration 2 complete!")
