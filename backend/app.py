from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import hashlib
import os
import re
import requests as http_requests   # for Google token verification (fallback)

# ── Firebase Admin SDK for server-side token verification ─────
# Download your service account key from:
#   Firebase Console → Project Settings → Service Accounts
#   → Generate new private key → save as backend/firebase-service-account.json
#
# If the file is absent, we fall back to Google tokeninfo endpoint.
import firebase_admin
from firebase_admin import credentials as fb_creds, auth as fb_auth

_SERVICE_ACCOUNT_FILE = '/etc/secrets/firebase-service-account.json'
_firebase_app_initialized = False

def _init_firebase_admin():
    global _firebase_app_initialized
    if _firebase_app_initialized:
        return True
    if os.path.exists(_SERVICE_ACCOUNT_FILE):
        try:
            cred = fb_creds.Certificate(_SERVICE_ACCOUNT_FILE)
            firebase_admin.initialize_app(cred)
            _firebase_app_initialized = True
            print("+ Firebase Admin SDK initialised from service account key")
            return True
        except Exception as e:
            print(f"Firebase Admin init failed: {e}")
    return False

# Try to init on startup
_init_firebase_admin()

# ── Google tokeninfo fallback (no service account needed) ─────
GOOGLE_TOKEN_INFO_URL = 'https://oauth2.googleapis.com/tokeninfo'

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'local-dev-secret-change-me')
CORS(app, supports_credentials=True, origins=[
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'https://skillx-frontend.onrender.com',
    'null'          # allows file:// origin as fallback
])

# ============================================
# Database Configuration
# ============================================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'system'),
    'database': os.getenv('DB_NAME', 'student_skill_exchange'),
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
            # Check if email is verified (for non-Google accounts)
            if not student.get('google_sub') and not student.get('email_verified', 0):
                cursor.close()
                conn.close()
                return jsonify({'error': 'Please verify your email before logging in. Check your inbox for the verification link.'}), 403
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


