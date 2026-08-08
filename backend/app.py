from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'sse_secret_key_2024'
CORS(app, supports_credentials=True, origins=[
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'null'          # allows file:// origin as fallback
])

# ============================================
# Database Configuration
# ============================================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'system',          # <-- Change to your MySQL password
    'database': 'student_skill_exchange'
}

def get_db():
    """Get a database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ============================================
# AUTH ROUTES
# ============================================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = hash_password(data.get('password'))
    department = data.get('department')
    year = data.get('year')

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO students (name, email, password, department, year) VALUES (%s, %s, %s, %s, %s)",
            (name, email, password, department, year)
        )
        conn.commit()
        return jsonify({'message': 'Registration successful'}), 201
    except Error as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'Email already registered'}), 409
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = hash_password(data.get('password'))

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE email=%s AND password=%s", (email, password))
        student = cursor.fetchone()
        if student:
            session['student_id'] = student['id']
            student.pop('password')
            # profile_pic and avatar_key are already in SELECT * — keep them in response
            return jsonify({'message': 'Login successful', 'student': student}), 200
        return jsonify({'error': 'Invalid credentials'}), 401
    finally:
        cursor.close()
        conn.close()


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200


# ============================================
# STUDENT ROUTES
# ============================================

@app.route('/api/students', methods=['GET'])
def get_all_students():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.name, s.email, s.department, s.year,
            GROUP_CONCAT(DISTINCT CASE WHEN ss.type='teach' THEN sk.skill_name END SEPARATOR ', ') AS teaches,
            GROUP_CONCAT(DISTINCT CASE WHEN ss.type='learn' THEN sk.skill_name END SEPARATOR ', ') AS learns
        FROM students s
        LEFT JOIN student_skills ss ON s.id = ss.student_id
        LEFT JOIN skills sk ON ss.skill_id = sk.skill_id
        GROUP BY s.id
    """)
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(students)


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, department, year FROM students WHERE id=%s", (student_id,))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Student not found'}), 404

    cursor.execute("""
        SELECT sk.skill_id, sk.skill_name, ss.type
        FROM student_skills ss
        JOIN skills sk ON ss.skill_id = sk.skill_id
        WHERE ss.student_id = %s
    """, (student_id,))
    skills = cursor.fetchall()
    student['skills'] = skills
    cursor.close()
    conn.close()
    return jsonify(student)


@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE students SET name=%s, department=%s, year=%s WHERE id=%s",
        (data.get('name'), data.get('department'), data.get('year'), student_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Profile updated'})


# ============================================
# SKILLS ROUTES
# ============================================

@app.route('/api/skills', methods=['GET'])
def get_all_skills():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT skill_id, skill_name, domain_id FROM skills ORDER BY skill_name")
    skills = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(skills)


@app.route('/api/skills', methods=['POST'])
def add_skill():
    data = request.json
    skill_name = data.get('skill_name', '').strip()
    domain_id  = data.get('domain_id')
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO skills (skill_name, domain_id) VALUES (%s, %s)",
            (skill_name, domain_id))
        conn.commit()
        skill_id = cursor.lastrowid
        return jsonify({'skill_id': skill_id, 'skill_name': skill_name}), 201
    except Error as e:
        return jsonify({'error': 'Skill already exists'}), 409
    finally:
        cursor.close()
        conn.close()


@app.route('/api/student-skills', methods=['POST'])
def add_student_skill():
    data = request.json
    student_id = data.get('student_id')
    skill_id = data.get('skill_id')
    skill_type = data.get('type')

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO student_skills (student_id, skill_id, type) VALUES (%s, %s, %s)",
            (student_id, skill_id, skill_type)
        )
        conn.commit()
        return jsonify({'message': 'Skill added'}), 201
    except Error as e:
        return jsonify({'error': 'Skill already added'}), 409
    finally:
        cursor.close()
        conn.close()


