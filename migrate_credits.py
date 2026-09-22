"""
Migration — Time Credit System
Adds:
  students.time_credits          INT DEFAULT 5   (new users start with 5 free credits)
  learning_sessions.credits_escrowed   INT DEFAULT 0
  learning_sessions.learner_confirmed  TINYINT(1) DEFAULT 0
  learning_sessions.teacher_confirmed  TINYINT(1) DEFAULT 0
  learning_sessions.role               ENUM('learner','teacher') DEFAULT 'learner'
    — records whether student_id is the learner or teacher for credit logic

Also creates:
  credit_ledger  — immutable audit log of every credit movement
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

# ── 1. Add time_credits to students ──────────────────────────
try:
    cur.execute("ALTER TABLE students ADD COLUMN time_credits INT NOT NULL DEFAULT 5")
    conn.commit()
    print("+ Column: students.time_credits")
except Exception as e:
    print(f"~ students.time_credits: {e}")

# ── 2. Add escrow / confirmation columns to learning_sessions ─
for col, defn in [
    ('credits_escrowed',  'INT NOT NULL DEFAULT 0'),
    ('learner_confirmed', 'TINYINT(1) NOT NULL DEFAULT 0'),
    ('teacher_confirmed', 'TINYINT(1) NOT NULL DEFAULT 0'),
    ('role',              "ENUM('learner','teacher') NOT NULL DEFAULT 'learner'"),
]:
    try:
        cur.execute(f"ALTER TABLE learning_sessions ADD COLUMN {col} {defn}")
        conn.commit()
        print(f"+ Column: learning_sessions.{col}")
    except Exception as e:
        print(f"~ learning_sessions.{col}: {e}")

# ── 3. Create credit_ledger ────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS credit_ledger (
    ledger_id   INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT NOT NULL,
    delta       INT NOT NULL,           -- positive = earn, negative = spend/escrow
    balance_after INT NOT NULL,
    txn_type    ENUM(
                  'earn_teaching',      -- 1 credit per hour taught (on session complete)
                  'escrow_lock',        -- deducted when session booked
                  'escrow_release',     -- returned to learner on cancel / non-complete
                  'payment_release',    -- credited to teacher on both confirm
                  'manual'
                ) NOT NULL,
    session_id  INT DEFAULT NULL,
    note        VARCHAR(255),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id) ON DELETE SET NULL
)
""")
conn.commit()
print("+ Table: credit_ledger")

cur.close()
conn.close()
print("\nMigration complete — Time Credit system ready.")
