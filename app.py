import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

DATABASE = 'database.db'

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change to a strong secret key

# ------------------- Helpers -------------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def admin_check(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return admin_check

def get_election_info():
    db = get_db()
    election = db.execute("SELECT * FROM elections WHERE id = 1").fetchone()
    db.close()
    return election

def get_vote_by_id(vote_id):
    db = get_db()
    vote = db.execute('''
        SELECT v.id, v.student_regno, c.name AS candidate_name
        FROM ballots v
        JOIN candidates c ON v.candidate_id = c.id
        WHERE v.id = ?
    ''', (vote_id,)).fetchone()
    db.close()
    if vote:
        return dict(vote)
    return None

def delete_vote(vote_id):
    db = get_db()
    db.execute('DELETE FROM ballots WHERE id = ?', (vote_id,))
    db.commit()
    db.close()

def log_audit_entry(action, user, details, timestamp):
    db = get_db()
    db.execute('''
        INSERT INTO audit_log (action, user, details, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (action, user, details, timestamp))
    db.commit()
    db.close()

from functools import wraps
from flask import session, redirect, url_for, flash

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session.get('role') != 'student':
            flash("Please log in as a student to access this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------- Routes -------------------


@app.route('/', endpoint='home')
def home():
    if 'user' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_regno = request.form['regno']
        password = request.form['password']

        db = get_db()
        user = db.execute("SELECT * FROM students WHERE regno = ?", (user_regno,)).fetchone()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['user'] = user['regno']
            session['name'] = user['name']
            session['course'] = user['course']
            session['batch'] = user['batch']
            session['voted'] = user['voted']
            session['role'] = 'admin' if user_regno == 'admin' else 'student'

            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            error = "Invalid registration number or password"

    return render_template('login.html', error=error, body_class='login-page')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -------- Student Dashboard & Voting --------

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    db = get_db()
    election = get_election_info()

    now = datetime.now()
    start = datetime.strptime(election['start_date'], "%Y-%m-%dT%H:%M")
    end = datetime.strptime(election['deadline'], "%Y-%m-%dT%H:%M")

    remaining = (end - now).total_seconds()
    started = now >= start

    leaders = db.execute("""
        SELECT p.name AS position, c.name AS candidate, COUNT(b.id) as votes
        FROM positions p
        JOIN candidates c ON p.id = c.position_id
        LEFT JOIN ballots b ON c.id = b.candidate_id
        GROUP BY p.id, c.id
        ORDER BY p.id, votes DESC
    """).fetchall()
    db.close()

    return render_template('student_dashboard.html',
                           election=election,
                           remaining=remaining,
                           started=started,
                           leaders=leaders,
                           session=session)


@app.route('/vote')
@login_required
def vote():
    if session.get('voted'):
        return redirect(url_for('ballot_summary'))

    db = get_db()
    positions = db.execute("SELECT * FROM positions").fetchall()
    candidates = db.execute("SELECT * FROM candidates").fetchall()
    db.close()

    # Group candidates by position
    grouped = {}
    for pos in positions:
        grouped[pos['name']] = [c for c in candidates if c['position_id'] == pos['id']]

    return render_template('vote.html', grouped=grouped)

@app.route('/submit_vote', methods=['POST'])
@login_required
def submit_vote():
    db = get_db()
    student = session['user']
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for key, value in request.form.items():
        if key.startswith("position_"):
            position_id = key.split("_")[1]
            candidate_id = value
            db.execute("INSERT INTO ballots (student_regno, position_id, candidate_id, timestamp) VALUES (?, ?, ?, ?)",
                       (student, position_id, candidate_id, timestamp))

    db.execute("UPDATE students SET voted = 1 WHERE regno = ?", (student,))
    db.commit()

    db.execute("INSERT INTO audit_log (user, action, details, timestamp) VALUES (?, ?, ?, ?)",
               (student, 'Vote Cast', 'Ballot submitted', timestamp))
    db.commit()
    db.close()

    session['voted'] = 1
    return redirect(url_for('ballot_summary'))

@app.route('/ballot_summary')
@login_required
def ballot_summary():
    db = get_db()
    student = session['user']

    summary = db.execute("""
        SELECT p.name as position, c.name as candidate
        FROM ballots b
        JOIN candidates c ON b.candidate_id = c.id
        JOIN positions p ON c.position_id = p.id
        WHERE b.student_regno = ?
    """, (student,)).fetchall()
    db.close()

    # Fixed template name here
    return render_template('ballot_summary.html', summary=summary)

# -------- Admin Dashboard and Management --------

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    students = db.execute("SELECT * FROM students").fetchall()
    total_voters = len(students)
    voted = sum([1 for s in students if s['voted']])
    election = get_election_info()
    db.close()
    return render_template('dashboard.html', students=students, total=total_voters, voted=voted, election=election)

@app.route('/manage_positions', methods=['GET', 'POST'])
@admin_required
def manage_positions():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        pos_id = request.form.get('id')

        if action == 'add' and name:
            db.execute("INSERT INTO positions (name) VALUES (?)", (name,))
        elif action == 'edit' and name and pos_id:
            db.execute("UPDATE positions SET name = ? WHERE id = ?", (name, pos_id))
        elif action == 'delete' and pos_id:
            db.execute("DELETE FROM positions WHERE id = ?", (pos_id,))

        db.commit()
        db.close()
        return redirect(url_for('manage_positions'))

    positions = db.execute("SELECT * FROM positions").fetchall()
    db.close()
    return render_template('positions.html', positions=positions)

@app.route('/manage_candidates', methods=['GET', 'POST'])
@admin_required
def manage_candidates():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        student_regno = request.form.get('student_regno')
        pos_id = request.form.get('position_id')
        cand_id = request.form.get('id')

        if action == 'add' and student_regno and pos_id:
            student = db.execute("SELECT * FROM students WHERE regno = ?", (student_regno,)).fetchone()
            if student:
                db.execute("INSERT INTO candidates (name, position_id, student_regno) VALUES (?, ?, ?)",
                           (student['name'], pos_id, student_regno))
        elif action == 'edit' and student_regno and pos_id and cand_id:
            student = db.execute("SELECT * FROM students WHERE regno = ?", (student_regno,)).fetchone()
            if student:
                db.execute("UPDATE candidates SET name = ?, position_id = ?, student_regno = ? WHERE id = ?",
                           (student['name'], pos_id, student_regno, cand_id))
        elif action == 'delete' and cand_id:
            db.execute("DELETE FROM candidates WHERE id = ?", (cand_id,))

        db.commit()
        db.close()
        return redirect(url_for('manage_candidates'))

    positions = db.execute("SELECT * FROM positions").fetchall()
    candidates = db.execute("""
        SELECT c.*, p.name as position, s.avatar as avatar
        FROM candidates c
        JOIN positions p ON c.position_id = p.id
        LEFT JOIN students s ON s.regno = c.student_regno
    """).fetchall()
    db.close()
    return render_template('manage_candidates.html', positions=positions, candidates=candidates)


@app.route('/election_settings', methods=['GET', 'POST'])
@admin_required
def election_settings():
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title')
        start_date = request.form.get('start')
        deadline = request.form.get('deadline')

        if title and start_date and deadline:
            db.execute("UPDATE elections SET title = ?, start_date = ?, deadline = ? WHERE id = 1",
                       (title, start_date, deadline))
            db.commit()
            db.close()
            flash('Election settings updated.')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Please fill all fields.')

    election = get_election_info()
    return render_template('election_settings.html', election=election)

@app.route('/results')
@login_required
def results():
    db = get_db()
    data = db.execute("""
    SELECT p.name as position, c.name as candidate, COUNT(b.id) as votes
    FROM positions p
    JOIN candidates c ON p.id = c.position_id
    LEFT JOIN ballots b ON c.id = b.candidate_id AND b.position_id = p.id
    GROUP BY p.id, c.id
    ORDER BY p.id, votes DESC
""").fetchall()


    db.close()

    results_by_position = {}
    for row in data:
        pos = row['position']
        if pos not in results_by_position:
            results_by_position[pos] = []
        results_by_position[pos].append({'candidate': row['candidate'], 'votes': row['votes']})

    return render_template('results.html', results=results_by_position)

@app.route('/audit_log')
@admin_required
def audit_log():
    db = get_db()
    logs = db.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
    db.close()
    return render_template('audit_log.html', logs=logs)

@app.route('/admin/delete_vote/<int:vote_id>', methods=['GET', 'POST'])
@admin_required
def admin_delete_vote(vote_id):
    vote = get_vote_by_id(vote_id)
    if not vote:
        flash('Vote not found.')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        remark = request.form.get('remark', '').strip()
        if not remark:
            flash('Remark is required to delete a vote.')
            return redirect(request.url)

        delete_vote(vote_id)
        log_audit_entry(
            action='Delete Vote',
            user=session.get('user'),
            details=f"Deleted vote ID {vote_id}. Remark: {remark}",
            timestamp=datetime.now()
        )
        flash('Vote deleted successfully.')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_delete_vote.html', vote=vote)

@app.route('/add_student', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        course = request.form.get('course')
        batch = request.form.get('batch')

        if not (name and course and batch):
            flash("All fields are required.")
            return redirect(url_for('add_student'))

        db = get_db()
        prefix = f"{course.upper()}{batch}_"
        last = db.execute("SELECT regno FROM students WHERE regno LIKE ? ORDER BY regno DESC LIMIT 1", (prefix + '%',)).fetchone()
        if last:
            try:
                last_num = int(last['regno'].split('_')[-1])
                next_num = last_num + 1
            except:
                next_num = 1001
        else:
            next_num = 1001

        new_regno = f"{prefix}{next_num}"
        default_pw_hash = generate_password_hash("voter123")

        db.execute("INSERT INTO students (regno, name, course, batch, password, voted) VALUES (?, ?, ?, ?, ?, 0)",
                   (new_regno, name, course, batch, default_pw_hash))
        db.commit()
        db.close()

        flash(f"Student '{name}' added with Reg No: {new_regno} and default password 'voter123'.")
        return redirect(url_for('admin_dashboard'))

    return render_template('add_student.html')


@app.route('/edit_student/<regno>', methods=['GET', 'POST'])
@admin_required
def edit_student(regno):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE regno = ?", (regno,)).fetchone()

    if not student:
        flash("Student not found.")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        course = request.form.get('course')
        batch = request.form.get('batch')
        if name and course and batch:
            db.execute("UPDATE students SET name = ?, course = ?, batch = ? WHERE regno = ?",
                       (name, course, batch, regno))
            db.commit()
            db.close()
            flash("Student updated.")
            return redirect(url_for('admin_dashboard'))

    db.close()
    return render_template('edit_student.html', student=student)


@app.route('/delete_student/<regno>', methods=['POST'])
@admin_required
def delete_student(regno):
    db = get_db()
    db.execute("DELETE FROM students WHERE regno = ?", (regno,))
    db.commit()
    db.close()
    flash(f"Deleted student: {regno}")
    return redirect(url_for('admin_dashboard'))

@app.route('/reset_vote/<regno>', methods=['POST'])
@admin_required
def reset_vote(regno):
    db = get_db()

    db.execute("DELETE FROM ballots WHERE student_regno = ?", (regno,))
    db.execute("UPDATE students SET voted = 0 WHERE regno = ?", (regno,))
    db.commit()

    log_audit_entry(
        action="Reset Vote",
        user=session.get("user"),
        details=f"Vote reset for student: {regno}",
        timestamp=datetime.now()
    )

    flash(f"Vote reset for {regno}.")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/votes')
@admin_required
def admin_votes():
    db = get_db()

    # Fetch vote count per candidate (only for existing candidates with valid positions)
    vote_data = db.execute("""
        SELECT p.name AS position, c.name AS candidate, COUNT(b.id) AS votes
        FROM candidates c
        JOIN positions p ON c.position_id = p.id
        LEFT JOIN ballots b ON c.id = b.candidate_id
        GROUP BY c.id
        ORDER BY p.name, votes DESC
    """).fetchall()

    # Fetch individual ballots — only those where candidate still exists
    ballots = db.execute("""
        SELECT b.id, b.student_regno, c.name as candidate, p.name as position, b.timestamp
        FROM ballots b
        JOIN candidates c ON b.candidate_id = c.id
        JOIN positions p ON b.position_id = p.id
        ORDER BY b.timestamp DESC
    """).fetchall()

    db.close()

    return render_template('admin_votes.html', vote_data=vote_data, ballots=ballots)

@app.route('/live_vote_count')
@login_required
def live_vote_count():
    db = get_db()
    data = db.execute("""
        SELECT p.name as position, c.name as candidate, COUNT(b.id) as votes
        FROM positions p
        JOIN candidates c ON p.id = c.position_id
        LEFT JOIN ballots b ON c.id = b.candidate_id AND b.position_id = p.id
        GROUP BY p.id, c.id
        ORDER BY p.id, votes DESC
    """).fetchall()
    db.close()

    results_by_position = {}
    for row in data:
        pos = row['position']
        if pos not in results_by_position:
            results_by_position[pos] = []
        results_by_position[pos].append({'candidate': row['candidate'], 'votes': row['votes']})

    return render_template('live_vote_count.html', results=results_by_position)

@app.route('/student/live_vote_count')
@login_required
def student_live_vote_count():
    db = get_db()
    data = db.execute("""
        SELECT p.name as position, c.name as candidate, COUNT(b.id) as votes
        FROM positions p
        LEFT JOIN candidates c ON p.id = c.position_id
        LEFT JOIN ballots b ON c.id = b.candidate_id AND b.position_id = p.id
        GROUP BY p.id, c.id
        ORDER BY p.id, votes DESC
    """).fetchall()
    db.close()

    # Structure data grouped by position for template
    results_by_position = {}
    for row in data:
        pos = row['position']
        if pos not in results_by_position:
            results_by_position[pos] = []
        results_by_position[pos].append({'candidate': row['candidate'], 'votes': row['votes']})

    return render_template('live_vote_count.html', results=results_by_position)

@app.route('/student/profile')
@student_required
def student_profile():
    election = get_election_info()
    return render_template('student_profile.html', election=election)
@app.route('/student/change_password', methods=['POST'])
@student_required
def change_password():
    old = request.form.get('old_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')

    if new != confirm:
        flash("New passwords do not match.")
        return redirect(url_for('student_profile'))

    db = get_db()
    user = db.execute("SELECT * FROM students WHERE regno = ?", (session['user'],)).fetchone()

    if not check_password_hash(user['password'], old):
        flash("Current password is incorrect.")
        return redirect(url_for('student_profile'))

    hashed_new = generate_password_hash(new)
    db.execute("UPDATE students SET password = ? WHERE regno = ?", (hashed_new, session['user']))
    db.commit()
    db.close()

    flash("Password updated successfully.")
    return redirect(url_for('student_profile'))

@app.route('/admin/reset_password/<regno>', methods=['POST'])
@admin_required
def admin_reset_password(regno):
    from werkzeug.security import generate_password_hash

    db = get_db()
    db.execute("UPDATE students SET password = ? WHERE regno = ?", (generate_password_hash("voter123"), regno))
    db.commit()
    db.close()

    flash(f"Password for {regno} has been reset to default ('voter123').")
    return redirect(url_for('admin_dashboard'))
@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'avatar' in request.files:
        file = request.files['avatar']
        filename = secure_filename(file.filename)
        # Save file logic (e.g., uploads/avatars/user123.jpg)
        filepath = os.path.join('static/uploads/avatars', filename)
        file.save(filepath)

        # Update session (and DB if needed)
        session['avatar'] = f'uploads/avatars/{filename}'

        flash('Avatar updated successfully.')
    return redirect(url_for('student_profile'))

# ----------- Main -----------

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        from schema import create_schema
        create_schema()
    app.run(debug=True)