@app.route('/api/student-skills/<int:record_id>', methods=['DELETE'])
def delete_student_skill(record_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM student_skills WHERE id=%s", (record_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Skill removed'})


@app.route('/api/search', methods=['GET'])
def search_by_skill():
    skill_name = request.args.get('skill', '')
    skill_type = request.args.get('type', 'teach')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.name, s.email, s.department, s.year, sk.skill_name
        FROM students s
        JOIN student_skills ss ON s.id = ss.student_id
        JOIN skills sk ON ss.skill_id = sk.skill_id
        WHERE sk.skill_name LIKE %s AND ss.type = %s
    """, (f'%{skill_name}%', skill_type))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(results)


# ============================================
# EXCHANGE REQUEST ROUTES
# ============================================

@app.route('/api/requests', methods=['POST'])
def send_request():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO exchange_requests (sender_id, receiver_id, skill_id) VALUES (%s, %s, %s)",
            (data['sender_id'], data['receiver_id'], data['skill_id'])
        )
        conn.commit()
        return jsonify({'message': 'Request sent'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/requests/<int:student_id>', methods=['GET'])
def get_requests(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT er.request_id, s1.name AS sender_name, s2.name AS receiver_name,
               sk.skill_name, er.status, er.created_at,
               er.sender_id, er.receiver_id
        FROM exchange_requests er
        JOIN students s1 ON er.sender_id = s1.id
        JOIN students s2 ON er.receiver_id = s2.id
        JOIN skills sk ON er.skill_id = sk.skill_id
        WHERE er.sender_id = %s OR er.receiver_id = %s
        ORDER BY er.created_at DESC
    """, (student_id, student_id))
    requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(requests)


@app.route('/api/requests/<int:request_id>/status', methods=['PUT'])
def update_request_status(request_id):
    data = request.json
    status = data.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE exchange_requests SET status=%s WHERE request_id=%s", (status, request_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': f'Request {status}'})


# ============================================
# MESSAGES ROUTES
# ============================================

@app.route('/api/messages/<int:student_id>', methods=['GET'])
def get_messages(student_id):
    other_id = request.args.get('with')
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    if other_id:
        cursor.execute("""
            SELECT m.message_id, s1.name AS sender_name, s2.name AS receiver_name,
                   m.message, m.timestamp, m.sender_id, m.receiver_id,
                   m.message_type, m.file_url, m.file_name,
                   m.is_read, m.is_deleted, m.edited_at,
                   m.reply_to_id, m.is_forwarded, m.location_lat, m.location_lng
            FROM messages m
            JOIN students s1 ON m.sender_id = s1.id
            JOIN students s2 ON m.receiver_id = s2.id
            WHERE (m.sender_id=%s AND m.receiver_id=%s)
               OR (m.sender_id=%s AND m.receiver_id=%s)
            ORDER BY m.timestamp ASC
        """, (student_id, other_id, other_id, student_id))
    else:
        cursor.execute("""
            SELECT m.message_id, s1.name AS sender_name, s2.name AS receiver_name,
                   m.message, m.timestamp, m.sender_id, m.receiver_id,
                   m.message_type, m.file_url, m.file_name,
                   m.is_read, m.is_deleted, m.edited_at,
                   m.reply_to_id, m.is_forwarded
            FROM messages m
            JOIN students s1 ON m.sender_id = s1.id
            JOIN students s2 ON m.receiver_id = s2.id
            WHERE m.sender_id=%s OR m.receiver_id=%s
            ORDER BY m.timestamp DESC
        """, (student_id, student_id))
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(messages)


# ============================================
# DASHBOARD STATS
# ============================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total_students FROM students")
    total_students = cursor.fetchone()['total_students']
    cursor.execute("SELECT COUNT(*) AS total_skills FROM skills")
    total_skills = cursor.fetchone()['total_skills']
    cursor.execute("SELECT COUNT(*) AS total_requests FROM exchange_requests")
    total_requests = cursor.fetchone()['total_requests']
    cursor.execute("SELECT COUNT(*) AS total_messages FROM messages")
    total_messages = cursor.fetchone()['total_messages']
    cursor.close()
    conn.close()
    return jsonify({
        'total_students': total_students,
        'total_skills': total_skills,
        'total_requests': total_requests,
        'total_messages': total_messages
    })


@app.route('/api/domains', methods=['GET'])
def get_domains():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM skill_domains ORDER BY domain_name")
    domains = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(domains)


@app.route('/api/domains', methods=['POST'])
def add_domain():
    data = request.json
    name = data.get('domain_name', '').strip()
    icon = data.get('domain_icon', '📚')
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO skill_domains (domain_name, domain_icon) VALUES (%s,%s)", (name, icon))
        conn.commit()
        return jsonify({'domain_id': cursor.lastrowid, 'domain_name': name, 'domain_icon': icon}), 201
    except Exception as e:
        return jsonify({'error': 'Domain already exists'}), 409
    finally:
        cursor.close(); conn.close()


