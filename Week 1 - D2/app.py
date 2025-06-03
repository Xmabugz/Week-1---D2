from flask import Flask, render_template, redirect, url_for, request, flash, session, get_flashed_messages
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.utils import secure_filename
from datetime import date
from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / 'static' / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///profile.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = str(UPLOAD_DIR)

bootstrap = Bootstrap5(app)

class Base(DeclarativeBase):
    pass    

db = SQLAlchemy(model_class=Base)
db.init_app(app)

class User(db.Model):
    __tablename__ = 'info'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    bday = db.Column(db.Date, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)

    def age(self) -> int:
        today = date.today()
        return today.year - self.bday.year - (
            (today.month, today.day) < (self.bday.month, self.bday.day)
        )

    def image_url(self) -> str:
        if self.image_filename:
            return url_for('static', filename=f"uploads/{self.image_filename}")
        return url_for('static', filename='uploads/default.png')  # Fallback image

def is_allowed_file(filename: str) -> bool:
    return '.' in filename and (
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        bday_str = request.form.get('birthdate', '').strip()
        address = request.form.get('address', '').strip()

        if not (username and password and name and bday_str and address):
            flash('All fields are required.', 'warning')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose a new one.', 'danger')
            return render_template('register.html')

        try:
            bday = date.fromisoformat(bday_str)
        except ValueError:
            flash('Invalid date format for birthday.', 'danger')
            return render_template('register.html')

        uploaded_file = request.files.get('image')
        saved_filename = None
        if uploaded_file and uploaded_file.filename:
            if is_allowed_file(uploaded_file.filename):
                safe_name = secure_filename(uploaded_file.filename)
                saved_path = UPLOAD_DIR / safe_name
                uploaded_file.save(saved_path)
                saved_filename = f'uploads/{safe_name}'
            else:
                flash('Unsupported file type for image.', 'danger')
                return render_template('register.html')

        new_user = User(
            username=username,
            password=password,
            name=name,
            bday=bday,
            address=address,
            image_filename=saved_filename
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            flash('Logged in successfully.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/profile')
def profile():
    current_user = get_current_user()
    if not current_user:
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('login'))

    user_data = {
        'id': current_user.id,
        'name': current_user.name,
        'age': current_user.age,
        'address': current_user.address,
        'image_url': current_user.image_filename
    }
    return render_template('profile.html', user=user_data)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)