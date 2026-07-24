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

# ─── 7. Seed badges ───────────────────────────────────────────────────────────
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
            'INSERT INTO badges (badge_name, badge_icon, description, xp_required) VALUES (%s,%s,%s,%s)',
            (name, icon, desc, xp)
        )
        conn.commit()
    except Exception:
        pass
print('  + Badges seeded')

# ─── 8. Give every student the Newbie badge ───────────────────────────────────
cur.execute('SELECT id FROM students')
for (sid,) in cur.fetchall():
    try:
        cur.execute('INSERT INTO student_badges (student_id, badge_id) VALUES (%s, 1)', (sid,))
        conn.commit()
    except Exception:
        pass
print('  + Newbie badge assigned to all students')

# ─── 9. Seed skill_progress for learners ──────────────────────────────────────
cur.execute('SELECT student_id, skill_id FROM student_skills WHERE type="learn"')
rows = cur.fetchall()
import random, datetime
for student_id, skill_id in rows:
    pct = random.randint(20, 80)
    hrs = round(random.uniform(2.0, 30.0), 1)
    days_ago = random.randint(0, 14)
    last = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()
    try:
        cur.execute(
            'INSERT INTO skill_progress (student_id, skill_id, progress_percent, hours_spent, last_practiced) VALUES (%s,%s,%s,%s,%s)',
            (student_id, skill_id, pct, hrs, last)
        )
        conn.commit()
    except Exception:
        pass
print('  + Skill progress seeded')

# ─── 10. Seed learning sessions ───────────────────────────────────────────────
import datetime as dt
sessions = [
    (1, 2, 3, dt.datetime.now() + dt.timedelta(hours=5),  60, 'scheduled'),
    (2, 3, 1, dt.datetime.now() + dt.timedelta(days=1),   45, 'scheduled'),
    (4, 1, 4, dt.datetime.now() - dt.timedelta(days=2),   90, 'completed'),
    (3, 7, 6, dt.datetime.now() + dt.timedelta(days=2),   30, 'scheduled'),
    (6, 8, 4, dt.datetime.now() + dt.timedelta(hours=20), 60, 'scheduled'),
]
for s in sessions:
    try:
        cur.execute(
            'INSERT INTO learning_sessions (student_id, partner_id, skill_id, session_date, duration_minutes, status) VALUES (%s,%s,%s,%s,%s,%s)',
            s
        )
        conn.commit()
    except Exception:
        pass
print('  + Learning sessions seeded')

# ─── 11. Update XP, streak, goals for students ────────────────────────────────
goals = [
    'Learn Python for 30 minutes',
    'Build a React component today',
    'Solve 3 DSA problems',
    'Read ML documentation for 20 min',
    'Practice SQL queries',
    'Review Git workflows',
    'Work on your Web Dev project',
    'Study Data Structures chapter',
]
cur.execute('SELECT id FROM students')
ids = [r[0] for r in cur.fetchall()]
for i, sid in enumerate(ids):
    xp     = random.randint(30, 180)
    streak = random.randint(1, 12)
    goal   = goals[i % len(goals)]
    last   = (dt.date.today() - dt.timedelta(days=random.randint(0, 2))).isoformat()
    cur.execute(
        'UPDATE students SET xp_points=%s, learning_streak=%s, daily_goal=%s, last_activity_date=%s WHERE id=%s',
        (xp, streak, goal, last, sid)
    )
conn.commit()
print('  + XP / streaks / goals updated')

# ─── 12. Seed activity log ────────────────────────────────────────────────────
activities = [
    (1, 'badge_earned',       'Earned Newbie badge',              10),
    (1, 'exchange_completed', 'Completed exchange with Priya',    15),
    (2, 'skill_taught',       'Taught Web Development to Rohan',  20),
    (3, 'skill_learned',      'Made progress in Python',          10),
    (4, 'badge_earned',       'Earned Quick Learner badge',       25),
    (5, 'skill_learned',      'Practiced SQL queries',            10),
    (6, 'exchange_completed', 'Completed ML exchange with Meera', 20),
]
for a in activities:
    try:
        cur.execute(
            'INSERT INTO activity_log (student_id, activity_type, description, xp_earned) VALUES (%s,%s,%s,%s)',
            a
        )
        conn.commit()
    except Exception:
        pass
print('  + Activity log seeded')

cur.close()
conn.close()
print('\nMigration complete!')
