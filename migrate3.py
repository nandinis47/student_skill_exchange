import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'student_skill_exchange')
)
cur = conn.cursor()

# Create domains table
cur.execute("""
CREATE TABLE IF NOT EXISTS skill_domains (
    domain_id   INT AUTO_INCREMENT PRIMARY KEY,
    domain_name VARCHAR(100) NOT NULL UNIQUE,
    domain_icon VARCHAR(10) DEFAULT '📚',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
print("+ Table: skill_domains")

# Add domain_id FK to skills table
try:
    cur.execute("ALTER TABLE skills ADD COLUMN domain_id INT DEFAULT NULL")
    conn.commit()
    print("+ Column: skills.domain_id")
except:
    print("~ skills.domain_id already exists")

try:
    cur.execute("ALTER TABLE skills ADD FOREIGN KEY (domain_id) REFERENCES skill_domains(domain_id) ON DELETE SET NULL")
    conn.commit()
    print("+ FK: skills.domain_id -> skill_domains")
except:
    print("~ FK already exists")

# Seed domains
domains = [
    ('Programming Languages', '💻'),
    ('General Studies',       '📚'),
    ('Technical Courses',     '⚙️'),
    ('Entertainment',         '🎭'),
]
for name, icon in domains:
    try:
        cur.execute("INSERT INTO skill_domains (domain_name, domain_icon) VALUES (%s, %s)", (name, icon))
        conn.commit()
    except:
        pass
print("+ Domains seeded")

# Map existing skills to domains
cur.execute("SELECT domain_id FROM skill_domains WHERE domain_name='Programming Languages'")
prog_id = cur.fetchone()[0]
cur.execute("SELECT domain_id FROM skill_domains WHERE domain_name='Technical Courses'")
tech_id = cur.fetchone()[0]
cur.execute("SELECT domain_id FROM skill_domains WHERE domain_name='General Studies'")
gen_id = cur.fetchone()[0]

prog_skills = ['Python','Java','C++','JavaScript','React','Node.js','Android Development']
tech_skills = ['Web Development','Machine Learning','Data Structures','SQL','Cloud Computing','Cybersecurity','Git & GitHub','UI/UX Design']
gen_skills  = ['Mathematics']

for skill in prog_skills:
    cur.execute("UPDATE skills SET domain_id=%s WHERE skill_name=%s", (prog_id, skill))
for skill in tech_skills:
    cur.execute("UPDATE skills SET domain_id=%s WHERE skill_name=%s", (tech_id, skill))
for skill in gen_skills:
    cur.execute("UPDATE skills SET domain_id=%s WHERE skill_name=%s", (gen_id, skill))

conn.commit()
print("+ Skills mapped to domains")

cur.close()
conn.close()
print("Migration 3 complete!")
