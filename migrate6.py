"""
Migration 6 — Notes & Assignments
Adds two tables:
  notes        — teacher posts notes/assignments for a learner
  submissions  — learner uploads completed work for an assignment
"""
import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "student_skill_exchange")
)
cur = conn.cursor()

# ── 1. notes ──────────────────────────────────────────────────
# teacher_id  : the student who is teaching
# learner_id  : the student who is learning
# skill_id    : which skill this note/assignment belongs to
# note_type   : 'note' = plain note, 'assignment' = has work to submit
# title       : short title
# content     : body text (instructions, note content)
# file_url    : optional attachment URL (teacher-uploaded file)
# available_from : learner cannot see/submit before this datetime
# due_at      : submission deadline (NULL = no deadline)
cur.execute("""
CREATE TABLE IF NOT EXISTS notes (
    note_id        INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id     INT NOT NULL,
    learner_id     INT NOT NULL,
    skill_id       INT,
    note_type      ENUM('note','assignment') NOT NULL DEFAULT 'note',
    title          VARCHAR(255) NOT NULL,
    content        TEXT,
    file_url       VARCHAR(500),
    file_name      VARCHAR(255),
    available_from DATETIME DEFAULT NULL,
    due_at         DATETIME DEFAULT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (learner_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id)   REFERENCES skills(skill_id) ON DELETE SET NULL
)
""")
conn.commit()
print("+ Table: notes")

# ── 2. submissions ────────────────────────────────────────────
# One row per learner submission per note (assignments only).
# learner can re-submit before due_at — latest row is the active one.
cur.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    sub_id      INT AUTO_INCREMENT PRIMARY KEY,
    note_id     INT NOT NULL,
    learner_id  INT NOT NULL,
    content     TEXT,
    file_url    VARCHAR(500),
    file_name   VARCHAR(255),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id)    REFERENCES notes(note_id)    ON DELETE CASCADE,
    FOREIGN KEY (learner_id) REFERENCES students(id)      ON DELETE CASCADE
)
""")
conn.commit()
print("+ Table: submissions")

cur.close()
conn.close()
print("\nMigration 6 complete — Notes & Assignments tables ready.")
