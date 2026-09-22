-- ============================================
-- Student Skills Exchange - Skills Catalogue
-- ============================================
-- NOTE: Fake/seeded student data has been removed.
-- Only the skills catalogue is seeded here — these
-- are legitimate app reference data, not test users.
-- ============================================

USE student_skill_exchange;

-- Insert Skills (catalogue only — no student/user data)
INSERT IGNORE INTO skills (skill_name) VALUES
('Python'),
('Java'),
('Web Development'),
('Machine Learning'),
('Data Structures'),
('SQL'),
('React'),
('Node.js'),
('C++'),
('UI/UX Design'),
('Android Development'),
('Cybersecurity'),
('Cloud Computing'),
('Git & GitHub'),
('Mathematics');
