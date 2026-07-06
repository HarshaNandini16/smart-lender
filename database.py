from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import json

def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(100), default='default.png', nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    
    predictions = db.relationship('Prediction', backref='user', lazy=True, cascade="all, delete-orphan")
    logs = db.relationship('Log', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'address': self.address,
            'profile_pic': self.profile_pic,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='admin', nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    logs = db.relationship('Log', backref='admin', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    gender = db.Column(db.String(10), nullable=False)
    married = db.Column(db.String(10), nullable=False)
    dependents = db.Column(db.String(10), nullable=False)
    education = db.Column(db.String(20), nullable=False)
    self_employed = db.Column(db.String(10), nullable=False)
    applicant_income = db.Column(db.Float, nullable=False)
    coapplicant_income = db.Column(db.Float, nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    loan_amount_term = db.Column(db.Float, nullable=False)
    credit_history = db.Column(db.Float, nullable=False)
    property_area = db.Column(db.String(20), nullable=False)
    is_eligible = db.Column(db.Integer, nullable=False) # 1 = Eligible, 0 = Not Eligible
    approval_probability = db.Column(db.Float, nullable=False)
    explanation_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    def get_explanation(self):
        return json.loads(self.explanation_json)
        
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'gender': self.gender,
            'married': self.married,
            'dependents': self.dependents,
            'education': self.education,
            'self_employed': self.self_employed,
            'applicant_income': self.applicant_income,
            'coapplicant_income': self.coapplicant_income,
            'loan_amount': self.loan_amount,
            'loan_amount_term': self.loan_amount_term,
            'credit_history': self.credit_history,
            'property_area': self.property_area,
            'is_eligible': self.is_eligible,
            'approval_probability': self.approval_probability,
            'explanation': self.get_explanation(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Log(db.Model):
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='CASCADE'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'admin_id': self.admin_id,
            'action': self.action,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # Seed default admin if none exists
        if not Admin.query.filter_by(username='admin').first():
            default_admin = Admin(
                username='admin',
                email='admin@smartlender.com',
                role='admin'
            )
            default_admin.set_password('Admin@123456')
            db.session.add(default_admin)
            db.session.commit()
            print("Default admin account created successfully!")
