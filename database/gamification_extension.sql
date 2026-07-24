-- ============================================
-- Gamification & Advanced Features Extension
-- ============================================

USE student_skill_exchange;

-- Add gamification columns to students
ALTER TABLE students 
ADD COLUMN IF NOT EXISTS xp_points INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS learning_streak INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_activity_date DATE,
ADD COLUMN IF NOT EXISTS daily_goal VARCHAR(200),
ADD COLUMN IF NOT EXISTS avatar_emoji VARCHAR(10) DEFAULT '🎓';

-- Badges table
CREATE TABLE IF NOT EXISTS badges (
    badge_id INT AUTO_INCREMENT PRIMARY KEY,
    badge_name VARCHAR(100) NOT NULL,
    badge_emoji VARCHAR(10),
    description VARCHAR(255),
    xp_required INT DEFAULT 0
);

-- Student badges (earned)
CREATE TABLE IF NOT EXISTS student_badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    badge_id INT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badges(badge_id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_badge (student_id, badge_id)
);

-- Skill progress tracking
CREATE TABLE IF NOT EXISTS skill_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    progress_percent INT DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    hours_spent DECIMAL(5,1) DEFAULT 0,
    last_practiced DATE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_skill_progress (student_id, skill_id)
);

-- Learning sessions (for calendar & tracking)
CREATE TABLE IF NOT EXISTS learning_sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    partner_id INT,
    skill_id INT NOT NULL,
    session_date DATETIME NOT NULL,
    duration_minutes INT DEFAULT 30,
    status ENUM('scheduled', 'completed', 'cancelled') DEFAULT 'scheduled',
    notes TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (partner_id) REFERENCES students(id) ON DELETE SET NULL,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- Activity log
CREATE TABLE IF NOT EXISTS activity_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    activity_type ENUM('skill_learned', 'skill_taught', 'exchange_completed', 'badge_earned', 'milestone') NOT NULL,
    description VARCHAR(255),
    xp_earned INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Insert sample badges
INSERT INTO badges (badge_name, badge_emoji, description, xp_required) VALUES
('Newbie', '🌱', 'Welcome to Skills Exchange!', 0),
('First Exchange', '🤝', 'Completed your first skill exchange', 10),
('Quick Learner', '⚡', 'Learned 3 skills', 50),
('Master Teacher', '👨‍🏫', 'Taught 5 different skills', 100),
('Streak Master', '🔥', 'Maintained a 7-day learning streak', 75),
('Social Butterfly', '🦋', 'Connected with 10 students', 60),
('Knowledge Seeker', '📚', 'Learning 5 skills simultaneously', 40),
('Community Hero', '🏆', 'Helped 20+ students', 200);

-- Give all existing students the Newbie badge
INSERT IGNORE INTO student_badges (student_id, badge_id)
SELECT id, 1 FROM students;

-- Sample skill progress for existing students
INSERT IGNORE INTO skill_progress (student_id, skill_id, progress_percent, hours_spent, last_practiced)
SELECT ss.student_id, ss.skill_id, 
    CASE WHEN ss.type = 'teach' THEN 100 ELSE FLOOR(RAND() * 70) + 20 END,
    FLOOR(RAND() * 50) + 5,
    CURDATE() - INTERVAL FLOOR(RAND() * 30) DAY
FROM student_skills ss
WHERE ss.type = 'learn'
LIMIT 15;

-- Sample learning sessions
INSERT INTO learning_sessions (student_id, partner_id, skill_id, session_date, duration_minutes, status)
VALUES
(1, 2, 3, DATE_ADD(NOW(), INTERVAL 5 HOUR), 60, 'scheduled'),
(2, 3, 1, DATE_ADD(NOW(), INTERVAL 1 DAY), 45, 'scheduled'),
(4, 1, 4, DATE_SUB(NOW(), INTERVAL 2 DAY), 90, 'completed');

-- Sample activity log
INSERT INTO activity_log (student_id, activity_type, description, xp_earned) VALUES
(1, 'badge_earned', 'Earned Newbie badge', 10),
(1, 'exchange_completed', 'Completed exchange with Priya', 15),
(2, 'skill_taught', 'Taught Web Development to Rohan', 20),
(3, 'skill_learned', 'Made progress in Python', 10),
(4, 'badge_earned', 'Earned Quick Learner badge', 25);

-- Update XP for existing students (sample)
UPDATE students SET xp_points = FLOOR(RAND() * 150) + 20, 
    learning_streak = FLOOR(RAND() * 10),
    last_activity_date = CURDATE() - INTERVAL FLOOR(RAND() * 5) DAY,
    daily_goal = CASE 
        WHEN id % 3 = 0 THEN 'Learn Python for 30 minutes'
        WHEN id % 3 = 1 THEN 'Complete React tutorial'
        ELSE 'Practice Data Structures'
    END
WHERE id <= 8;
