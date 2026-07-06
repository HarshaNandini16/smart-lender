import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart_lender_super_secret_key_12938012')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Database configuration
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'smart_lender.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT authentication configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt_secret_key_9837482734_secure_enterprise_key_32bytes')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    
    # Upload configurations
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB limits
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Rate Limiting configuration
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    
    # PDF generation folder
    REPORTS_FOLDER = os.path.join(BASE_DIR, 'static', 'reports')
    
    @staticmethod
    def init_app(app):
        # Create necessary folders if they don't exist
        os.makedirs(os.path.join(Config.BASE_DIR, 'instance'), exist_ok=True)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(Config.BASE_DIR, 'dataset'), exist_ok=True)
        os.makedirs(os.path.join(Config.BASE_DIR, 'models'), exist_ok=True)