@app.route('/api/domains/<int:domain_id>/skills', methods=['GET'])
def get_skills_by_domain(domain_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM skills WHERE domain_id=%s ORDER BY skill_name", (domain_id,))
    skills = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(skills)


import base64, uuid, os, json as json_lib

# ============================================
# GROUPS API
# ============================================

@app.route('/api/groups', methods=['POST'])
def create_group():
    data = request.json
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chat_groups (group_name, description, created_by) VALUES (%s,%s,%s)",
            (data['group_name'], data.get('description',''), data['created_by'])
        )
        conn.commit()
        gid = cursor.lastrowid
        # Add creator as admin + other members
        cursor.execute("INSERT INTO group_members (group_id,student_id,role) VALUES (%s,%s,'admin')",
                       (gid, data['created_by']))
        for mid in data.get('members', []):
            if mid != data['created_by']:
                try:
                    cursor.execute("INSERT INTO group_members (group_id,student_id,role) VALUES (%s,%s,'member')",
                                   (gid, mid))
                except: pass
        conn.commit()
        return jsonify({'group_id': gid, 'message': 'Group created'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close(); conn.close()


@app.route('/api/groups/<int:student_id>', methods=['GET'])
def get_my_groups(student_id):
    conn = get_db(); cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.group_id, g.group_name, g.description, g.group_icon,
               g.created_at, g.created_by, gm.role,
               (SELECT COUNT(*) FROM group_members WHERE group_id=g.group_id) AS member_count,
               (SELECT message FROM group_messages WHERE group_id=g.group_id ORDER BY timestamp DESC LIMIT 1) AS last_msg
        FROM chat_groups g
        JOIN group_members gm ON g.group_id=gm.group_id
        WHERE gm.student_id=%s ORDER BY g.created_at DESC
    """, (student_id,))
    groups = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(groups)


@app.route('/api/groups/<int:group_id>/messages', methods=['GET'])
def get_group_messages(group_id):
    conn = get_db(); cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT gm.*, s.name AS sender_name
        FROM group_messages gm
        JOIN students s ON gm.sender_id=s.id
        WHERE gm.group_id=%s ORDER BY gm.timestamp ASC
    """, (group_id,))
    msgs = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(msgs)


@app.route('/api/groups/<int:group_id>/messages', methods=['POST'])
def send_group_message(group_id):
    data = request.json
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO group_messages (group_id,sender_id,message,message_type,file_url,file_name)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (group_id, data['sender_id'], data.get('message',''),
          data.get('message_type','text'), data.get('file_url'), data.get('file_name')))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Sent'}), 201


@app.route('/api/groups/<int:group_id>/members', methods=['GET'])
def get_group_members(group_id):
    conn = get_db(); cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.name, s.department, s.year, gm.role, gm.joined_at
        FROM group_members gm JOIN students s ON gm.student_id=s.id
        WHERE gm.group_id=%s ORDER BY gm.role DESC, s.name ASC
    """, (group_id,))
    members = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(members)


@app.route('/api/groups/<int:group_id>/members', methods=['POST'])
def add_group_member(group_id):
    data = request.json
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO group_members (group_id,student_id,role) VALUES (%s,%s,'member')",
                       (group_id, data['student_id']))
        conn.commit()
        return jsonify({'message': 'Member added'}), 201
    except:
        return jsonify({'error': 'Already a member'}), 409
    finally:
        cursor.close(); conn.close()


@app.route('/api/groups/<int:group_id>/members/<int:student_id>', methods=['DELETE'])
def remove_group_member(group_id, student_id):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("DELETE FROM group_members WHERE group_id=%s AND student_id=%s",
                   (group_id, student_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Removed'})


# ============================================
# PROFILE PICTURE API
# ============================================

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/api/profile-pic/<int:student_id>', methods=['POST'])
def upload_profile_pic(student_id):
    data = request.json
    b64  = data.get('image_b64', '')
    if not b64:
        return jsonify({'error': 'No image data'}), 400

    # Validate size (max 5MB base64 ≈ 6.7MB encoded)
    if len(b64) > 7_000_000:
        return jsonify({'error': 'Image too large. Max 5MB'}), 400

    # Decode and save
    try:
        # Strip data URL prefix if present
        if ',' in b64:
            b64 = b64.split(',', 1)[1]
        img_bytes = base64.b64decode(b64)
        fname = f"pic_{student_id}_{uuid.uuid4().hex[:8]}.jpg"
        fpath = os.path.join(UPLOAD_DIR, fname)
        with open(fpath, 'wb') as f:
            f.write(img_bytes)

        url = f'/uploads/{fname}'
        conn = get_db(); cursor = conn.cursor()
        cursor.execute("UPDATE students SET profile_pic=%s WHERE id=%s", (url, student_id))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'url': url, 'message': 'Profile picture updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profile-pic/<int:student_id>', methods=['DELETE'])
def remove_profile_pic(student_id):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE students SET profile_pic=NULL WHERE id=%s", (student_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Profile picture removed'})


@app.route('/api/avatar/<int:student_id>', methods=['PUT'])
def set_avatar(student_id):
    data = request.json
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE students SET avatar_key=%s, profile_pic=NULL WHERE id=%s",
                   (data.get('avatar_key'), student_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Avatar updated'})


# ============================================
# ENHANCED MESSAGES — reactions, reply, delete, edit
# ============================================

@app.route('/api/messages/<int:msg_id>/react', methods=['POST'])
def react_message(msg_id):
    data = request.json
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO message_reactions (message_id,student_id,emoji)
            VALUES (%s,%s,%s)
            ON DUPLICATE KEY UPDATE emoji=%s
        """, (msg_id, data['student_id'], data['emoji'], data['emoji']))
        conn.commit()
        return jsonify({'message': 'Reaction added'})
    finally:
        cursor.close(); conn.close()