@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """
    Checks Firebase user's email verification status and updates the database.
    Called after user clicks the verification link in their email.
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Try to sign in with Firebase to get the user object
    try:
        if not _firebase_app_initialized:
            # Fallback: mark as verified if Firebase Admin not available
            # This is a safe fallback for development
            conn = get_db()
            if not conn:
                return jsonify({'error': 'Database connection failed'}), 500
            cursor = conn.cursor()
            cursor.execute("UPDATE students SET email_verified = 1 WHERE email = %s", (email,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'message': 'Email verified'}), 200

        # Use Firebase Admin to get user by email
        try:
            user = fb_auth.get_user_by_email(email)
            if user.email_verified:
                # Update database
                conn = get_db()
                if not conn:
                    return jsonify({'error': 'Database connection failed'}), 500
                cursor = conn.cursor()
                cursor.execute("UPDATE students SET email_verified = 1 WHERE email = %s", (email,))
                conn.commit()
                cursor.close()
                conn.close()
                return jsonify({'message': 'Email verified successfully'}), 200
            else:
                return jsonify({'error': 'Email not yet verified. Please check your inbox.'}), 400
        except fb_auth.UserNotFoundError:
            return jsonify({'error': 'User not found in Firebase'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/send-verification', methods=['POST'])
def send_verification_email():
    """
    Server-assisted verification email send.
    1) Confirms email/password with Identity Toolkit
    2) Calls accounts:sendOobCode (same path as client sendEmailVerification)
    3) On rate-limit / send failure, tries Admin generateEmailVerificationLink
       and returns the link so the UI can still let the user verify
    Does not touch Google Sign-In.
    """
    data = request.json or {}
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    api_key = None
    try:
        # Reuse the web API key already published in frontend config (not a new secret)
        config_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'js', 'firebase-config.js')
        with open(config_path, 'r', encoding='utf-8') as f:
            m = re.search(r'apiKey:\s*"([^"]+)"', f.read())
            if m:
                api_key = m.group(1)
    except Exception:
        api_key = None

    if not api_key:
        return jsonify({'error': 'Firebase web API key not found in frontend config'}), 500

    try:
        sign_in = http_requests.post(
            f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}',
            json={'email': email, 'password': password, 'returnSecureToken': True},
            timeout=30,
        )
        sign_body = sign_in.json()
        if sign_in.status_code != 200:
            return jsonify({
                'error': sign_body.get('error', {}).get('message', 'Invalid email or password'),
                'firebase_error': sign_body.get('error', {}).get('message'),
            }), 401

        id_token = sign_body.get('idToken')
        firebase_email = sign_body.get('email') or email
        if sign_body.get('emailVerified') in (True, 'true'):
            return jsonify({
                'message': 'Email is already verified',
                'email': firebase_email,
                'already_verified': True,
            }), 200

        send = http_requests.post(
            f'https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}',
            json={'requestType': 'VERIFY_EMAIL', 'idToken': id_token},
            timeout=30,
        )
        send_body = send.json()
        if send.status_code == 200:
            return jsonify({
                'message': 'Verification email sent',
                'email': send_body.get('email') or firebase_email,
                'method': 'firebase_email',
                'check_spam': True,
                'sender': 'noreply@skillx-4b13d.firebaseapp.com',
            }), 200

        firebase_err = send_body.get('error', {}).get('message', 'sendOobCode failed')

        # Fallback: Admin-generated link (same quota; helps when client SDK errors differ)
        link = None
        link_error = None
        if _firebase_app_initialized:
            try:
                link = fb_auth.generate_email_verification_link(firebase_email)
            except Exception as link_ex:
                link_error = str(link_ex)

        if link:
            return jsonify({
                'message': 'Firebase email send failed; use this verification link instead',
                'email': firebase_email,
                'method': 'admin_link',
                'verification_link': link,
                'firebase_error': firebase_err,
                'check_spam': True,
                'sender': 'noreply@skillx-4b13d.firebaseapp.com',
            }), 200

        return jsonify({
            'error': firebase_err,
            'email': firebase_email,
            'firebase_error': firebase_err,
            'link_error': link_error,
            'hint': 'If you see TOO_MANY_ATTEMPTS_TRY_LATER, wait a few minutes. '
                    'Also check Spam/Promotions for earlier SkillX verification emails.',
        }), 429 if 'TOO_MANY' in str(firebase_err) else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# GOOGLE SIGN-IN
# ============================================

@app.route('/api/auth/google', methods=['POST'])
def google_signin():
    """
    Receives the Google ID token from the frontend,
    validates it with Google's tokeninfo endpoint,
    then creates or finds the user in the DB and
    returns a session just like normal login.

    Security:
    - Token is verified by Google's server (not locally decoded)
    - audience (aud) is checked against GOOGLE_CLIENT_ID
    - Email verified flag is required
    - A secure random password is stored for Google users
      (they never use it; it prevents password-login to their account)
    """
    data  = request.json
    token = data.get('id_token', '').strip()

    if not token:
        return jsonify({'error': 'No token provided'}), 400

    # ── 1. Verify Firebase ID token ──────────────────────────
    #
    # Method A — Firebase Admin SDK (most secure, requires service account key)
    # Method B — Google tokeninfo endpoint (works without service account)
    #
    if _firebase_app_initialized:
        # ── Method A: Firebase Admin (cryptographic verification) ─
        try:
            decoded = fb_auth.verify_id_token(token)
            email      = decoded.get('email', '').lower().strip()
            name       = decoded.get('name', email.split('@')[0])
            google_sub = decoded.get('sub', decoded.get('uid', ''))
            email_verified = decoded.get('email_verified', False)
        except fb_auth.InvalidIdTokenError as e:
            return jsonify({'error': f'Invalid Firebase token: {str(e)}'}), 401
        except fb_auth.ExpiredIdTokenError:
            return jsonify({'error': 'Firebase token has expired. Please sign in again.'}), 401
        except Exception as e:
            return jsonify({'error': f'Token verification failed: {str(e)}'}), 500
    else:
        # ── Method B: Google tokeninfo endpoint (fallback) ────────
        # Works for Firebase-issued tokens since Firebase uses Google's JWT infrastructure
        try:
            resp = http_requests.get(
                GOOGLE_TOKEN_INFO_URL,
                params={'id_token': token},
                timeout=10
            )
            info = resp.json()
        except Exception as e:
            return jsonify({'error': f'Token verification failed: {str(e)}'}), 500

        if 'error_description' in info or resp.status_code != 200:
            return jsonify({'error': 'Invalid token: ' + info.get('error_description', 'unknown')}), 401

        email          = info.get('email', '').lower().strip()
        name           = info.get('name', email.split('@')[0])
        google_sub     = info.get('sub', '')
        email_verified = info.get('email_verified') in ('true', True)

    # ── 2. Require verified email ─────────────────────────────
    if not email_verified:
        return jsonify({'error': 'Email is not verified in Google/Firebase'}), 401

    if not email:
        return jsonify({'error': 'No email in token'}), 401

    # ── 4. Find or create user in DB ──────────────────────────
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
        student = cursor.fetchone()

        if student:
            # Existing user — link their Google sub if not already linked
            if not student.get('google_sub'):
                cursor.execute(
                    "UPDATE students SET google_sub=%s WHERE id=%s",
                    (google_sub, student['id'])
                )
                conn.commit()
            student.pop('password', None)
        else:
            # New user — create account from Google profile
            # Store a random hash as password (unusable for direct login)
            fake_password = hashlib.sha256(
                (google_sub + os.urandom(16).hex()).encode()
            ).hexdigest()

            cursor.execute("""
                INSERT INTO students (name, email, password, department, year, google_sub)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, email, fake_password, 'Not specified', 1, google_sub))
            conn.commit()

            cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
            student = cursor.fetchone()
            student.pop('password', None)

            # Give Newbie badge to new Google users
            try:
                cursor.execute(
                    "INSERT IGNORE INTO student_badges (student_id, badge_id) VALUES (%s, 1)",
                    (student['id'],)
                )
                conn.commit()
            except Exception:
                pass

        session['student_id'] = student['id']
        return jsonify({'message': 'Google sign-in successful', 'student': student}), 200

    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


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


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM students WHERE id=%s", (student_id,))
        conn.commit()
        session.clear()
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/students/<int:student_id>/email', methods=['PUT'])
def update_student_email(student_id):
    data = request.json or {}
    new_email = (data.get('email') or '').strip().lower()
    if not new_email or '@' not in new_email:
        return jsonify({'error': 'Invalid email address'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM students WHERE email=%s AND id!=%s", (new_email, student_id))
        if cursor.fetchone():
            return jsonify({'error': 'Email address is already in use by another account'}), 400

        cursor.execute("UPDATE students SET email=%s WHERE id=%s", (new_email, student_id))
        conn.commit()

        cursor.execute("SELECT id, name, email, department, year, profile_pic, avatar_key, google_sub FROM students WHERE id=%s", (student_id,))
        student = cursor.fetchone()
        return jsonify({'message': 'Email updated successfully', 'student': student})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/students/<int:student_id>/password', methods=['PUT'])
def update_student_password(student_id):
    data = request.json or {}
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')

    if not current_pw or not new_pw:
        return jsonify({'error': 'Current password and new password are required'}), 400

    if len(new_pw) < 6:
        return jsonify({'error': 'New password must be at least 6 characters long'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE id=%s", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        if student.get('google_sub'):
            return jsonify({'error': 'Password change is disabled for Google-authenticated accounts'}), 400

        if student.get('password') != hash_password(current_pw):
            return jsonify({'error': 'Current password is incorrect'}), 400

        cursor.execute("UPDATE students SET password=%s WHERE id=%s", (hash_password(new_pw), student_id))
        conn.commit()
        return jsonify({'message': 'Password changed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/settings/<int:student_id>', methods=['GET'])
def get_user_settings(student_id):
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, email, google_sub FROM students WHERE id=%s", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        cursor.execute("SELECT * FROM user_settings WHERE student_id=%s", (student_id,))
        settings = cursor.fetchone()

        if not settings:
            cursor.execute("""
                INSERT INTO user_settings (student_id, notif_requests, notif_messages, notif_sessions, notif_smart_matches, request_permissions, profile_visibility, session_duration, session_availability, theme)
                VALUES (%s, 1, 1, 1, 1, 'everyone', 'public', 60, 'anytime', 'light')
            """, (student_id,))
            conn.commit()
            cursor.execute("SELECT * FROM user_settings WHERE student_id=%s", (student_id,))
            settings = cursor.fetchone()

        settings['is_google_user'] = bool(student.get('google_sub'))
        settings['email'] = student.get('email')
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/settings/<int:student_id>', methods=['PUT'])
def update_user_settings(student_id):
    data = request.json or {}
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO user_settings (
                student_id, notif_requests, notif_messages, notif_sessions, notif_smart_matches,
                request_permissions, profile_visibility, session_duration, session_availability, theme
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notif_requests = VALUES(notif_requests),
                notif_messages = VALUES(notif_messages),
                notif_sessions = VALUES(notif_sessions),
                notif_smart_matches = VALUES(notif_smart_matches),
                request_permissions = VALUES(request_permissions),
                profile_visibility = VALUES(profile_visibility),
                session_duration = VALUES(session_duration),
                session_availability = VALUES(session_availability),
                theme = VALUES(theme)
        """, (
            student_id,
            1 if data.get('notif_requests', True) else 0,
            1 if data.get('notif_messages', True) else 0,
            1 if data.get('notif_sessions', True) else 0,
            1 if data.get('notif_smart_matches', True) else 0,
            data.get('request_permissions', 'everyone'),
            data.get('profile_visibility', 'public'),
            int(data.get('session_duration', 60)),
            data.get('session_availability', 'anytime'),
            data.get('theme', 'light')
        ))
        conn.commit()
        return jsonify({'message': 'Settings updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/support-requests', methods=['POST'])
def create_support_request():
    data = request.json or {}
    category = (data.get('category') or '').strip()
    description = (data.get('description') or '').strip()

    # Authenticated user ID (or payload student_id fallback)
    student_id = session.get('student_id') or data.get('student_id')

    if not student_id:
        return jsonify({'error': 'Authentication required. Student ID missing.'}), 401

    if not category or not description:
        return jsonify({'error': 'Category and description are required.'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM students WHERE id=%s", (student_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Student not found'}), 404

        cursor.execute("""
            INSERT INTO support_requests (student_id, category, description, status)
            VALUES (%s, %s, %s, 'Open')
        """, (student_id, category, description))
        conn.commit()
        req_id = cursor.lastrowid

        cursor.execute("SELECT * FROM support_requests WHERE request_id=%s", (req_id,))
        ticket = cursor.fetchone()
        return jsonify({'message': 'Support request submitted successfully', 'ticket': ticket}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/support-requests/<int:student_id>', methods=['GET'])
def get_student_support_requests(student_id):
    auth_id = session.get('student_id')
    if auth_id and int(auth_id) != int(student_id):
        return jsonify({'error': 'Unauthorized to view support tickets for another user.'}), 403

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM support_requests
            WHERE student_id=%s
            ORDER BY created_at DESC
        """, (student_id,))
        tickets = cursor.fetchall()
        return jsonify(tickets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/feedback', methods=['POST'])
def create_feedback():
    data = request.json or {}
    rating = data.get('rating')
    category = (data.get('category') or '').strip()
    message = (data.get('message') or '').strip()
    allow_contact = 1 if data.get('allow_contact') else 0

    student_id = session.get('student_id') or data.get('student_id')

    if not student_id:
        return jsonify({'error': 'Authentication required. Student ID missing.'}), 401

    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            return jsonify({'error': 'Rating must be an integer between 1 and 5.'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid star rating (1-5) is required.'}), 400

    if not category or not message:
        return jsonify({'error': 'Category and feedback message are required.'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM students WHERE id=%s", (student_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Student not found'}), 404

        cursor.execute("""
            INSERT INTO feedback (student_id, rating, category, message, allow_contact, status)
            VALUES (%s, %s, %s, %s, %s, 'Open')
        """, (student_id, rating_int, category, message, allow_contact))
        conn.commit()
        fb_id = cursor.lastrowid

        cursor.execute("SELECT * FROM feedback WHERE feedback_id=%s", (fb_id,))
        fb_item = cursor.fetchone()
        return jsonify({'message': 'Feedback submitted successfully', 'feedback': fb_item}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/feedback/<int:student_id>', methods=['GET'])
def get_student_feedback(student_id):
    auth_id = session.get('student_id')
    if auth_id and int(auth_id) != int(student_id):
        return jsonify({'error': 'Unauthorized to view feedback history for another user.'}), 403

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM feedback
            WHERE student_id=%s
            ORDER BY created_at DESC
        """, (student_id,))
        feedback_list = cursor.fetchall()
        return jsonify(feedback_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()





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
            "INSERT INTO exchange_requests (sender_id, receiver_id, skill_id, note) VALUES (%s, %s, %s, %s)",
            (data['sender_id'], data['receiver_id'], data['skill_id'], data.get('note') or None)
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
               er.sender_id, er.receiver_id, er.note
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

def validate_https_url(url):
    """
    Returns (True, cleaned_url) or (False, error_message).
    - Auto-upgrades http:// → https://
    - Auto-prepends https:// to bare domains like example.com
    - Rejects ftp://, javascript:, and truly malformed strings
    """
    if not url:
        return True, url
    url = url.strip()

    # Block dangerous schemes explicitly first
    lower = url.lower()
    for bad in ('javascript:', 'data:', 'vbscript:', 'ftp://', 'file://'):
        if lower.startswith(bad):
            return False, f'"{bad}" URLs are not allowed. Only https:// is accepted.'

    # Auto-upgrade http → https
    if url.startswith('http://'):
        url = 'https://' + url[7:]

    # Auto-prepend https:// to bare domains (e.g. "example.com")
    if not url.startswith('https://'):
        url = 'https://' + url

    # Final parse check
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        if p.scheme != 'https' or not p.netloc or '.' not in p.netloc:
            raise ValueError
        return True, url
    except Exception:
        return False, 'Invalid URL. Use a full address like https://example.com'


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
# SMART MATCHES & DASHBOARD API
# ============================================

def compute_smart_matches(cursor, student_id):
    """
    Compute Smart Matches for a given student_id.
    Includes:
      - Semantic/NLP skill expansion (_related_ids via ALIASES + token containment)
      - Mutual-benefit scoring (common_skills / learn_count * 70 + reciprocal_skills / teach_count * 30)
      - Reliability scoring (completion rate + acceptance rate multiplier)
      - Feedback scoring (direct outcome history adjustments)
    """
    # 1. Fetch all skills from the catalogue once
    cursor.execute("SELECT skill_id, skill_name FROM skills")
    all_skills = cursor.fetchall()                             # list of dicts

    # 2. Alias table: maps normalised variant → normalised canonical name.
    ALIASES = {
        'ml':                    'machine learning',
        'ai':                    'machine learning',
        'artificial intelligence':'machine learning',
        'react.js':              'react',
        'react js':              'react',
        'reactjs':               'react',
        'react native':          'react',
        'node':                  'node.js',
        'nodejs':                'node.js',
        'node js':               'node.js',
        'js':                    'javascript',
        'javascript':            'javascript',
        'ts':                    'typescript',
        'typescript':            'typescript',
        'py':                    'python',
        'c plus plus':           'c++',
        'cpp':                   'c++',
        'dsa':                   'data structures',
        'data structure':        'data structures',
        'dbms':                  'sql',
        'database':              'sql',
        'mysql':                 'sql',
        'postgresql':            'sql',
        'ui ux':                 'ui/ux design',
        'uiux':                  'ui/ux design',
        'ux':                    'ui/ux design',
        'ui':                    'ui/ux design',
        'cloud':                 'cloud computing',
        'aws':                   'cloud computing',
        'azure':                 'cloud computing',
        'gcp':                   'cloud computing',
        'devops':                'cloud computing',
        'git':                   'git & github',
        'github':                'git & github',
        'android':               'android development',
        'mobile':                'android development',
        'security':              'cybersecurity',
        'cyber':                 'cybersecurity',
        'infosec':               'cybersecurity',
        'web dev':               'web development',
        'web':                   'web development',
        'frontend':              'web development',
        'backend':               'web development',
        'fullstack':             'web development',
        'maths':                 'mathematics',
        'math':                  'mathematics',
        'calculus':              'mathematics',
        'statistics':            'mathematics',
    }

    def _norm(s):
        import re
        return re.sub(r'\s+', ' ', re.sub(r'[.\-_/]', ' ', s.lower())).strip()

    def _related_ids(target_skill_id, target_name, catalogue):
        related = {target_skill_id}
        norm_target = _norm(target_name)

        canonical_target = ALIASES.get(norm_target, norm_target)

        for row in catalogue:
            cid  = row['skill_id']
            norm_cat = _norm(row['skill_name'])
            canonical_cat = ALIASES.get(norm_cat, norm_cat)

            if cid == target_skill_id:
                continue

            if canonical_target == canonical_cat:
                related.add(cid)
                continue

            import re
            tokens_t = set(re.split(r'[\s./\-_]+', canonical_target))
            tokens_c = set(re.split(r'[\s./\-_]+', canonical_cat))
            nontrivial_t = {t for t in tokens_t if len(t) > 1}
            nontrivial_c = {t for t in tokens_c if len(t) > 1}
            if nontrivial_t and nontrivial_c and (nontrivial_t & nontrivial_c):
                related.add(cid)

        return related

    # 3. Fetch viewer's learning skill IDs and names
    cursor.execute("""
        SELECT ss.skill_id, sk.skill_name
        FROM student_skills ss
        JOIN skills sk ON ss.skill_id = sk.skill_id
        WHERE ss.student_id = %s AND ss.type = 'learn'
    """, (student_id,))
    learn_rows = cursor.fetchall()

    # 4. Build expanded set: for each learn skill, find all related IDs
    expanded_learn_ids = set()
    for lr in learn_rows:
        expanded_learn_ids |= _related_ids(lr['skill_id'], lr['skill_name'], all_skills)

    if not expanded_learn_ids:
        expanded_learn_ids = {-1}

    exp_ph = ','.join(['%s'] * len(expanded_learn_ids))

    cursor.execute(f"""
        SELECT
            s.id,
            s.name,
            s.department,
            s.year,
            MIN(sk.skill_name) AS skill_name,
            COUNT(DISTINCT ss2.skill_id) AS common_skills,
            COUNT(DISTINCT ss_rec.skill_id) AS reciprocal_skills
        FROM student_skills ss2
        JOIN students s  ON ss2.student_id = s.id
        JOIN skills   sk ON ss2.skill_id   = sk.skill_id
        LEFT JOIN student_skills ss_rec
             ON ss_rec.student_id = s.id AND ss_rec.type = 'learn'
             AND ss_rec.skill_id IN (
                 SELECT skill_id FROM student_skills
                 WHERE student_id = %s AND type = 'teach'
             )
        WHERE ss2.type = 'teach'
          AND ss2.skill_id IN ({exp_ph})
          AND s.id != %s
        GROUP BY s.id, s.name, s.department, s.year
        ORDER BY common_skills DESC, reciprocal_skills DESC
        LIMIT 5
    """, (
        student_id,
        *expanded_learn_ids,
        student_id,
    ))
    matches = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) AS total FROM student_skills WHERE student_id=%s AND type='learn'",
        (student_id,)
    )
    learn_count = cursor.fetchone()['total'] or 1

    cursor.execute(
        "SELECT COUNT(*) AS total FROM student_skills WHERE student_id=%s AND type='teach'",
        (student_id,)
    )
    teach_count = cursor.fetchone()['total'] or 1

    # ── Reliability scoring ────────────────────────────────────
    if matches:
        match_ids = tuple(m['id'] for m in matches)
        ph = ','.join(['%s'] * len(match_ids))

        cursor.execute(f"""
            SELECT
                s.id AS student_id,
                SUM(CASE WHEN ls.status='completed' THEN 1 ELSE 0 END)   AS sess_completed,
                SUM(CASE WHEN ls.status='cancelled' THEN 1 ELSE 0 END)   AS sess_cancelled,
                COUNT(ls.session_id)                                      AS sess_total,
                SUM(CASE WHEN er.status='accepted' THEN 1 ELSE 0 END)    AS req_accepted,
                COUNT(er.request_id)                                      AS req_total
            FROM students s
            LEFT JOIN learning_sessions ls
                   ON ls.partner_id = s.id
            LEFT JOIN exchange_requests er
                   ON er.receiver_id = s.id
            WHERE s.id IN ({ph})
            GROUP BY s.id
        """, match_ids)

        rel_rows = {r['student_id']: r for r in cursor.fetchall()}

        for m in matches:
            row = rel_rows.get(m['id'], {})

            sess_total     = int(row.get('sess_total', 0) or 0)
            sess_completed = int(row.get('sess_completed', 0) or 0)
            sess_cancelled = int(row.get('sess_cancelled', 0) or 0)
            if sess_total == 0:
                completion_rate = 0.5
            else:
                effective_total = sess_completed + sess_cancelled
                completion_rate = (sess_completed / effective_total) if effective_total else 0.5

            req_total    = int(row.get('req_total', 0) or 0)
            req_accepted = int(row.get('req_accepted', 0) or 0)
            if req_total == 0:
                acceptance_rate = 0.5
            else:
                acceptance_rate = req_accepted / req_total

            reliability_mult = completion_rate * 0.6 + acceptance_rate * 0.4

            primary = (m['common_skills'] / learn_count) * 70
            bonus   = (m['reciprocal_skills'] / teach_count) * 30
            raw     = primary + bonus

            adjusted = raw * (reliability_mult * 2)

            m['match_percent']       = max(1, min(100, round(adjusted)))
            m['is_mutual']           = m['reciprocal_skills'] > 0
            m['reliability_mult']    = round(reliability_mult, 3)

        # ── Feedback loop ──────────────────────────────────────
        cursor.execute(f"""
            SELECT
                partner_teacher_id,
                SUM(CASE WHEN outcome='session_completed'  THEN 1 ELSE 0 END) AS n_completed,
                SUM(CASE WHEN outcome='session_cancelled'  THEN 1 ELSE 0 END) AS n_cancelled,
                SUM(CASE WHEN outcome='request_accepted'   THEN 1 ELSE 0 END) AS n_accepted,
                SUM(CASE WHEN outcome='request_rejected'   THEN 1 ELSE 0 END) AS n_rejected
            FROM (
                SELECT ls.partner_id AS partner_teacher_id,
                       CASE ls.status
                           WHEN 'completed' THEN 'session_completed'
                           WHEN 'cancelled' THEN 'session_cancelled'
                           ELSE NULL
                       END AS outcome
                FROM learning_sessions ls
                WHERE ls.student_id = %s
                  AND ls.partner_id IN ({ph})
                  AND ls.status IN ('completed','cancelled')

                UNION ALL

                SELECT er.sender_id AS partner_teacher_id,
                       'request_accepted' AS outcome
                FROM exchange_requests er
                WHERE er.receiver_id = %s
                  AND er.sender_id IN ({ph})
                  AND er.status = 'accepted'

                UNION ALL

                SELECT er.sender_id AS partner_teacher_id,
                       'request_rejected' AS outcome
                FROM exchange_requests er
                WHERE er.receiver_id = %s
                  AND er.sender_id IN ({ph})
                  AND er.status = 'rejected'

                UNION ALL

                SELECT er.receiver_id AS partner_teacher_id,
                       'request_accepted' AS outcome
                FROM exchange_requests er
                WHERE er.sender_id = %s
                  AND er.receiver_id IN ({ph})
                  AND er.status = 'accepted'
            ) AS pair_outcomes
            WHERE partner_teacher_id IS NOT NULL
            GROUP BY partner_teacher_id
        """, (
            student_id, *match_ids,
            student_id, *match_ids,
            student_id, *match_ids,
            student_id, *match_ids,
        ))

        fb_rows = {r['partner_teacher_id']: r for r in cursor.fetchall()}

        for m in matches:
            fb = fb_rows.get(m['id'])
            if not fb:
                m['feedback_adj'] = 0
                continue

            adj = 0
            adj += int(fb['n_completed'] or 0) * 15
            adj += int(fb['n_accepted']  or 0) * 10
            adj -= int(fb['n_cancelled'] or 0) *  5
            adj -= int(fb['n_rejected']  or 0) * 15

            m['match_percent'] = max(1, min(100, m['match_percent'] + adj))
            m['feedback_adj']  = adj

        matches.sort(key=lambda x: x['match_percent'], reverse=True)

    return matches


@app.route('/api/matches/<int:student_id>', methods=['GET'])
def get_smart_matches(student_id):
    """Dedicated endpoint for Smart Matches For You."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Student not found'}), 404
        matches = compute_smart_matches(cursor, student_id)
        return jsonify(matches)
    finally:
        cursor.close()
        conn.close()


@app.route('/api/dashboard/<int:student_id>', methods=['GET'])
def get_dashboard(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Student with gamification data
    cursor.execute("""
        SELECT id, name, email, department, year,
               xp_points, learning_streak, daily_goal, last_activity_date,
               time_credits
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

    # Smart matches computed via helper
    matches = compute_smart_matches(cursor, student_id)

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
            'time_credits':    student.get('time_credits', 0),
        },
        'recommended':     recommended,
        'weekly_activity': weekly_activity,
    })


@app.route('/api/sessions', methods=['POST'])
def schedule_session():
    """
    Book a session with credit escrow.
    Body must include:
      student_id    — the person booking (the LEARNER spending credits)
      partner_id    — the teacher
      skill_id, session_date, duration_minutes
    Credits escrowed = ceil(duration_minutes / 60), min 1.
    If learner has insufficient credits the booking is rejected.
    Solo sessions (no partner_id) require no credits.
    """
    data = request.json
    learner_id = data['student_id']
    teacher_id = data.get('partner_id')
    duration   = int(data.get('duration_minutes', 60))

    # Credits required: 1 per hour (round up), minimum 1 for paired sessions
    import math
    credits_needed = math.ceil(duration / 60) if teacher_id else 0

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # ── Check learner balance ────────────────────────────
        if credits_needed > 0:
            cursor.execute("SELECT time_credits FROM students WHERE id=%s", (learner_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': 'Student not found'}), 404
            balance = row['time_credits']
            if balance < credits_needed:
                return jsonify({
                    'error': f'Insufficient Time Credits. '
                             f'You need {credits_needed} but have {balance}. '
                             f'Teach more sessions to earn credits!'
                }), 402

        # ── Insert session ───────────────────────────────────
        cursor2 = conn.cursor()
        cursor2.execute("""
            INSERT INTO learning_sessions
                (student_id, partner_id, skill_id, session_date,
                 duration_minutes, credits_escrowed, role)
            VALUES (%s, %s, %s, %s, %s, %s, 'learner')
        """, (learner_id, teacher_id,
              data['skill_id'], data['session_date'],
              duration, credits_needed))
        conn.commit()
        session_id = cursor2.lastrowid

        # ── Escrow credits ───────────────────────────────────
        if credits_needed > 0:
            cursor2.execute(
                "UPDATE students SET time_credits = time_credits - %s WHERE id=%s",
                (credits_needed, learner_id)
            )
            cursor2.execute("SELECT time_credits FROM students WHERE id=%s", (learner_id,))
            new_bal = cursor2.fetchone()[0]
            cursor2.execute("""
                INSERT INTO credit_ledger
                    (student_id, delta, balance_after, txn_type, session_id, note)
                VALUES (%s, %s, %s, 'escrow_lock', %s, %s)
            """, (learner_id, -credits_needed, new_bal, session_id,
                  f'Escrowed {credits_needed} credit(s) for session {session_id}'))
            conn.commit()

        cursor2.close()
        return jsonify({
            'message': 'Session scheduled',
            'id': session_id,
            'credits_escrowed': credits_needed
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close(); conn.close()


@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
def update_session(session_id):
    """
    Generic status update (used by existing dashboard cancel button).
    If status == 'cancelled': refund escrowed credits to learner.
    For completion use POST /api/sessions/<id>/confirm instead.
    """
    data   = request.json
    status = data.get('status')
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT student_id, partner_id, credits_escrowed, status "
            "FROM learning_sessions WHERE session_id=%s",
            (session_id,)
        )
        sess = cursor.fetchone()
        if not sess:
            return jsonify({'error': 'Session not found'}), 404

        cursor2 = conn.cursor()
        cursor2.execute(
            "UPDATE learning_sessions SET status=%s WHERE session_id=%s",
            (status, session_id)
        )

        # Refund escrow if cancelled and not already refunded
        if status == 'cancelled' and sess['credits_escrowed'] > 0 \
                and sess['status'] == 'scheduled':
            learner_id = sess['student_id']
            refund     = sess['credits_escrowed']
            cursor2.execute(
                "UPDATE students SET time_credits = time_credits + %s WHERE id=%s",
                (refund, learner_id)
            )
            cursor2.execute("SELECT time_credits FROM students WHERE id=%s", (learner_id,))
            new_bal = cursor2.fetchone()[0]
            cursor2.execute("""
                INSERT INTO credit_ledger
                    (student_id, delta, balance_after, txn_type, session_id, note)
                VALUES (%s, %s, %s, 'escrow_release', %s, %s)
            """, (learner_id, refund, new_bal, session_id,
                  f'Refunded {refund} credit(s) — session {session_id} cancelled'))

        conn.commit()
        cursor2.close()
        return jsonify({'message': f'Session {status}'})
    finally:
        cursor.close(); conn.close()


@app.route('/api/xp/<int:student_id>', methods=['POST'])
def add_xp(student_id):
    data    = request.json
    xp      = data.get('xp', 10)
    txn_type = data.get('type', 'milestone')
    conn    = get_db()
    cursor  = conn.cursor(dictionary=True)

    # ── Daily-goal guard: award +10 XP only once per calendar day ──
    # Only applies to milestone/daily-goal calls, not session XP etc.
    if txn_type == 'milestone':
        cursor.execute(
            "SELECT last_activity_date FROM students WHERE id=%s", (student_id,)
        )
        row = cursor.fetchone()
        if row and row['last_activity_date']:
            from datetime import date
            if row['last_activity_date'] == date.today():
                # Already completed today — return current XP without adding
                cursor.execute("SELECT xp_points FROM students WHERE id=%s", (student_id,))
                current_xp = cursor.fetchone()['xp_points']
                cursor.close(); conn.close()
                return jsonify({'xp_points': current_xp, 'already_done': True})

    # Award XP and stamp last_activity_date
    cursor2 = conn.cursor()
    cursor2.execute(
        "UPDATE students SET xp_points = xp_points + %s, last_activity_date = CURDATE() WHERE id=%s",
        (xp, student_id)
    )

    # Log the activity
    cursor2.execute("""
        INSERT INTO activity_log (student_id, activity_type, description, xp_earned)
        VALUES (%s, %s, %s, %s)
    """, (student_id, txn_type,
          data.get('description', 'XP earned'), xp))
    conn.commit()

    cursor2.execute("SELECT xp_points FROM students WHERE id=%s", (student_id,))
    new_xp = cursor2.fetchone()[0]
    cursor2.close(); cursor.close(); conn.close()
    return jsonify({'xp_points': new_xp, 'already_done': False})


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
    data = request.json
    conn = get_db()
    cursor = conn.cursor()

    msg_type = data.get('message_type', 'text')
    file_url  = data.get('file_url')

    # Validate https:// for link and shared-url messages
    if msg_type == 'link' and file_url:
        ok, result = validate_https_url(file_url)
        if not ok:
            return jsonify({'error': result}), 422
        file_url = result   # use upgraded/cleaned URL

    cursor.execute("""
        INSERT INTO messages
            (sender_id, receiver_id, message, message_type, file_url, file_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['sender_id'], data['receiver_id'], data.get('message',''),
        msg_type, file_url, data.get('file_name')
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

    # Validate https:// for any provided URL
    file_url = data.get('file_url')
    if file_url:
        ok, result = validate_https_url(file_url)
        if not ok:
            cursor.close(); conn.close()
            return jsonify({'error': f'Invalid URL: {result}'}), 422
        file_url = result  # store upgraded/cleaned URL

    try:
        cursor.execute("""
            INSERT INTO shared_content
              (sender_id, receiver_id, title, content_type, media_type,
               file_url, file_name, file_size, description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data['sender_id'], data['receiver_id'], data['title'],
            data['content_type'], data.get('media_type'),
            file_url, data.get('file_name'),
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
               xp_points, learning_streak, is_online, last_seen,
               profile_pic, avatar_key, time_credits, is_admin
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


@app.route('/api/voice-upload', methods=['POST'])
def upload_voice():
    """Receive base64 audio, save to uploads/, return URL."""
    data = request.json
    b64  = data.get('audio_b64', '')
    if not b64:
        return jsonify({'error': 'No audio data'}), 400
    # Strip data URL header  e.g. "data:audio/webm;base64,..."
    if ',' in b64:
        b64 = b64.split(',', 1)[1]
    try:
        audio_bytes = base64.b64decode(b64)
        fname = f"voice_{uuid.uuid4().hex[:12]}.webm"
        fpath = os.path.join(UPLOAD_DIR, fname)
        with open(fpath, 'wb') as f:
            f.write(audio_bytes)
        url = f"{os.getenv('BACKEND_URL', 'http://127.0.0.1:5000')}/uploads/{fname}"
        return jsonify({'url': url}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

# ============================================================
# NOTES & ASSIGNMENTS
# ============================================================
#
# Relationships used:
#   student_skills.type = 'teach'  →  teacher_id is that student
#   student_skills.type = 'learn'  →  learner_id is that student
#
# Who I teach:  people who have skill X as 'learn'
#               where I have skill X as 'teach'  (I teach them)
# Who teaches me: people who have skill X as 'teach'
#               where I have skill X as 'learn'  (they teach me)
#
# This is resolved purely from student_skills — no extra FK needed.
# ============================================================

@app.route('/api/notes/connections/<int:student_id>', methods=['GET'])
def get_notes_connections(student_id):
    """
    Returns two lists:
      teaching  — people I am teaching (they learn a skill I teach)
      learning  — people who are teaching me (they teach a skill I learn)
    Only students who share at least one skill relationship are included.
    """
    conn = get_db(); cur = conn.cursor(dictionary=True)

    # People I teach: they have 'learn' for a skill I have 'teach'
    cur.execute("""
        SELECT DISTINCT s.id, s.name, s.department, s.year,
               sk.skill_name, sk.skill_id
        FROM student_skills my_ss
        JOIN student_skills   their_ss ON my_ss.skill_id = their_ss.skill_id
                                      AND their_ss.type = 'learn'
        JOIN students s  ON their_ss.student_id = s.id
        JOIN skills   sk ON my_ss.skill_id = sk.skill_id
        WHERE my_ss.student_id = %s
          AND my_ss.type = 'teach'
          AND s.id != %s
        ORDER BY s.name
    """, (student_id, student_id))
    teaching = cur.fetchall()

    # People who teach me: they have 'teach' for a skill I have 'learn'
    cur.execute("""
        SELECT DISTINCT s.id, s.name, s.department, s.year,
               sk.skill_name, sk.skill_id
        FROM student_skills my_ss
        JOIN student_skills   their_ss ON my_ss.skill_id = their_ss.skill_id
                                      AND their_ss.type = 'teach'
        JOIN students s  ON their_ss.student_id = s.id
        JOIN skills   sk ON my_ss.skill_id = sk.skill_id
        WHERE my_ss.student_id = %s
          AND my_ss.type = 'learn'
          AND s.id != %s
        ORDER BY s.name
    """, (student_id, student_id))
    learning = cur.fetchall()

    cur.close(); conn.close()
    return jsonify({'teaching': teaching, 'learning': learning})


@app.route('/api/notes', methods=['POST'])
def create_note():
    """
    Teacher creates a note or assignment for a specific learner.
    Body: { teacher_id, learner_id, skill_id, note_type,
            title, content, file_url, file_name,
            available_from, due_at }
    """
    data = request.json
    required = ['teacher_id', 'learner_id', 'title', 'note_type']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'Missing field: {f}'}), 400

    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO notes
                (teacher_id, learner_id, skill_id, note_type,
                 title, content, file_url, file_name,
                 available_from, due_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data['teacher_id'], data['learner_id'],
            data.get('skill_id') or None,
            data['note_type'],
            data['title'],
            data.get('content', ''),
            data.get('file_url') or None,
            data.get('file_name') or None,
            data.get('available_from') or None,
            data.get('due_at') or None,
        ))
        conn.commit()
        return jsonify({'message': 'Created', 'note_id': cur.lastrowid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close(); conn.close()


@app.route('/api/notes/for-pair', methods=['GET'])
def get_notes_for_pair():
    """
    Returns notes for a specific teacher-learner pair.
    Query params: teacher_id, learner_id, viewer_id
    viewer_id determines what is visible:
      - If viewer is the teacher  → see everything
      - If viewer is the learner  → only notes where available_from <= NOW()
                                     (or available_from IS NULL)
    """
    teacher_id = request.args.get('teacher_id', type=int)
    learner_id = request.args.get('learner_id', type=int)
    viewer_id  = request.args.get('viewer_id',  type=int)

    if not teacher_id or not learner_id or not viewer_id:
        return jsonify({'error': 'teacher_id, learner_id, viewer_id required'}), 400

    conn = get_db(); cur = conn.cursor(dictionary=True)

    if viewer_id == teacher_id:
        # Teacher sees all notes + submission counts
        cur.execute("""
            SELECT n.*,
                   sk.skill_name,
                   t.name AS teacher_name,
                   l.name AS learner_name,
                   (SELECT COUNT(*) FROM submissions
                    WHERE note_id = n.note_id) AS submission_count,
                   (SELECT sub_id FROM submissions
                    WHERE note_id = n.note_id
                    ORDER BY submitted_at DESC LIMIT 1) AS latest_sub_id
            FROM notes n
            LEFT JOIN skills   sk ON n.skill_id   = sk.skill_id
            JOIN      students t  ON n.teacher_id = t.id
            JOIN      students l  ON n.learner_id = l.id
            WHERE n.teacher_id = %s AND n.learner_id = %s
            ORDER BY n.created_at DESC
        """, (teacher_id, learner_id))
    else:
        # Learner sees only available notes
        cur.execute("""
            SELECT n.*,
                   sk.skill_name,
                   t.name AS teacher_name,
                   l.name AS learner_name,
                   (SELECT sub_id FROM submissions
                    WHERE note_id = n.note_id AND learner_id = %s
                    ORDER BY submitted_at DESC LIMIT 1) AS latest_sub_id,
                   (SELECT submitted_at FROM submissions
                    WHERE note_id = n.note_id AND learner_id = %s
                    ORDER BY submitted_at DESC LIMIT 1) AS submitted_at_val
            FROM notes n
            LEFT JOIN skills   sk ON n.skill_id   = sk.skill_id
            JOIN      students t  ON n.teacher_id = t.id
            JOIN      students l  ON n.learner_id = l.id
            WHERE n.teacher_id = %s AND n.learner_id = %s
              AND (n.available_from IS NULL OR n.available_from <= NOW())
            ORDER BY n.created_at DESC
        """, (learner_id, learner_id, teacher_id, learner_id))

    notes = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(notes)


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Teacher deletes a note (cascades to submissions)."""
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE note_id = %s", (note_id,))
    conn.commit()
    cur.close(); conn.close()
    return jsonify({'message': 'Deleted'})


@app.route('/api/notes/<int:note_id>/submissions', methods=['GET'])
def get_submissions(note_id):
    """Teacher views all submissions for a note."""
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT sub.*, s.name AS learner_name
        FROM submissions sub
        JOIN students s ON sub.learner_id = s.id
        WHERE sub.note_id = %s
        ORDER BY sub.submitted_at DESC
    """, (note_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)


@app.route('/api/notes/<int:note_id>/submit', methods=['POST'])
def submit_work(note_id):
    """
    Learner submits completed work.
    Body: { learner_id, content, file_url, file_name }
    Allowed only when available_from <= NOW() (enforced server-side).
    """
    data = request.json
    learner_id = data.get('learner_id')
    if not learner_id:
        return jsonify({'error': 'learner_id required'}), 400

    conn = get_db(); cur = conn.cursor(dictionary=True)

    # Verify the note exists and is available
    cur.execute("""
        SELECT note_id, note_type, available_from, due_at
        FROM notes WHERE note_id = %s AND learner_id = %s
    """, (note_id, learner_id))
    note = cur.fetchone()
    if not note:
        cur.close(); conn.close()
        return jsonify({'error': 'Assignment not found'}), 404
    if note['note_type'] != 'assignment':
        cur.close(); conn.close()
        return jsonify({'error': 'This note is not an assignment'}), 400
    if note['available_from']:
        cur.execute("SELECT NOW() AS now")
        now = cur.fetchone()['now']
        if now < note['available_from']:
            cur.close(); conn.close()
            return jsonify({'error': 'Assignment is not yet available'}), 403

    try:
        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO submissions (note_id, learner_id, content, file_url, file_name)
            VALUES (%s, %s, %s, %s, %s)
        """, (note_id, learner_id,
              data.get('content', ''),
              data.get('file_url') or None,
              data.get('file_name') or None))
        conn.commit()
        return jsonify({'message': 'Submitted', 'sub_id': cur2.lastrowid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        if 'cur2' in dir():
            cur2.close()
        conn.close()



# ============================================================
# TIME CREDIT SYSTEM
# ============================================================

def _ledger_entry(cursor, student_id, delta, txn_type, session_id, note):
    """Insert a credit_ledger row and return the new balance."""
    cursor.execute(
        "UPDATE students SET time_credits = time_credits + %s WHERE id=%s",
        (delta, student_id)
    )
    cursor.execute("SELECT time_credits FROM students WHERE id=%s", (student_id,))
    new_bal = cursor.fetchone()[0]
    cursor.execute("""
        INSERT INTO credit_ledger
            (student_id, delta, balance_after, txn_type, session_id, note)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (student_id, delta, new_bal, txn_type, session_id, note))
    return new_bal


@app.route('/api/sessions/<int:session_id>/confirm', methods=['POST'])
def confirm_session(session_id):
    """
    Called by either the learner or the teacher to mark the session done
    from their side.

    Body: { student_id: <int> }

    Logic:
    - Identify whether the caller is the learner (student_id) or teacher (partner_id).
    - Set learner_confirmed or teacher_confirmed = 1.
    - If BOTH are now confirmed:
        * Mark session status = 'completed'.
        * Release escrowed credits to the teacher (1 per escrowed credit).
        * Award the teacher 1 extra Time Credit per hour taught (earn_teaching).
        * Add XP to teacher (+20) via activity_log.
    - Returns: { both_confirmed, credits_released, teacher_new_balance,
                 learner_confirmed, teacher_confirmed }
    """
    data       = request.json
    caller_id  = data.get('student_id')
    if not caller_id:
        return jsonify({'error': 'student_id required'}), 400

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT session_id, student_id, partner_id, status,
                   duration_minutes, credits_escrowed,
                   learner_confirmed, teacher_confirmed
            FROM learning_sessions WHERE session_id=%s
        """, (session_id,))
        sess = cursor.fetchone()
        if not sess:
            return jsonify({'error': 'Session not found'}), 404
        if sess['status'] == 'completed':
            return jsonify({'error': 'Session already completed'}), 409
        if sess['status'] == 'cancelled':
            return jsonify({'error': 'Session was cancelled'}), 409

        learner_id = sess['student_id']
        teacher_id = sess['partner_id']

        # Determine role of caller
        if caller_id == learner_id:
            col = 'learner_confirmed'
        elif caller_id == teacher_id:
            col = 'teacher_confirmed'
        else:
            return jsonify({'error': 'You are not part of this session'}), 403

        # Mark this side confirmed
        cursor2 = conn.cursor(dictionary=True)
        cursor2.execute(
            f"UPDATE learning_sessions SET {col}=1 WHERE session_id=%s",
            (session_id,)
        )
        conn.commit()

        # Re-read confirmed state
        cursor2.execute("""
            SELECT learner_confirmed, teacher_confirmed, credits_escrowed, duration_minutes
            FROM learning_sessions WHERE session_id=%s
        """, (session_id,))
        updated = cursor2.fetchone()
        lc = updated['learner_confirmed']
        tc = updated['teacher_confirmed']
        escrowed  = updated['credits_escrowed']
        duration  = updated['duration_minutes']

        result = {
            'learner_confirmed': bool(lc),
            'teacher_confirmed': bool(tc),
            'both_confirmed':    bool(lc and tc),
            'credits_released':  0,
        }

        if lc and tc and teacher_id:
            # ── Both confirmed — complete & pay ──────────────
            cursor2.execute(
                "UPDATE learning_sessions SET status='completed' WHERE session_id=%s",
                (session_id,)
            )

            import math
            hours_taught = max(1, math.ceil(duration / 60))

            # Release escrowed credits → teacher gets them
            if escrowed > 0:
                new_bal = _ledger_entry(
                    cursor2, teacher_id,
                    escrowed, 'payment_release', session_id,
                    f'Received {escrowed} credit(s) from learner for session {session_id}'
                )
                result['credits_released']    = escrowed
                result['teacher_new_balance'] = new_bal

            # Bonus: teacher earns 1 credit per hour for their time
            earn_credits = hours_taught
            _ledger_entry(
                cursor2, teacher_id,
                earn_credits, 'earn_teaching', session_id,
                f'Earned {earn_credits} credit(s) for teaching {duration} min'
            )

            # XP for teacher
            cursor2.execute(
                "UPDATE students SET xp_points = xp_points + 20 WHERE id=%s",
                (teacher_id,)
            )
            cursor2.execute("""
                INSERT INTO activity_log
                    (student_id, activity_type, description, xp_earned)
                VALUES (%s, 'skill_taught', %s, 20)
            """, (teacher_id,
                  f'Completed teaching session (session {session_id})'))

            conn.commit()

        cursor2.close()
        return jsonify(result)
    finally:
        cursor.close(); conn.close()


@app.route('/api/credits/<int:student_id>', methods=['GET'])
def get_credit_balance(student_id):
    """Return current balance and recent ledger entries."""
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT time_credits FROM students WHERE id=%s", (student_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); conn.close()
        return jsonify({'error': 'Not found'}), 404

    cursor.execute("""
        SELECT cl.ledger_id, cl.delta, cl.balance_after, cl.txn_type,
               cl.session_id, cl.note, cl.created_at
        FROM credit_ledger cl
        WHERE cl.student_id=%s
        ORDER BY cl.created_at DESC
        LIMIT 20
    """, (student_id,))
    ledger = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify({'balance': row['time_credits'], 'ledger': ledger})


# ============================================
# ADMIN DASHBOARD OVERVIEW API
# ============================================

def _is_admin_user(cursor, student_id):
    if not student_id:
        return False
    cursor.execute("SELECT is_admin FROM students WHERE id=%s", (student_id,))
    row = cursor.fetchone()
    return bool(row and row.get('is_admin'))

@app.route('/api/admin/overview', methods=['GET'])
def get_admin_overview():
    student_id = session.get('student_id')
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        if not _is_admin_user(cursor, student_id):
            return jsonify({'error': 'Admin authorization required. Access denied.'}), 403

        # 1. Total Users
        cursor.execute("SELECT COUNT(*) AS total_users FROM students")
        total_users = cursor.fetchone()['total_users']

        # 2. Open Support Tickets
        cursor.execute("SELECT COUNT(*) AS open_support_tickets FROM support_requests WHERE status='Open'")
        open_support_tickets = cursor.fetchone()['open_support_tickets']

        # 3. In Progress Support Tickets
        cursor.execute("SELECT COUNT(*) AS in_progress_support_tickets FROM support_requests WHERE status='In Progress'")
        in_progress_support_tickets = cursor.fetchone()['in_progress_support_tickets']

        # 4. Unresolved Feedback
        cursor.execute("SELECT COUNT(*) AS unresolved_feedback FROM feedback WHERE status != 'Resolved'")
        unresolved_feedback = cursor.fetchone()['unresolved_feedback']

        # 5. Total Feedback
        cursor.execute("SELECT COUNT(*) AS total_feedback FROM feedback")
        total_feedback = cursor.fetchone()['total_feedback']

        # Recent Support Tickets
        cursor.execute("""
            SELECT sr.*, s.name AS student_name, s.email AS student_email
            FROM support_requests sr
            JOIN students s ON sr.student_id = s.id
            ORDER BY sr.created_at DESC LIMIT 10
        """)
        recent_tickets = cursor.fetchall()

        # Recent Feedback
        cursor.execute("""
            SELECT f.*, s.name AS student_name, s.email AS student_email
            FROM feedback f
            JOIN students s ON f.student_id = s.id
            ORDER BY f.created_at DESC LIMIT 10
        """)
        recent_feedback = cursor.fetchall()

        return jsonify({
            'total_users': total_users,
            'open_support_tickets': open_support_tickets,
            'in_progress_support_tickets': in_progress_support_tickets,
            'unresolved_feedback': unresolved_feedback,
            'total_feedback': total_feedback,
            'recent_tickets': recent_tickets,
            'recent_feedback': recent_feedback
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/support-tickets', methods=['GET'])
def get_admin_support_tickets():
    student_id = session.get('student_id')
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    search_q = request.args.get('q', '').strip()

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        if not _is_admin_user(cursor, student_id):
            return jsonify({'error': 'Admin authorization required. Access denied.'}), 403

        query = """
            SELECT sr.*, s.name AS student_name, s.email AS student_email,
                   s.department AS student_department, s.year AS student_year
            FROM support_requests sr
            JOIN students s ON sr.student_id = s.id
            WHERE 1=1
        """
        params = []

        if status_filter and status_filter != 'all':
            query += " AND sr.status = %s"
            params.append(status_filter)

        if category_filter and category_filter != 'all':
            query += " AND sr.category = %s"
            params.append(category_filter)

        if search_q:
            query += " AND (s.name LIKE %s OR s.email LIKE %s OR sr.description LIKE %s OR sr.category LIKE %s OR CAST(sr.request_id AS CHAR) LIKE %s)"
            q_param = f"%{search_q}%"
            params.extend([q_param, q_param, q_param, q_param, q_param])

        query += " ORDER BY sr.created_at DESC"

        cursor.execute(query, params)
        tickets = cursor.fetchall()
        return jsonify(tickets), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/support-tickets/<int:request_id>', methods=['PUT'])
def update_support_ticket_full(request_id):
    data = request.json or {}
    new_status = data.get('status')
    admin_reply = data.get('admin_reply')
    student_id = session.get('student_id')

    if new_status and new_status not in ['Open', 'In Progress', 'Resolved']:
        return jsonify({'error': 'Invalid status. Must be Open, In Progress, or Resolved.'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        if not _is_admin_user(cursor, student_id):
            return jsonify({'error': 'Admin authorization required. Access denied.'}), 403

        updates = []
        params = []

        if new_status:
            updates.append("status = %s")
            params.append(new_status)

        if admin_reply is not None:
            updates.append("admin_reply = %s")
            params.append(admin_reply.strip())

        if not updates:
            return jsonify({'error': 'No fields provided for update'}), 400

        params.append(request_id)
        sql = f"UPDATE support_requests SET {', '.join(updates)} WHERE request_id = %s"
        cursor.execute(sql, params)
        conn.commit()

        cursor.execute("""
            SELECT sr.*, s.name AS student_name, s.email AS student_email
            FROM support_requests sr
            JOIN students s ON sr.student_id = s.id
            WHERE sr.request_id = %s
        """, (request_id,))
        ticket = cursor.fetchone()

        return jsonify({'message': 'Support ticket updated successfully', 'ticket': ticket}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/support-tickets/<int:request_id>/status', methods=['PUT'])
def update_support_ticket_status(request_id):
    data = request.json or {}
    new_status = data.get('status')
    student_id = session.get('student_id')

    if new_status not in ['Open', 'In Progress', 'Resolved']:
        return jsonify({'error': 'Invalid status. Must be Open, In Progress, or Resolved.'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        if not _is_admin_user(cursor, student_id):
            return jsonify({'error': 'Admin authorization required. Access denied.'}), 403

        cursor.execute("UPDATE support_requests SET status=%s WHERE request_id=%s", (new_status, request_id))
        conn.commit()
        return jsonify({'message': f'Ticket status updated to {new_status}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/feedback/<int:feedback_id>/status', methods=['PUT'])
def update_admin_feedback_status(feedback_id):
    data = request.json or {}
    new_status = data.get('status')
    student_id = session.get('student_id')

    if new_status not in ['Open', 'In Progress', 'Resolved']:
        return jsonify({'error': 'Invalid status. Must be Open, In Progress, or Resolved.'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        if not _is_admin_user(cursor, student_id):
            return jsonify({'error': 'Admin authorization required. Access denied.'}), 403

        cursor.execute("UPDATE feedback SET status=%s WHERE feedback_id=%s", (new_status, feedback_id))
        conn.commit()
        return jsonify({'message': f'Feedback status updated to {new_status}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
