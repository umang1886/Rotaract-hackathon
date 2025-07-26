from flask import Flask, render_template, redirect, url_for, request, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from functools import wraps
import pymysql
import bcrypt
from flask import session, redirect, url_for
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
import os
from wtforms import StringField, PasswordField, SubmitField, SelectField
import uuid  # required for unique filenames



app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ✅ Admin credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"


# ✅ Database connection
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='rotabase',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):  # 🔐 Check if admin is logged in
            return redirect(url_for('admin_login'))  # 🔁 Redirect if not
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ✅ Forms
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    mobile = StringField("Mobile", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")


class MembershipForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    mobile = StringField("Mobile", validators=[DataRequired()])
    semester = SelectField("Semester", choices=[("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"),
                                                ("5", "5"), ("6", "6"), ("7", "7"), ("8", "8")])
    division = SelectField("Division", choices=[("A", "A"), ("B", "B"), ("C", "C")])
    screenshot = FileField("Upload Payment Screenshot", validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField("Submit")


class AnnouncementForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = StringField("Content", validators=[DataRequired()])
    submit = SubmitField("Post Announcement")



# ✅ User Login
@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error = None

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM myuser WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user'] = user['name']
            return redirect(url_for('home'))
        else:
            error = "Invalid email or password"

    return render_template('user/login.html', form=form, error=error)

# ✅ User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        mobile = form.mobile.data  # ✅ new
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM myuser WHERE email=%s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template('register.html', form=form, error="Email already registered.")

        cursor.execute("INSERT INTO myuser (name, email, mobile, password) VALUES (%s, %s, %s, %s)",
               (name, email, mobile, hashed_password))

        conn.commit()
        conn.close()
        return redirect(url_for('login'))

    return render_template('user/register.html', form=form)

# ✅ User Home
@app.route('/home')
def home():
    if 'user' in session:
        return render_template('index.html', username=session['user'])
    else:
        return redirect(url_for('login'))
    


@app.route('/membership', methods=['GET', 'POST'])
@login_required
def membership():
    # 🔐 Only allow logged-in users to access the form
    if 'user' not in session:
        return redirect(url_for('login'))

    form = MembershipForm()
    message = None

    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        mobile = form.mobile.data
        semester = form.semester.data
        division = form.division.data

        # 📸 Handle screenshot upload
        screenshot_file = form.screenshot.data
        if screenshot_file:
            # Use a UUID to prevent filename conflicts
            original_filename = secure_filename(screenshot_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            screenshot_file.save(filepath)
        else:
            unique_filename = ''

        # 💾 Store data in MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO membership (name, email, mobile, semester, division, screenshot)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email, mobile, semester, division, unique_filename))
        conn.commit()
        conn.close()

        message = "Membership submitted successfully!"

    return render_template('user/membership.html', form=form, message=message)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    success = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        message = request.form['message']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO contact (name, email, mobile, message) VALUES (%s, %s, %s, %s)",
                       (name, email, mobile, message))
        conn.commit()
        conn.close()
        success = "Your message has been sent successfully!"

    return render_template('user/contact.html', success=success)


@app.route('/announcements')
@login_required
def view_announcements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    conn.close()
    return render_template('user/announcements.html', announcements=announcements)


@app.route('/events')
def events():
    return render_template('user/events.html')

@app.route('/events/collaboration')
def event_collab():
    return render_template('user/event1.html')


@app.route('/events/oldage')
def oldage():
    return render_template('user/event2.html')

@app.route('/events/education-drive')
def education_drive():
    return render_template('user/event3.html')

@app.route('/events/tree-plantation')
def tree_plantation():
    return render_template('user/event4.html')

@app.route('/events/women-empowerment')
def women_empowerment():
    return render_template('user/event5.html')

@app.route('/member-score')
def member_score():
    members = [
        {
            'name': 'Amit Sharma',
            'scores': ['🌱 Clean Drive', '🩺 Blood Camp', '📚 Book Donation', '🎤 Youth Talk'],
            'percent': '100%'
        },
        {
            'name': 'Sneha Patel',
            'scores': ['🌱 Clean Drive', '📚 Book Donation'],
            'percent': '60%'
        },
        {
            'name': 'Rahul Mehta',
            'scores': ['🩺 Blood Camp'],
            'percent': '25%'
        }
    ]
    return render_template('user/member_score.html', members=members)





# ✅ User Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ✅ Admin Login
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    error = None

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin'] = True  # ✅ Set admin session
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid admin credentials"

    return render_template('admin/admin_login.html', form=form, error=error)

# ✅ Admin Dashboard (Protected)
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total registered users
    cursor.execute("SELECT COUNT(*) AS total_users FROM myuser")
    user_stats = cursor.fetchone()

    # Get total membership submissions
    cursor.execute("SELECT COUNT(*) AS total_members FROM membership")
    member_stats = cursor.fetchone()

    conn.close()

    return render_template('admin/admin_dashboard.html', stats=user_stats, members=member_stats)



# ✅ Registered Users (Protected)
@app.route('/admin/dashboard/users')
@admin_required
def registered_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, mobile FROM myuser")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin/registered_users.html', users=users)

@app.route('/admin/dashboard/members')
@admin_required
def view_members():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM membership")
    members = cursor.fetchall()
    conn.close()
    return render_template('admin/admin_members.html', members=members)

@app.route('/admin/dashboard/contact')
@admin_required
def admin_contact():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contact")
    contacts = cursor.fetchall()
    conn.close()
    return render_template('admin/admin_contact.html', contacts=contacts)

@app.route('/admin/dashboard/announcement', methods=['GET', 'POST'])
@admin_required
def admin_announcement():
    form = AnnouncementForm()
    message = None

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO announcements (title, content) VALUES (%s, %s)", (title, content))
        conn.commit()
        conn.close()

        message = "Announcement posted successfully!"
    
    return render_template('admin/admin_announcement.html', form=form, message=message)

@app.route('/admin/dashboard/members/delete/<int:member_id>', methods=['POST'])
@admin_required
def delete_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete screenshot file (optional)
    cursor.execute("SELECT screenshot FROM membership WHERE id = %s", (member_id,))
    result = cursor.fetchone()
    if result and result['screenshot']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], result['screenshot'])
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete member from DB
    cursor.execute("DELETE FROM membership WHERE id = %s", (member_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('view_members'))




# ✅ Admin Logout
@app.route('/admin/logout')
def logout_admin():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# ✅ Run Server
if __name__ == '__main__':
    app.run(debug=True)