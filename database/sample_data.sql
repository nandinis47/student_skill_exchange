-- ============================================
-- Student Skills Exchange - Sample Data
-- ============================================

USE student_skill_exchange;

-- Insert Skills
INSERT INTO skills (skill_name) VALUES
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

-- Passwords are SHA-256 hash of 'pass123'
-- Hash: 9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c
INSERT INTO students (name, email, password, department, year) VALUES
('Aarav Sharma',    'aarav@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Computer Science', 2),
('Priya Patel',     'priya@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Information Technology', 3),
('Rohan Mehta',     'rohan@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Electronics', 2),
('Sneha Iyer',      'sneha@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Computer Science', 4),
('Karan Verma',     'karan@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Mechanical', 1),
('Divya Nair',      'divya@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Information Technology', 3),
('Arjun Singh',     'arjun@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Computer Science', 2),
('Meera Joshi',     'meera@college.edu',   '9b8769a4a742959a2d0298c36fb70623f2dfacda8436237df08d8dfd5b37374c', 'Data Science', 4);

-- Student Skills (teach)
INSERT INTO student_skills (student_id, skill_id, type) VALUES
(1, 1, 'teach'),   -- Aarav teaches Python
(1, 5, 'teach'),   -- Aarav teaches Data Structures
(2, 3, 'teach'),   -- Priya teaches Web Development
(2, 7, 'teach'),   -- Priya teaches React
(3, 9, 'teach'),   -- Rohan teaches C++
(4, 4, 'teach'),   -- Sneha teaches Machine Learning
(4, 6, 'teach'),   -- Sneha teaches SQL
(5, 15,'teach'),   -- Karan teaches Mathematics
(6, 10,'teach'),   -- Divya teaches UI/UX Design
(7, 8, 'teach'),   -- Arjun teaches Node.js
(7, 14,'teach'),   -- Arjun teaches Git & GitHub
(8, 4, 'teach'),   -- Meera teaches Machine Learning
(8, 13,'teach');   -- Meera teaches Cloud Computing

-- Student Skills (learn)
INSERT INTO student_skills (student_id, skill_id, type) VALUES
(1, 3, 'learn'),   -- Aarav wants to learn Web Development
(1, 4, 'learn'),   -- Aarav wants to learn Machine Learning
(2, 1, 'learn'),   -- Priya wants to learn Python
(3, 1, 'learn'),   -- Rohan wants to learn Python
(3, 6, 'learn'),   -- Rohan wants to learn SQL
(4, 7, 'learn'),   -- Sneha wants to learn React
(5, 1, 'learn'),   -- Karan wants to learn Python
(5, 6, 'learn'),   -- Karan wants to learn SQL
(6, 4, 'learn'),   -- Divya wants to learn Machine Learning
(7, 4, 'learn'),   -- Arjun wants to learn Machine Learning
(8, 7, 'learn');   -- Meera wants to learn React

-- Exchange Requests
INSERT INTO exchange_requests (sender_id, receiver_id, skill_id, status) VALUES
(1, 2, 3, 'pending'),    -- Aarav requests Priya for Web Dev
(3, 1, 1, 'accepted'),   -- Rohan requests Aarav for Python
(5, 4, 6, 'pending'),    -- Karan requests Sneha for SQL
(6, 8, 4, 'accepted'),   -- Divya requests Meera for ML
(7, 4, 4, 'rejected');   -- Arjun requests Sneha for ML

-- Messages
INSERT INTO messages (sender_id, receiver_id, message) VALUES
(1, 2, 'Hi Priya! Can you help me learn Web Development?'),
(2, 1, 'Sure Aarav! I can teach you React and HTML basics.'),
(3, 1, 'Hey Aarav, when are you free to teach Python?'),
(1, 3, 'I am free on weekends. Lets connect!'),
(6, 8, 'Hi Meera, I accepted your ML exchange. Lets start this week!'),
(8, 6, 'Great! I will share some resources with you.');
