CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    keywords TEXT NOT NULL,
    language TEXT NOT NULL,
    emotion TEXT NOT NULL,
    generated_story TEXT NOT NULL,
    audio_file TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_stories_user_created
ON stories (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_users_email
ON users (email);
