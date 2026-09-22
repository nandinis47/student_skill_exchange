"""
Student Skills Exchange - Database Setup Script
Usage: python setup_db.py <mysql_root_password>
"""
import mysql.connector
import sys
import os
import re

print("=" * 55)
print("  Student Skills Exchange - Database Setup")
print("=" * 55)

if len(sys.argv) < 2:
    print("\nUsage: python setup_db.py <your_mysql_password>")
    sys.exit(1)

password = sys.argv[1]

print(f"\nConnecting to MySQL...")
try:
    conn = mysql.connector.connect(host='localhost', user='root', password=password)
    print("✓ Connected to MySQL successfully!")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)

cursor = conn.cursor()
base = os.path.dirname(os.path.abspath(__file__))

def run_sql_file(filepath, label):
    print(f"\nRunning {label}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    # Remove single-line comments
    raw = re.sub(r'--[^\n]*', '', raw)
    # Remove multi-line comments
    raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.DOTALL)
    # Split on semicolons
    statements = [s.strip() for s in raw.split(';')]

    ok = 0
    for stmt in statements:
        if not stmt:
            continue
        try:
            cursor.execute(stmt)
            conn.commit()
            ok += 1
        except mysql.connector.Error as e:
            if e.errno in (1007, 1050, 1062):  # DB/table exists, duplicate
                ok += 1
            else:
                print(f"  Warning ({e.errno}): {e.msg[:80]}")
    print(f"  ✓ {ok} statements executed")

run_sql_file(os.path.join(base, 'database', 'schema.sql'), 'schema.sql')
# sample_data.sql only inserts skills catalogue (INSERT IGNORE — safe to re-run).
# Student/user seed data was removed from that file intentionally.
run_sql_file(os.path.join(base, 'database', 'sample_data.sql'), 'sample_data.sql (skills catalogue only)')

# Verify counts
cursor.execute("USE student_skill_exchange")
counts = {}
for tbl in ['students', 'skills', 'student_skills', 'exchange_requests', 'messages']:
    cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
    counts[tbl] = cursor.fetchone()[0]

print(f"\n✓ Database populated!")
for k, v in counts.items():
    print(f"  {k:<22} {v} rows")

cursor.close()
conn.close()

# Update app.py password
app_path = os.path.join(base, 'backend', 'app.py')
with open(app_path, 'r') as f:
    content = f.read()
new_content = re.sub(
    r"'password': '[^']*',\s*# <-- Change to your MySQL password",
    f"'password': '{password}',          # <-- Change to your MySQL password",
    content
)
with open(app_path, 'w') as f:
    f.write(new_content)

print(f"\n✓ backend/app.py updated with MySQL password")
print("\n" + "=" * 55)
print("  Setup complete! Starting backend now...")
print("=" * 55)
