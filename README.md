# Ananas AI Educational Platform

A Flask-based educational platform for managing course materials and student profiles.

## Features

- Course material management (Notes and Exercises)
- Student profile management
- Secure file uploads and downloads
- Admin panel for content management
- Responsive design

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file with your configuration:
```
SECRET_KEY=your-secure-secret-key
DATABASE_URL=sqlite:///education.db
```

5. Initialize the database:
```bash
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

## Deployment

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- A web server (e.g., Nginx)

### Production Setup

1. Set environment variables:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secure-secret-key
```

2. Configure your web server (e.g., Nginx) to proxy requests to Gunicorn.

3. Start the application with Gunicorn:
```bash
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

### Security Notes

1. Always change the default admin credentials:
   - Username: admin
   - Default password: admin123

2. Set a secure SECRET_KEY in production
3. Configure your web server with HTTPS
4. Regular security updates for dependencies
5. Backup your database regularly

## Maintenance

- Regular backups of the uploads folder and database
- Monitor disk space for uploads
- Update dependencies regularly for security patches
- Review and remove unused files periodically