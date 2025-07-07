import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_schema():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Students table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            regno TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            batch TEXT NOT NULL,
            password TEXT NOT NULL,
            voted INTEGER DEFAULT 0
        )
    ''')

    # Elections table
    c.execute('''
        CREATE TABLE IF NOT EXISTS elections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_date TEXT,
            deadline TEXT
        )
    ''')

    # Positions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    # Candidates table (with position)
    c.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position_id INTEGER NOT NULL,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        )
    ''')

    # Ballots: who voted, for what position, selected which candidate
    c.execute('''
        CREATE TABLE IF NOT EXISTS ballots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_regno TEXT NOT NULL,
            position_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (student_regno) REFERENCES students(regno),
            FOREIGN KEY (position_id) REFERENCES positions(id),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')

    # Audit logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TEXT NOT NULL
        )
    ''')

    # Settings (for legacy use)
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            deadline TEXT
        )
    ''')

    # Insert default election if missing
    c.execute("SELECT * FROM elections WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO elections (id, title, start_date, deadline) VALUES (1, 'Class Representative Election', ?, ?)",
                  (datetime.now().strftime("%Y-%m-%dT%H:%M"), '2025-12-31T23:59'))

    # Insert default settings row
    c.execute("INSERT OR IGNORE INTO settings (id, deadline) VALUES (1, '')")

    # Insert sample positions
    c.execute("INSERT OR IGNORE INTO positions (id, name) VALUES (1, 'President'), (2, 'Secretary')")

    # Insert sample candidates
    c.execute("INSERT OR IGNORE INTO candidates (id, name, position_id) VALUES (?, ?, ?)", (1, 'John Doe', 1))
    c.execute("INSERT OR IGNORE INTO candidates (id, name, position_id) VALUES (?, ?, ?)", (2, 'Jane Smith', 1))
    c.execute("INSERT OR IGNORE INTO candidates (id, name, position_id) VALUES (?, ?, ?)", (3, 'Emily Davis', 2))

    # Insert sample students
    students = [
        ('S1001', 'Alice Johnson', 'Computer Science', '2023', generate_password_hash('alice123')),
        ('S1002', 'Bob Smith', 'IT', '2023', generate_password_hash('bob123')),
        ('S1003', 'Charlie Lee', 'ECE', '2022', generate_password_hash('charlie123'))
    ]
    for s in students:
        c.execute("INSERT OR IGNORE INTO students (regno, name, course, batch, password) VALUES (?, ?, ?, ?, ?)", s)

    # Insert admin user
    admin_regno = 'admin'
    admin_password_hash = generate_password_hash('admin')
    c.execute("INSERT OR IGNORE INTO students (regno, name, course, batch, password, voted) VALUES (?, ?, ?, ?, ?, ?)",
              (admin_regno, 'Administrator', '', '', admin_password_hash, 0))

    conn.commit()
    conn.close()
    print("✅ Database initialized with election, positions, candidates, students, and admin.")

if __name__ == "__main__":
    create_schema()
