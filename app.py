from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config.from_object('config.Config')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(200))
    resume = db.Column(db.String(200))
    description = db.Column(db.Text)
    skills = db.Column(db.Text)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 'notes', 'exercise', or 'exam'
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

# Create tables
with app.app_context():
    db.create_all()
    # Create admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')  # Change this password!
        db.session.add(admin)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    notes = Material.query.filter_by(category='notes').all()
    exercises = Material.query.filter_by(category='exercise').all()
    return render_template('index.html', notes=notes, exercises=exercises)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/students')
def students():
    students_list = Student.query.all()
    return render_template('students.html', students=students_list)

@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('students'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        skills = request.form.get('skills')
        
        profile_pic = request.files.get('profile_picture')
        resume_file = request.files.get('resume')
        
        if name:
            student = Student(
                name=name,
                description=description,
                skills=skills
            )
            
            if profile_pic:
                profile_filename = secure_filename(f"profile_{name}_{profile_pic.filename}")
                profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_filename))
                student.profile_picture = profile_filename
                
            if resume_file:
                resume_filename = secure_filename(f"resume_{name}_{resume_file.filename}")
                resume_file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))
                student.resume = resume_filename
            
            db.session.add(student)
            db.session.commit()
            flash('Student profile added successfully!', 'success')
            return redirect(url_for('students'))
        
        flash('Please provide at least the student name', 'error')
    return render_template('add_student.html')

@app.route('/student/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('students'))
        
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        student.name = request.form.get('name', student.name)
        student.description = request.form.get('description', student.description)
        student.skills = request.form.get('skills', student.skills)
        
        profile_pic = request.files.get('profile_picture')
        resume_file = request.files.get('resume')
        
        if profile_pic:
            if student.profile_picture:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], student.profile_picture))
                except:
                    pass
            profile_filename = secure_filename(f"profile_{student.name}_{profile_pic.filename}")
            profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_filename))
            student.profile_picture = profile_filename
            
        if resume_file:
            if student.resume:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], student.resume))
                except:
                    pass
            resume_filename = secure_filename(f"resume_{student.name}_{resume_file.filename}")
            resume_file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))
            student.resume = resume_filename
        
        db.session.commit()
        flash('Student profile updated successfully!', 'success')
        return redirect(url_for('students'))
        
    return render_template('edit_student.html', student=student)

@app.route('/student/delete/<int:id>')
@login_required
def delete_student(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('students'))
        
    student = Student.query.get_or_404(id)
    
    try:
        if student.profile_picture:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], student.profile_picture))
        if student.resume:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], student.resume))
            
        db.session.delete(student)
        db.session.commit()
        flash('Student profile deleted successfully!', 'success')
    except:
        flash('Error deleting student profile', 'error')
        
    return redirect(url_for('students'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        file = request.files.get('file')

        if file and title and category:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            material = Material(
                title=title,
                category=category,
                filename=filename,
                description=description
            )
            db.session.add(material)
            db.session.commit()
            flash('Material uploaded successfully!', 'success')
            return redirect(url_for('home'))
        
        flash('Please fill in all required fields', 'error')
    return render_template('upload.html')

@app.route('/download/<int:id>')
@app.route('/download/<int:id>/<string:type>')
def download(id, type=None):
    if type in ['profile', 'resume']:
        student = Student.query.get_or_404(id)
        filename = student.profile_picture if type == 'profile' else student.resume
    else:
        material = Material.query.get_or_404(id)
        filename = material.filename

    if not filename:
        abort(404)
        
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))

    material = Material.query.get_or_404(id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], material.filename))
        db.session.delete(material)
        db.session.commit()
        flash('Material deleted successfully!', 'success')
    except:
        flash('Error deleting material', 'error')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)