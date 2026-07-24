-- ============================================
-- Student Skills Exchange - JOIN Query Examples
-- (For Viva Demonstration)
-- ============================================

USE student_skill_exchange;

-- ============================================
-- QUERY 1: List all students with skills they can TEACH
-- (JOIN: students + student_skills + skills)
-- ============================================
SELECT 
    s.name AS Student,
    s.department,
    s.year AS Year,
    sk.skill_name AS Teaches
FROM students s
JOIN student_skills ss ON s.id = ss.student_id
JOIN skills sk ON ss.skill_id = sk.skill_id
WHERE ss.type = 'teach'
ORDER BY s.name;

-- ============================================
-- QUERY 2: List all students with skills they want to LEARN
-- ============================================
SELECT 
    s.name AS Student,
    s.department,
    sk.skill_name AS WantsToLearn
FROM students s
JOIN student_skills ss ON s.id = ss.student_id
JOIN skills sk ON ss.skill_id = sk.skill_id
WHERE ss.type = 'learn'
ORDER BY s.name;

-- ============================================
-- QUERY 3: Find students who can teach a specific skill (e.g., Python)
-- ============================================
SELECT 
    s.name, s.email, s.department, s.year
FROM students s
JOIN student_skills ss ON s.id = ss.student_id
JOIN skills sk ON ss.skill_id = sk.skill_id
WHERE sk.skill_name = 'Python' AND ss.type = 'teach';

-- ============================================
-- QUERY 4: Show all exchange requests with sender, receiver, skill, and status
-- (JOIN: exchange_requests + students (x2) + skills)
-- ============================================
SELECT 
    er.request_id,
    s1.name AS Sender,
    s2.name AS Receiver,
    sk.skill_name AS Skill,
    er.status,
    er.created_at
FROM exchange_requests er
JOIN students s1 ON er.sender_id = s1.id
JOIN students s2 ON er.receiver_id = s2.id
JOIN skills sk ON er.skill_id = sk.skill_id
ORDER BY er.created_at DESC;

-- ============================================
-- QUERY 5: Show all messages with sender and receiver names
-- ============================================
SELECT 
    m.message_id,
    s1.name AS From_Student,
    s2.name AS To_Student,
    m.message,
    m.timestamp
FROM messages m
JOIN students s1 ON m.sender_id = s1.id
JOIN students s2 ON m.receiver_id = s2.id
ORDER BY m.timestamp DESC;

-- ============================================
-- QUERY 6: Count how many skills each student can teach
-- ============================================
SELECT 
    s.name,
    COUNT(ss.skill_id) AS Skills_Teaching
FROM students s
LEFT JOIN student_skills ss ON s.id = ss.student_id AND ss.type = 'teach'
GROUP BY s.id, s.name
ORDER BY Skills_Teaching DESC;

-- ============================================
-- QUERY 7: Find matching pairs - students who can teach what others want to learn
-- ============================================
SELECT 
    teacher.name AS Teacher,
    learner.name AS Learner,
    sk.skill_name AS Skill
FROM student_skills teach_ss
JOIN student_skills learn_ss ON teach_ss.skill_id = learn_ss.skill_id
JOIN students teacher ON teach_ss.student_id = teacher.id
JOIN students learner ON learn_ss.student_id = learner.id
JOIN skills sk ON teach_ss.skill_id = sk.skill_id
WHERE teach_ss.type = 'teach'
  AND learn_ss.type = 'learn'
  AND teach_ss.student_id != learn_ss.student_id
ORDER BY sk.skill_name;

-- ============================================
-- QUERY 8: Full student profile with all skills
-- ============================================
SELECT 
    s.name,
    s.email,
    s.department,
    s.year,
    GROUP_CONCAT(CASE WHEN ss.type='teach' THEN sk.skill_name END ORDER BY sk.skill_name SEPARATOR ', ') AS Teaches,
    GROUP_CONCAT(CASE WHEN ss.type='learn' THEN sk.skill_name END ORDER BY sk.skill_name SEPARATOR ', ') AS Wants_To_Learn
FROM students s
LEFT JOIN student_skills ss ON s.id = ss.student_id
LEFT JOIN skills sk ON ss.skill_id = sk.skill_id
GROUP BY s.id, s.name, s.email, s.department, s.year;

-- ============================================
-- QUERY 9: Pending exchange requests for a specific student (id=1)
-- ============================================
SELECT 
    er.request_id,
    s.name AS From_Student,
    sk.skill_name AS Requested_Skill,
    er.status,
    er.created_at
FROM exchange_requests er
JOIN students s ON er.sender_id = s.id
JOIN skills sk ON er.skill_id = sk.skill_id
WHERE er.receiver_id = 1 AND er.status = 'pending';

-- ============================================
-- QUERY 10: Most popular skills (by number of learners)
-- ============================================
SELECT 
    sk.skill_name,
    COUNT(ss.student_id) AS Learners
FROM skills sk
JOIN student_skills ss ON sk.skill_id = ss.skill_id
WHERE ss.type = 'learn'
GROUP BY sk.skill_id, sk.skill_name
ORDER BY Learners DESC;