@app.route('/api/messages/<int:msg_id>/delete', methods=['PUT'])
def delete_message(msg_id):
    data = request.json
    scope = data.get('scope', 'me')  # 'me' or 'everyone'
    conn = get_db(); cursor = conn.cursor()
    if scope == 'everyone':
        cursor.execute("UPDATE messages SET is_deleted=1, message='This message was deleted' WHERE message_id=%s",
                       (msg_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Deleted'})


@app.route('/api/messages/<int:msg_id>/edit', methods=['PUT'])
def edit_message(msg_id):
    data = request.json
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE messages SET message=%s, edited_at=NOW() WHERE message_id=%s",
                   (data['message'], msg_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Edited'})


# ============================================
# SERVE UPLOADED FILES
# ============================================

from flask import send_from_directory

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ============================================
# GAMIFICATION — XP / STREAK / TODAY'S FOCUS
# ============================================

@app.route('/api/dashboard/<int:student_id>', methods=['GET'])
def get_dashboard(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Student with gamification data
    cursor.execute("""
        SELECT id, name, email, department, year,
               xp_points, learning_streak, daily_goal, last_activity_date
        FROM students WHERE id = %s
    """, (student_id,))
    student = cursor.fetchone()
    if not student:
        cursor.close(); conn.close()
        return jsonify({'error': 'Not found'}), 404

    # Badges earned
    cursor.execute("""
        SELECT b.badge_name, b.badge_emoji AS badge_icon, b.description, sb.earned_at
        FROM student_badges sb JOIN badges b ON sb.badge_id = b.badge_id
        WHERE sb.student_id = %s ORDER BY sb.earned_at DESC
    """, (student_id,))
    badges = cursor.fetchall()

    # Skill progress
    cursor.execute("""
        SELECT sk.skill_name, sp.progress_percent, sp.hours_spent, sp.last_practiced, sp.skill_id
        FROM skill_progress sp JOIN skills sk ON sp.skill_id = sk.skill_id
        WHERE sp.student_id = %s ORDER BY sp.progress_percent DESC
    """, (student_id,))
    progress = cursor.fetchall()

    # Smart matches: students who teach what I want to learn
    cursor.execute("""
        SELECT DISTINCT s.id, s.name, s.department, s.year, sk.skill_name,
               COUNT(DISTINCT ss2.skill_id) AS common_skills
        FROM student_skills ss1
        JOIN student_skills ss2 ON ss1.skill_id = ss2.skill_id AND ss2.type = 'teach'
        JOIN students s ON ss2.student_id = s.id
        JOIN skills sk ON ss1.skill_id = sk.skill_id
        WHERE ss1.student_id = %s AND ss1.type = 'learn' AND s.id != %s
        GROUP BY s.id, s.name, s.department, s.year, sk.skill_name
        ORDER BY common_skills DESC
        LIMIT 5
    """, (student_id, student_id))
    matches = cursor.fetchall()

    # My learning skills for match scoring
    cursor.execute("""
        SELECT COUNT(*) AS total FROM student_skills WHERE student_id=%s AND type='learn'
    """, (student_id,))
    learn_count = cursor.fetchone()['total'] or 1

    for m in matches:
        m['match_percent'] = min(100, int((m['common_skills'] / learn_count) * 100) + 60)

    # Upcoming sessions
    cursor.execute("""
        SELECT ls.session_id, ls.session_date, ls.duration_minutes, ls.status,
               sk.skill_name, s2.name AS partner_name, ls.partner_id
        FROM learning_sessions ls
        JOIN skills sk ON ls.skill_id = sk.skill_id
        LEFT JOIN students s2 ON ls.partner_id = s2.id
        WHERE ls.student_id = %s AND ls.status = 'scheduled'
              AND ls.session_date >= NOW()
        ORDER BY ls.session_date ASC
        LIMIT 5
    """, (student_id,))
    sessions = cursor.fetchall()

    # Skill of the day (most wanted skill)
    cursor.execute("""
        SELECT sk.skill_name, COUNT(ss.student_id) AS learner_count, sk.skill_id
        FROM skills sk
        JOIN student_skills ss ON sk.skill_id = ss.skill_id
        WHERE ss.type = 'teach'
        GROUP BY sk.skill_id, sk.skill_name
        ORDER BY learner_count DESC
        LIMIT 1
    """)
    skill_of_day = cursor.fetchone()

    # Leaderboard (top by XP)
    cursor.execute("""
        SELECT id, name, department, xp_points, learning_streak,
               (SELECT COUNT(*) FROM exchange_requests
                WHERE sender_id=s.id AND status='accepted') AS exchanges_done
        FROM students s
        ORDER BY xp_points DESC
        LIMIT 8
    """)
    leaderboard = cursor.fetchall()

    # Analytics — personal stats
    cursor.execute("SELECT COUNT(*) AS cnt FROM exchange_requests WHERE sender_id=%s AND status='accepted'", (student_id,))
    exchanges_done = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM student_skills WHERE student_id=%s AND type='learn'", (student_id,))
    skills_learning = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM student_skills WHERE student_id=%s AND type='teach'", (student_id,))
    skills_teaching = cursor.fetchone()['cnt']

    cursor.execute("SELECT COALESCE(SUM(hours_spent),0) AS hrs FROM skill_progress WHERE student_id=%s", (student_id,))
    total_hours = float(cursor.fetchone()['hrs'])

    # Recommended skills based on what similar learners study
    cursor.execute("""
        SELECT DISTINCT sk.skill_id, sk.skill_name, COUNT(*) AS popularity
        FROM student_skills ss
        JOIN skills sk ON ss.skill_id = sk.skill_id
        WHERE ss.type = 'learn'
          AND ss.student_id != %s
          AND sk.skill_id NOT IN (
              SELECT skill_id FROM student_skills WHERE student_id=%s
          )
        GROUP BY sk.skill_id, sk.skill_name
        ORDER BY popularity DESC
        LIMIT 5
    """, (student_id, student_id))
    recommended = cursor.fetchall()

    # Weekly activity (last 7 days message + request count)
    cursor.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as cnt
        FROM activity_log WHERE student_id=%s
          AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY day ORDER BY day ASC
    """, (student_id,))
    weekly_activity = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        'student':        student,
        'badges':         badges,
        'skill_progress': progress,
        'smart_matches':  matches,
        'sessions':       sessions,
        'skill_of_day':   skill_of_day,
        'leaderboard':    leaderboard,
        'analytics': {
            'exchanges_done':  exchanges_done,
            'skills_learning': skills_learning,
            'skills_teaching': skills_teaching,
            'total_hours':     total_hours,
        },
        'recommended':     recommended,
        'weekly_activity': weekly_activity,
    })


@app.route('/api/sessions', methods=['POST'])
def schedule_session():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO learning_sessions
                (student_id, partner_id, skill_id, session_date, duration_minutes)
            VALUES (%s, %s, %s, %s, %s)
        """, (data['student_id'], data.get('partner_id'),
              data['skill_id'], data['session_date'], data.get('duration_minutes', 30)))
        conn.commit()
        return jsonify({'message': 'Session scheduled', 'id': cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close(); conn.close()


@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
def update_session(session_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE learning_sessions SET status=%s WHERE session_id=%s",
                   (data['status'], session_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Session updated'})


@app.route('/api/xp/<int:student_id>', methods=['POST'])
def add_xp(student_id):
    data = request.json
    xp = data.get('xp', 10)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET xp_points = xp_points + %s WHERE id=%s", (xp, student_id))

    # Log the activity
    cursor.execute("""
        INSERT INTO activity_log (student_id, activity_type, description, xp_earned)
        VALUES (%s, %s, %s, %s)
    """, (student_id, data.get('type', 'milestone'),
          data.get('description', 'XP earned'), xp))
    conn.commit()

    cursor.execute("SELECT xp_points FROM students WHERE id=%s", (student_id,))
    new_xp = cursor.fetchone()[0]
    cursor.close(); conn.close()
    return jsonify({'xp_points': new_xp})


@app.route('/api/progress/<int:student_id>/<int:skill_id>', methods=['PUT'])
def update_progress(student_id, skill_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO skill_progress (student_id, skill_id, progress_percent, hours_spent, last_practiced)
        VALUES (%s, %s, %s, %s, CURDATE())
        ON DUPLICATE KEY UPDATE
            progress_percent = %s,
            hours_spent = hours_spent + %s,
            last_practiced = CURDATE()
    """, (student_id, skill_id,
          data.get('progress', 0), data.get('hours', 0),
          data.get('progress', 0), data.get('hours', 0)))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Progress updated'})


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.name, s.department, s.xp_points, s.learning_streak,
               (SELECT COUNT(*) FROM exchange_requests
                WHERE (sender_id=s.id OR receiver_id=s.id) AND status='accepted') AS exchanges,
               (SELECT COUNT(*) FROM student_skills WHERE student_id=s.id AND type='teach') AS teaching_count,
               (SELECT COUNT(*) FROM student_skills WHERE student_id=s.id AND type='learn') AS learning_count
        FROM students s
        ORDER BY xp_points DESC
        LIMIT 10
    """)
    leaders = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(leaders)


# ============================================
# REAL-TIME CHAT — enhanced messages
# ============================================

@app.route('/api/messages', methods=['POST'])
def send_message_v2():
    # Handle both old simple messages and new rich messages
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages
            (sender_id, receiver_id, message, message_type, file_url, file_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['sender_id'], data['receiver_id'], data.get('message',''),
        data.get('message_type','text'),
        data.get('file_url'), data.get('file_name')
    ))
    conn.commit()
    msg_id = cursor.lastrowid
    cursor.close(); conn.close()
    return jsonify({'message': 'Message sent', 'message_id': msg_id}), 201


@app.route('/api/messages/<int:student_id>/mark-read', methods=['PUT'])
def mark_messages_read(student_id):
    other_id = request.json.get('other_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE messages SET is_read=1
        WHERE receiver_id=%s AND sender_id=%s AND is_read=0
    """, (student_id, other_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Marked read'})


@app.route('/api/messages/<int:student_id>/unread-count', methods=['GET'])
def unread_count(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT sender_id, COUNT(*) AS cnt
        FROM messages
        WHERE receiver_id=%s AND is_read=0
        GROUP BY sender_id
    """, (student_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(rows)


@app.route('/api/typing', methods=['POST'])
def set_typing():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    if data.get('is_typing'):
        cursor.execute("""
            INSERT INTO typing_status (student_id, typing_to)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE updated_at=NOW()
        """, (data['student_id'], data['typing_to']))
    else:
        cursor.execute("""
            DELETE FROM typing_status
            WHERE student_id=%s AND typing_to=%s
        """, (data['student_id'], data['typing_to']))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'ok': True})


@app.route('/api/typing/<int:student_id>/<int:other_id>', methods=['GET'])
def get_typing(student_id, other_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT COUNT(*) AS is_typing
        FROM typing_status
        WHERE student_id=%s AND typing_to=%s
          AND updated_at >= DATE_SUB(NOW(), INTERVAL 5 SECOND)
    """, (other_id, student_id))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return jsonify({'is_typing': row['is_typing'] > 0})


@app.route('/api/online/<int:student_id>', methods=['POST'])
def set_online(student_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE students SET is_online=%s, last_seen=NOW() WHERE id=%s
    """, (1 if data.get('online') else 0, student_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'ok': True})


@app.route('/api/online/<int:student_id>', methods=['GET'])
def get_online(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT is_online, last_seen FROM students WHERE id=%s", (student_id,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return jsonify(row or {'is_online': 0, 'last_seen': None})


# ============================================
# SHARED CONTENT
# ============================================

@app.route('/api/shared-content', methods=['POST'])
def share_content():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO shared_content
              (sender_id, receiver_id, title, content_type, media_type,
               file_url, file_name, file_size, description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data['sender_id'], data['receiver_id'], data['title'],
            data['content_type'], data.get('media_type'),
            data.get('file_url'), data.get('file_name'),
            data.get('file_size'), data.get('description','')
        ))
        conn.commit()
        return jsonify({'message': 'Content shared', 'id': cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close(); conn.close()


@app.route('/api/shared-content/<int:student_id>', methods=['GET'])
def get_shared_content(student_id):
    other_id     = request.args.get('with')
    content_type = request.args.get('type')   # media / document / link
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT sc.*, s1.name AS sender_name, s2.name AS receiver_name
        FROM shared_content sc
        JOIN students s1 ON sc.sender_id   = s1.id
        JOIN students s2 ON sc.receiver_id = s2.id
        WHERE (sc.sender_id=%s OR sc.receiver_id=%s)
    """
    params = [student_id, student_id]

    if other_id:
        query += " AND (sc.sender_id=%s OR sc.receiver_id=%s)"
        params += [other_id, other_id]
    if content_type:
        query += " AND sc.content_type=%s"
        params.append(content_type)

    query += " ORDER BY sc.shared_at DESC"
    cursor.execute(query, params)
    items = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(items)


@app.route('/api/shared-content/<int:content_id>', methods=['DELETE'])
def delete_shared_content(content_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shared_content WHERE content_id=%s", (content_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Deleted'})


# ============================================
# PROFILE — bio update
# ============================================

@app.route('/api/students/<int:student_id>/bio', methods=['PUT'])
def update_bio(student_id):
    data = request.json
    bio = data.get('bio','').strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET bio=%s WHERE id=%s", (bio, student_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Bio updated'})


@app.route('/api/students/<int:student_id>/full', methods=['GET'])
def get_student_full(student_id):
    """Extended profile with bio, badges, progress"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, name, email, department, year, bio,
               xp_points, learning_streak, is_online, last_seen
        FROM students WHERE id=%s
    """, (student_id,))
    student = cursor.fetchone()
    if not student:
        cursor.close(); conn.close()
        return jsonify({'error': 'Not found'}), 404

    cursor.execute("""
        SELECT sk.skill_id, sk.skill_name, ss.type, ss.id AS ss_id
        FROM student_skills ss
        JOIN skills sk ON ss.skill_id = sk.skill_id
        WHERE ss.student_id=%s
    """, (student_id,))
    student['skills'] = cursor.fetchall()

    cursor.execute("""
        SELECT b.badge_name, b.badge_emoji, b.description, sb.earned_at
        FROM student_badges sb
        JOIN badges b ON sb.badge_id = b.badge_id
        WHERE sb.student_id=%s ORDER BY sb.earned_at DESC
    """, (student_id,))
    student['badges'] = cursor.fetchall()

    cursor.close(); conn.close()
    return jsonify(student)


if __name__ == '__main__':
    app.run(debug=True, port=5000)


# ============================================
# CHAT PREFERENCES — pin, mute, archive, block
# ============================================

def _get_pref(student_id, other_id, create=True):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM chat_prefs WHERE student_id=%s AND other_id=%s", (student_id, other_id))
    row = cur.fetchone()
    if not row and create:
        cur.execute("INSERT INTO chat_prefs (student_id,other_id) VALUES (%s,%s)", (student_id, other_id))
        conn.commit()
        cur.execute("SELECT * FROM chat_prefs WHERE student_id=%s AND other_id=%s", (student_id, other_id))
        row = cur.fetchone()
    cur.close(); conn.close()
    return row

@app.route('/api/chat-pref/<int:student_id>/<int:other_id>', methods=['GET'])
def get_chat_pref(student_id, other_id):
    row = _get_pref(student_id, other_id, create=False)
    return jsonify(row or {'is_pinned':0,'is_muted':0,'is_archived':0,'is_blocked':0})

@app.route('/api/chat-pref/<int:student_id>/<int:other_id>', methods=['PUT'])
def update_chat_pref(student_id, other_id):
    data = request.json
    _get_pref(student_id, other_id, create=True)   # ensure row exists
    conn = get_db(); cur = conn.cursor()
    fields = ['is_pinned','is_muted','is_archived','is_blocked']
    updates = {f: data[f] for f in fields if f in data}
    if not updates:
        cur.close(); conn.close()
        return jsonify({'error': 'Nothing to update'}), 400
    blocked_at_sql = ", blocked_at=NOW()" if updates.get('is_blocked') else ""
    set_clause = ', '.join(f"{k}=%s" for k in updates)
    cur.execute(f"UPDATE chat_prefs SET {set_clause}{blocked_at_sql} WHERE student_id=%s AND other_id=%s",
                list(updates.values()) + [student_id, other_id])
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Preference updated'})

@app.route('/api/chat-pref/<int:student_id>/pinned', methods=['GET'])
def get_pinned_chats(student_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT cp.*, s.name, s.email, s.department FROM chat_prefs cp
        JOIN students s ON cp.other_id=s.id
        WHERE cp.student_id=%s AND cp.is_pinned=1""", (student_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/chat-pref/<int:student_id>/archived', methods=['GET'])
def get_archived_chats(student_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT cp.*, s.name FROM chat_prefs cp
        JOIN students s ON cp.other_id=s.id
        WHERE cp.student_id=%s AND cp.is_archived=1""", (student_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify(rows)

# ============================================
# NOTIFICATIONS
# ============================================

@app.route('/api/notifications/<int:student_id>', methods=['GET'])
def get_notifications(student_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT * FROM notifications WHERE student_id=%s ORDER BY created_at DESC LIMIT 50""",
                (student_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/notifications/<int:student_id>/unread', methods=['GET'])
def get_unread_notif_count(student_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE student_id=%s AND is_read=0", (student_id,))
    cnt = cur.fetchone()['cnt']; cur.close(); conn.close()
    return jsonify({'count': cnt})

@app.route('/api/notifications/<int:student_id>/read-all', methods=['PUT'])
def mark_all_notifs_read(student_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE notifications SET is_read=1 WHERE student_id=%s", (student_id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'All marked read'})

@app.route('/api/notifications', methods=['POST'])
def create_notification():
    data = request.json
    conn = get_db(); cur = conn.cursor()
    cur.execute("""INSERT INTO notifications (student_id,type,title,body,icon,action_url)
        VALUES (%s,%s,%s,%s,%s,%s)""",
        (data['student_id'], data.get('type','message'), data.get('title',''),
         data.get('body',''), data.get('icon','🔔'), data.get('action_url','')))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Created'}), 201

# ============================================
# FORWARD MESSAGE
# ============================================

@app.route('/api/messages/<int:msg_id>/forward', methods=['POST'])
def forward_message(msg_id):
    data = request.json
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM messages WHERE message_id=%s", (msg_id,))
    orig = cur.fetchone()
    if not orig:
        cur.close(); conn.close()
        return jsonify({'error': 'Message not found'}), 404
    # Forward to new recipients
    for receiver_id in data.get('to', []):
        cur.execute("""INSERT INTO messages
            (sender_id,receiver_id,message,message_type,file_url,file_name,is_forwarded,forward_from_id)
            VALUES (%s,%s,%s,%s,%s,%s,1,%s)""",
            (data['sender_id'], receiver_id, orig['message'],
             orig['message_type'], orig.get('file_url'), orig.get('file_name'), msg_id))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': f'Forwarded to {len(data.get("to",[]))} recipients'})

# ============================================
# PIN MESSAGE
# ============================================

@app.route('/api/messages/<int:msg_id>/pin', methods=['PUT'])
def pin_message(msg_id):
    data = request.json
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE messages SET is_pinned=%s WHERE message_id=%s", (data.get('pin',1), msg_id))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Pinned' if data.get('pin',1) else 'Unpinned'})

@app.route('/api/messages/pinned/<int:student_id>/<int:other_id>', methods=['GET'])
def get_pinned_messages(student_id, other_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT m.*, s.name AS sender_name FROM messages m
        JOIN students s ON m.sender_id=s.id
        WHERE is_pinned=1 AND (
            (sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s))
        ORDER BY m.timestamp DESC""", (student_id,other_id,other_id,student_id))
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify(rows)

# ============================================
# SEARCH MESSAGES
# ============================================

@app.route('/api/messages/search', methods=['GET'])
def search_messages():
    q          = request.args.get('q', '')
    student_id = request.args.get('student_id')
    other_id   = request.args.get('other_id')
    if not q or not student_id:
        return jsonify([])
    conn = get_db(); cur = conn.cursor(dictionary=True)
    params = [f'%{q}%', student_id, student_id]
    sql = """SELECT m.*, s.name AS sender_name FROM messages m
        JOIN students s ON m.sender_id=s.id
        WHERE m.message LIKE %s AND (m.sender_id=%s OR m.receiver_id=%s)"""
    if other_id:
        sql += " AND (m.sender_id=%s OR m.receiver_id=%s)"
        params += [other_id, other_id]
    sql += " ORDER BY m.timestamp DESC LIMIT 30"
    cur.execute(sql, params)
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify(rows)

# ============================================
# GROUP ADMIN FEATURES
# ============================================

@app.route('/api/groups/<int:group_id>/promote/<int:target_id>', methods=['PUT'])
def promote_member(group_id, target_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE group_members SET role='admin' WHERE group_id=%s AND student_id=%s", (group_id, target_id))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Promoted to admin'})

@app.route('/api/groups/<int:group_id>/demote/<int:target_id>', methods=['PUT'])
def demote_member(group_id, target_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE group_members SET role='member' WHERE group_id=%s AND student_id=%s", (group_id, target_id))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Demoted to member'})

@app.route('/api/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    data = request.json
    conn = get_db(); cur = conn.cursor()
    fields, vals = [], []
    for f in ['group_name','description','who_can_send','who_can_edit']:
        if f in data:
            fields.append(f'{f}=%s'); vals.append(data[f])
    if not fields:
        cur.close(); conn.close()
        return jsonify({'error': 'Nothing to update'}), 400
    cur.execute(f"UPDATE chat_groups SET {', '.join(fields)} WHERE group_id=%s", vals + [group_id])
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Group updated'})

@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM chat_groups WHERE group_id=%s", (group_id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'message': 'Group deleted'})

# Update /api/messages to store is_read, is_forwarded fields
# (already handled by existing GET with extra columns)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
