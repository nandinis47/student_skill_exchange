# 🎓 Student Skills Exchange

A mini DBMS project where students can share skills they can teach and skills they want to learn.

---

## 📁 Folder Structure

```
student_skill_exchange/
│
├── backend/
│   ├── app.py              ← Flask backend (API server)
│   └── requirements.txt    ← Python dependencies
│
├── database/
│   ├── schema.sql          ← CREATE TABLE statements
│   ├── sample_data.sql     ← INSERT sample records
│   └── queries.sql         ← JOIN query examples for viva
│
├── frontend/
│   ├── css/
│   │   └── style.css       ← Global styles (blue/white theme)
│   ├── js/
│   │   └── api.js          ← API helper functions
│   ├── index.html          ← Login / Register page
│   ├── dashboard.html      ← Home dashboard
│   ├── skills.html         ← Add/manage skills
│   ├── search.html         ← Search students by skill
│   ├── requests.html       ← Exchange requests
│   ├── messages.html       ← Messaging section
│   ├── profile.html        ← Student profile
│   └── er_diagram.html     ← Visual ER diagram
│
└── README.md
```

---

## ⚙️ Setup Steps

### Quick Start — Run Everything

**Windows:** Just double-click `LAUNCH APP.bat` in the project folder.

This will:
1. Start Flask backend on `http://localhost:5000`
2. Start frontend server on `http://localhost:8080`
3. Open your browser automatically

> ⚠️ **Important:** Always access the app via `http://localhost:8080` — don't double-click the HTML files directly or you'll get network errors.

---

### Manual Setup (if needed)

#### Step 1: MySQL Database Setup

1. Open **MySQL Workbench** or **phpMyAdmin** or the MySQL CLI.
2. Run the schema file:
   ```sql
   source /path/to/database/schema.sql
   ```
3. Load sample data:
   ```sql
   source /path/to/database/sample_data.sql
   ```

### Step 2: Backend Setup (Flask)

1. Make sure **Python 3.8+** is installed.
2. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Open `backend/app.py` and update the DB password:
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'user': 'root',
       'password': 'YOUR_MYSQL_PASSWORD',   # ← change this
       'database': 'student_skill_exchange'
   }
   ```
4. Start the Flask server:
   ```bash
   python app.py
   ```
   The API will run at: `http://localhost:5000`

### Step 3: Frontend

1. Open `frontend/index.html` in any browser.
2. Or use **Live Server** extension in VS Code for best experience.

> **Note:** The Flask backend must be running for the frontend to work.

---

## 🔑 Demo Login

| Email | Password |
|-------|----------|
| aarav@college.edu | pass123 |
| priya@college.edu | pass123 |
| sneha@college.edu | pass123 |

---

## 📄 Pages

| Page | File | Description |
|------|------|-------------|
| Login/Register | `index.html` | Authentication |
| Dashboard | `dashboard.html` | Stats, quick actions, recent requests |
| My Skills | `skills.html` | Add/remove teach & learn skills |
| Search | `search.html` | Find students by skill |
| Requests | `requests.html` | Send/accept/reject exchange requests |
| Messages | `messages.html` | Chat with other students |
| Profile | `profile.html` | View/edit profile |
| ER Diagram | `er_diagram.html` | Visual database diagram |

---

## 🗄️ Database Tables

| Table | Purpose |
|-------|---------|
| `students` | Stores student accounts |
| `skills` | Master list of all skills |
| `student_skills` | Links students to skills (teach/learn) |
| `exchange_requests` | Skill exchange requests between students |
| `messages` | Chat messages between students |

---

## 🔗 Key Relationships

- **students ↔ skills** → Many-to-Many via `student_skills`
- **students → exchange_requests** → One-to-Many (as sender & receiver)
- **students → messages** → One-to-Many (as sender & receiver)
- **skills → exchange_requests** → One-to-Many

---

## 🧪 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register new student |
| POST | `/api/login` | Login |
| POST | `/api/logout` | Logout |
| GET | `/api/students` | Get all students with skills |
| GET | `/api/students/:id` | Get student profile |
| PUT | `/api/students/:id` | Update profile |
| GET | `/api/skills` | Get all skills |
| POST | `/api/skills` | Add new skill |
| POST | `/api/student-skills` | Add skill to student |
| DELETE | `/api/student-skills/:id` | Remove skill from student |
| GET | `/api/search?skill=X&type=teach` | Search students by skill |
| POST | `/api/requests` | Send exchange request |
| GET | `/api/requests/:student_id` | Get requests for student |
| PUT | `/api/requests/:id/status` | Accept/reject request |
| POST | `/api/messages` | Send message |
| GET | `/api/messages/:student_id` | Get messages |
| GET | `/api/stats` | Dashboard statistics |

---

## 🎤 Viva Preparation

### What is this project?
A web-based DBMS mini project where students can register, list skills they can teach or want to learn, search for other students, send exchange requests, and chat — all backed by a normalized MySQL database.

### Key DBMS concepts used:
- **Primary Keys** on all tables
- **Foreign Keys** with `ON DELETE CASCADE`
- **Normalization** — skills stored once in `skills` table, linked via `student_skills`
- **Many-to-Many** relationship resolved with junction table
- **Self-referencing FK** in `exchange_requests` and `messages` (sender/receiver both reference `students`)
- **ENUM** data type for `type` and `status` columns
- **JOIN queries** — up to 4-table JOINs
- **CRUD** — Create, Read, Update, Delete on all entities
- **GROUP_CONCAT** for aggregating skills per student

### Sample JOIN query to explain:
```sql
-- Show all exchange requests with names and skill
SELECT s1.name AS Sender, s2.name AS Receiver,
       sk.skill_name, er.status
FROM exchange_requests er
JOIN students s1 ON er.sender_id = s1.id
JOIN students s2 ON er.receiver_id = s2.id
JOIN skills sk ON er.skill_id = sk.skill_id;
```
This uses a **4-table JOIN** including a **self-join** on the students table.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python Flask |
| Database | MySQL |
| DB Driver | mysql-connector-python |
| CORS | flask-cors |
