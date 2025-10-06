from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
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

class Gallery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

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
    return redirect(url_for('dashboard'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/dashboard')
@app.route('/dashboard/<int:page>')
def dashboard(page=1):
    per_page = 10
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', 'all')
    sort_order = request.args.get('sort', 'newest')

    # Base queries
    notes_query = Material.query.filter_by(category='notes')
    exercises_query = Material.query.filter_by(category='exercise')

    # Apply search filter if provided
    if search_query:
        notes_query = notes_query.filter(Material.title.ilike(f'%{search_query}%'))
        exercises_query = exercises_query.filter(Material.title.ilike(f'%{search_query}%'))

    # Apply sorting
    if sort_order == 'az':
        notes_query = notes_query.order_by(Material.title.asc())
        exercises_query = exercises_query.order_by(Material.title.asc())
    elif sort_order == 'za':
        notes_query = notes_query.order_by(Material.title.desc())
        exercises_query = exercises_query.order_by(Material.title.desc())
    else:  # Default to ID based sorting
        notes_query = notes_query.order_by(Material.id.desc())
        exercises_query = exercises_query.order_by(Material.id.desc())

    # Get paginated results
    notes = notes_query.paginate(page=page, per_page=per_page, error_out=False)
    exercises = exercises_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('dashboard.html', 
                         notes=notes, 
                         exercises=exercises,
                         search_query=search_query,
                         category_filter=category_filter,
                         sort_order=sort_order)

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
@app.route('/students/<int:page>')
def students(page=1):
    per_page = 9  # Show 9 students per page (3x3 grid)
    students_pagination = Student.query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('students.html', students=students_pagination)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('students'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        skills = request.form.get('skills', '').strip()
        
        profile_pic = request.files.get('profile_picture')
        resume_file = request.files.get('resume')
        
        if not name:
            flash('Please provide the student name', 'error')
            return render_template('add_student.html')

        try:
            student = Student(
                name=name,
                description=description,
                skills=skills
            )
            
            # Handle profile picture
            if profile_pic and profile_pic.filename:
                if not allowed_file(profile_pic.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                    flash('Invalid image format. Please use PNG, JPG, JPEG, or GIF.', 'error')
                    return render_template('add_student.html')
                
                try:
                    profile_filename = secure_filename(f"profile_{name}_{profile_pic.filename}")
                    profile_path = os.path.join(app.config['UPLOAD_FOLDER'], profile_filename)
                    profile_pic.save(profile_path)
                    
                    # Verify file was saved
                    if not os.path.exists(profile_path):
                        raise Exception("Failed to save profile picture")
                    
                    student.profile_picture = profile_filename
                except Exception as e:
                    flash(f'Error uploading profile picture: {str(e)}', 'error')
                    return render_template('add_student.html')
            
            # Handle resume
            if resume_file and resume_file.filename:
                if not allowed_file(resume_file.filename, {'pdf', 'doc', 'docx'}):
                    flash('Invalid resume format. Please use PDF, DOC, or DOCX.', 'error')
                    return render_template('add_student.html')
                
                try:
                    resume_filename = secure_filename(f"resume_{name}_{resume_file.filename}")
                    resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
                    resume_file.save(resume_path)
                    
                    # Verify file was saved
                    if not os.path.exists(resume_path):
                        raise Exception("Failed to save resume")
                    
                    student.resume = resume_filename
                except Exception as e:
                    flash(f'Error uploading resume: {str(e)}', 'error')
                    return render_template('add_student.html')
            
            # Save student to database
            db.session.add(student)
            db.session.commit()
            flash('Student profile added successfully!', 'success')
            return redirect(url_for('students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'error')
            return render_template('add_student.html')
    
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
    try:
        if type == 'gallery':
            gallery_item = Gallery.query.get_or_404(id)
            filename = gallery_item.filename
        elif type in ['profile', 'resume']:
            student = Student.query.get_or_404(id)
            filename = student.profile_picture if type == 'profile' else student.resume
        else:
            if not current_user.is_authenticated:
                flash('Please log in to download materials.', 'error')
                return redirect(url_for('login'))
            material = Material.query.get_or_404(id)
            filename = material.filename

        if not filename:
            abort(404)
            
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            abort(404)
            
        # Set content type for images
        if type == 'profile' or type == 'gallery':
            ext = filename.rsplit('.', 1)[1].lower()
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif'
            }
            mimetype = mime_types.get(ext, 'application/octet-stream')
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype=mimetype)
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        abort(404)

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

def get_predefined_categories():
    return [
        ('General', 'General images'),
        ('Education', 'Educational content'),
        ('Tour', 'Tours and visits'),
        ('Quiz', 'Quiz related'),
        ('Information', 'Informational content'),
        ('Facts', 'Interesting facts')
    ]

@app.route('/gallery')
def gallery():
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Show 12 images per page in a 3x4 grid
    category = request.args.get('category', '')
    
    # Use predefined categories instead of querying from database
    categories = get_predefined_categories()
    
    query = Gallery.query
    if category:
        query = query.filter_by(category=category)
    
    images = query.order_by(Gallery.upload_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('gallery.html', images=images, categories=categories, selected_category=category)

@app.route('/gallery/upload', methods=['GET', 'POST'])
@login_required
def upload_gallery():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('gallery'))

    # Get predefined categories for the form
    categories = get_predefined_categories()

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        image = request.files.get('image')

        if image and title and category:
            try:
                # Ensure upload directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Create a secure filename with gallery prefix
                filename = secure_filename(f"gallery_{title}_{image.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save the image
                image.save(file_path)
                
                # Verify the file was saved
                if not os.path.exists(file_path):
                    raise Exception("File failed to save")
                
                gallery_item = Gallery(
                    title=title,
                    category=category,
                    filename=filename,
                    description=description
                )
                db.session.add(gallery_item)
                db.session.commit()
                
                flash('Image uploaded successfully!', 'success')
                return redirect(url_for('gallery'))
            except Exception as e:
                print(f"Error uploading image: {str(e)}")
                flash('Error uploading image. Please try again.', 'error')
                return redirect(url_for('upload_gallery'))
        
        flash('Please fill in all required fields', 'error')
    return render_template('upload_gallery.html', categories=categories)

@app.route('/gallery/delete/<int:id>')
@login_required
def delete_gallery(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('gallery'))

    image = Gallery.query.get_or_404(id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
        db.session.delete(image)
        db.session.commit()
        flash('Image deleted successfully!', 'success')
    except:
        flash('Error deleting image', 'error')
    return redirect(url_for('gallery'))

@app.route('/api/search-materials')
def search_materials():
    search_query = request.args.get('search', '').strip()
    category = request.args.get('category', 'all')
    sort_order = request.args.get('sort', 'newest')

    # Base query
    query = Material.query

    # Apply search filter
    if search_query:
        query = query.filter(Material.title.ilike(f'%{search_query}%'))

    # Apply category filter
    if category != 'all':
        query = query.filter_by(category=category)

    # Apply sorting
    if sort_order == 'az':
        query = query.order_by(Material.title.asc())
    elif sort_order == 'za':
        query = query.order_by(Material.title.desc())
    else:  # newest/oldest based on ID
        query = query.order_by(Material.id.desc() if sort_order == 'newest' else Material.id.asc())

    # Get results
    materials = query.all()
    
    # Format results
    results = [{
        'id': m.id,
        'title': m.title,
        'category': m.category,
        'description': m.description,
        'filename': m.filename,
    } for m in materials]

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)