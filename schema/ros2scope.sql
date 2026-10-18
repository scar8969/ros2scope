-- 🤖 ros2-dash schema
CREATE TABLE topics(id INTEGER PRIMARY KEY, name TEXT UNIQUE, type TEXT, rate INTEGER DEFAULT 10);
CREATE TABLE recordings(id INTEGER PRIMARY KEY, name TEXT, topics_json TEXT DEFAULT '[]', status TEXT DEFAULT 'recording', size INTEGER DEFAULT 0, started_at DATETIME, file_path TEXT);
