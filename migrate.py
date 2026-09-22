import mysql.connector

conn = mysql.connector.connect(
    host='localhost', user='root', password='system',
    database='student_skill_exchange'
)
cur = conn.cursor()

# ─── 1. Add new columns to students ───────────────────────────────────────────
columns = [
    ('xp_points',          'INT DEFAULT 0'),
    ('learning_streak',    'INT DEFAULT 0'),
    ('last_activity_date', 'DATE'),
    ('daily_goal',         'VARCHAR(200)'),
    ('avatar_emoji',       'VARCHAR(10) DEFAULT NULL'),
]
for col, defn in columns:
    try:
        cur.execute(f'ALTER TABLE students ADD COLUMN {col} {defn}')
        conn.commit()
        print(f'  + Column added: {col}')
    except Exception:
        print(f'  ~ Column exists: {col}')

# ─── 2. Create badges table ────────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS badges (
    badge_id   INT AUTO_INCREMENT PRIMARY KEY,
    badge_name VARCHAR(100) NOT NULL,
    badge_icon VARCHAR(20),
    description VARCHAR(255),
    xp_required INT DEFAULT 0
)''')
conn.commit()
print('  + Table: badges')

# ─── 3. Create student_badges table ───────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS student_badges (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    badge_id   INT NOT NULL,
    earned_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id)   REFERENCES badges(badge_id) ON DELETE CASCADE,
    UNIQUE KEY uq_sb (student_id, badge_id)
)''')
conn.commit()
print('  + Table: student_badges')

# ─── 4. Create skill_progress table ───────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS skill_progress (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT NOT NULL,
    skill_id         INT NOT NULL,
    progress_percent INT DEFAULT 0,
    hours_spent      DECIMAL(5,1) DEFAULT 0,
    last_practiced   DATE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id)   REFERENCES skills(skill_id) ON DELETE CASCADE,
    UNIQUE KEY uq_sp (student_id, skill_id)
)''')
conn.commit()
print('  + Table: skill_progress')

# ─── 5. Create learning_sessions table ────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS learning_sessions (
    session_id       INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT NOT NULL,
    partner_id       INT,
    skill_id         INT NOT NULL,
    session_date     DATETIME NOT NULL,
    duration_minutes INT DEFAULT 30,
    status           ENUM("scheduled","completed","cancelled") DEFAULT "scheduled",
    notes            TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (partner_id) REFERENCES students(id) ON DELETE SET NULL,
    FOREIGN KEY (skill_id)   REFERENCES skills(skill_id) ON DELETE CASCADE
)''')
conn.commit()
print('  + Table: learning_sessions')

# ─── 6. Create activity_log table ─────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS activity_log (
    log_id       INT AUTO_INCREMENT PRIMARY KEY,
    student_id   INT NOT NULL,
    activity_type ENUM("skill_learned","skill_taught","exchange_completed","badge_earned","milestone") NOT NULL,
    description  VARCHAR(255),
    xp_earned    INT DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
)''')
conn.commit()
print('  + Table: activity_log')

# ─── 7. Seed badges catalogue (reference data only) ───────────────────────────
badge_data = [
    ('Newbie',          'seedling',  'Welcome to Skills Exchange!',         0),
    ('First Exchange',  'handshake', 'Completed first skill exchange',      10),
    ('Quick Learner',   'zap',       'Learning 3+ skills',                  50),
    ('Master Teacher',  'teacher',   'Taught 5+ students',                  100),
    ('Streak Master',   'fire',      '7-day learning streak',               75),
    ('Social Butterfly','butterfly', 'Connected with 10+ students',         60),
    ('Knowledge Seeker','books',     'Learning 5 skills simultaneously',    40),
    ('Community Hero',  'trophy',    'Helped 20+ students',                 200),
]
for name, icon, desc, xp in badge_data:
    try:
        cur.execute(
            'INSERT IGNORE INTO badges (badge_name, badge_icon, description, xp_required) VALUES (%s,%s,%s,%s)',
            (name, icon, desc, xp)
        )
        conn.commit()
    except Exception:
        pass
print('  + Badges catalogue ensured')

# NOTE: Steps 8-12 (Newbie badge assignment, skill_progress seeding,
# learning session seeding, XP/streak/goal updates, activity log seeding)
# have been intentionally removed. These were fake/test data for seeded
# users (IDs 1-8) that no longer exist. Genuine users earn this data
# through real interactions with the app.

cur.close()
conn.close()
print('\nMigration complete!')
