import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
from database import db, User, Prediction, Admin, Log
from predict import predictor
from utils import calculate_emi, compare_loans, generate_pdf_report, send_mock_email, send_mock_sms
from functools import wraps
import json
import csv
import io

routes_bp = Blueprint('routes', __name__)

# Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Access denied. Please login first.', 'warning')
            return redirect(url_for('routes.login'))
        g.user = db.session.get(User, session['user_id'])
        if not g.user:
            session.clear()
            return redirect(url_for('routes.login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Access denied. Admin credentials required.', 'danger')
            return redirect(url_for('routes.admin_login'))
        g.admin = db.session.get(Admin, session['admin_id'])
        if not g.admin:
            session.clear()
            return redirect(url_for('routes.admin_login'))
        return f(*args, **kwargs)
    return decorated

# Setup local context variables for templates
@routes_bp.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    admin_id = session.get('admin_id')
    if user_id:
        g.user = db.session.get(User, user_id)
    else:
        g.user = None
    if admin_id:
        g.admin = db.session.get(Admin, admin_id)
    else:
        g.admin = None

# Helper for file uploads
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# --- PUBLIC PAGES ---

@routes_bp.route('/')
def index():
    return render_template('index.html')

@routes_bp.route('/about')
def about():
    return render_template('about.html')

@routes_bp.route('/services')
def services():
    return render_template('services.html')

@routes_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Log contact query
        log = Log(
            action=f"Contact message submitted by {name} ({email}) - Subject: {subject}",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Thank you for contacting us! Our representative will reach out to you shortly.', 'success')
        return redirect(url_for('routes.contact'))
    return render_template('contact.html')

# --- USER AUTHENTICATION ---

@routes_bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('routes.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('routes.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('routes.register'))
            
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            phone=phone
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Log registration
        log = Log(
            user_id=user.id,
            action="User registered account via Web UI",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('routes.login'))
        
    return render_template('register.html')

@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('routes.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            
            # Log login
            log = Log(
                user_id=user.id,
                action="User logged in via Web UI",
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(log)
            db.session.commit()
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            return redirect(url_for('routes.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@routes_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Simulate password reset email
            send_mock_email(
                email=user.email,
                subject="Smart Lender Password Reset",
                body=f"Hello {user.username}, you requested a password reset. Please use reset code: SL-{user.id}9384"
            )
            flash('A password reset link has been simulated & printed to server logs.', 'info')
        else:
            flash('No account found with that email.', 'danger')
            
    return render_template('forgot_password.html')

@routes_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log = Log(
            user_id=user_id,
            action="User logged out",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
        
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('routes.login'))

# --- USER DASHBOARD & PREDICTION ---

@routes_bp.route('/dashboard')
@login_required
def dashboard():
    predictions = Prediction.query.filter_by(user_id=g.user.id).order_by(Prediction.created_at.desc()).limit(5).all()
    total = Prediction.query.filter_by(user_id=g.user.id).count()
    eligible = Prediction.query.filter_by(user_id=g.user.id, is_eligible=1).count()
    
    # Model comparison details for dashboard if needed
    model_comparison_file = os.path.join(current_app.config['BASE_DIR'], 'models', 'model_comparison.json')
    comparison_data = []
    if os.path.exists(model_comparison_file):
        with open(model_comparison_file, 'r') as f:
            comparison_data = json.load(f)
            
    return render_template(
        'dashboard.html', 
        predictions=predictions, 
        total=total, 
        eligible=eligible,
        comparison_data=comparison_data
    )

@routes_bp.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'POST':
        # Retrieve form data
        form_data = {
            'Gender': request.form.get('Gender'),
            'Married': request.form.get('Married'),
            'Dependents': request.form.get('Dependents'),
            'Education': request.form.get('Education'),
            'Self_Employed': request.form.get('Self_Employed'),
            'ApplicantIncome': float(request.form.get('ApplicantIncome', 0)),
            'CoapplicantIncome': float(request.form.get('CoapplicantIncome', 0)),
            'LoanAmount': float(request.form.get('LoanAmount', 0)),
            'Loan_Amount_Term': float(request.form.get('Loan_Amount_Term', 360)),
            'Credit_History': float(request.form.get('Credit_History', 1.0)),
            'Property_Area': request.form.get('Property_Area')
        }
        
        # Validation checks
        if form_data['ApplicantIncome'] <= 0 or form_data['LoanAmount'] <= 0:
            flash("Income and Loan Amount must be greater than zero.", "danger")
            return redirect(url_for('routes.predict'))
            
        try:
            # Predict
            res = predictor.predict(form_data)
            
            # Save Prediction to Database
            prediction = Prediction(
                user_id=g.user.id,
                gender=form_data['Gender'],
                married=form_data['Married'],
                dependents=form_data['Dependents'],
                education=form_data['Education'],
                self_employed=form_data['Self_Employed'],
                applicant_income=form_data['ApplicantIncome'],
                coapplicant_income=form_data['CoapplicantIncome'],
                loan_amount=form_data['LoanAmount'],
                loan_amount_term=form_data['Loan_Amount_Term'],
                credit_history=form_data['Credit_History'],
                property_area=form_data['Property_Area'],
                is_eligible=res['is_eligible'],
                approval_probability=res['approval_probability'],
                explanation_json=json.dumps(res['explanation'])
            )
            
            db.session.add(prediction)
            
            # Log action
            log = Log(
                user_id=g.user.id,
                action=f"Created Loan Prediction #{prediction.id} (Eligible: {res['is_eligible']})",
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(log)
            db.session.commit()
            
            # Simulated SMS/Email Notification
            status_text = "Approved" if res['is_eligible'] == 1 else "Rejected"
            sms_text = f"Smart Lender: Your loan application scoring is complete. Status: {status_text} (Prob: {res['approval_probability'] * 100:.1f}%)."
            send_mock_sms(g.user.phone or "N/A", sms_text)
            
            flash('Prediction calculated and results analyzed with explainable AI drivers.', 'success')
            return redirect(url_for('routes.prediction_result', id=prediction.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error evaluating loan application: {str(e)}", "danger")
            return redirect(url_for('routes.predict'))
            
    return render_template('predict_form.html')

@routes_bp.route('/prediction/<int:id>')
@login_required
def prediction_result(id):
    prediction = Prediction.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    explanation = prediction.get_explanation()
    return render_template('prediction_result.html', prediction=prediction, explanation=explanation)

@routes_bp.route('/history')
@login_required
def history():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    query = Prediction.query.filter_by(user_id=g.user.id)
    
    if search:
        # Search property area or education
        query = query.filter(
            (Prediction.property_area.like(f'%{search}%')) | 
            (Prediction.education.like(f'%{search}%'))
        )
        
    predictions_pagination = query.order_by(Prediction.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('history.html', pagination=predictions_pagination, search=search)

@routes_bp.route('/prediction/<int:id>/delete', methods=['POST'])
@login_required
def delete_prediction(id):
    prediction = Prediction.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    db.session.delete(prediction)
    
    log = Log(
        user_id=g.user.id,
        action=f"Deleted Loan Prediction #{id}",
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)
    db.session.commit()
    
    flash('Prediction record deleted successfully.', 'success')
    return redirect(url_for('routes.history'))

# --- EXPORTS & REPORTS ---

@routes_bp.route('/prediction/<int:id>/report')
@login_required
def download_report(id):
    prediction = Prediction.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    pdf_data = generate_pdf_report(prediction, g.user.full_name or g.user.username)
    
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'SmartLender_Report_{id}.pdf'
    )

@routes_bp.route('/prediction/<int:id>/email', methods=['POST'])
@login_required
def email_report(id):
    prediction = Prediction.query.filter_by(id=id, user_id=g.user.id).first_or_404()
    status_str = "Eligible" if prediction.is_eligible == 1 else "Ineligible"
    
    body_text = f"""
    Hello {g.user.full_name or g.user.username},
    
    Your AI Loan Eligibility Assessment is attached as a PDF report.
    Result: {status_str}
    Approval Probability Score: {prediction.approval_probability * 100:.2f}%
    
    Thank you for choosing Smart Lender!
    """
    
    send_mock_email(
        email=g.user.email,
        subject=f"Smart Lender Evaluation Report #{id}",
        body=body_text
    )
    
    flash('Evaluation report has been emailed successfully (check console/logs for simulated output).', 'success')
    return redirect(url_for('routes.prediction_result', id=id))

# --- USER PROFILE & SETTINGS ---

@routes_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        g.user.full_name = request.form.get('full_name')
        g.user.phone = request.form.get('phone')
        g.user.address = request.form.get('address')
        
        # Profile picture handling
        file = request.files.get('profile_pic')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Prefix user ID to prevent clashes
                filename = f"user_{g.user.id}_{filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                g.user.profile_pic = filename
            else:
                flash('Invalid image format. Allowed formats: PNG, JPG, JPEG, GIF', 'danger')
                return redirect(url_for('routes.profile'))
                
        db.session.commit()
        
        log = Log(
            user_id=g.user.id,
            action="Updated user profile details",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('routes.profile'))
        
    return render_template('profile.html')

@routes_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            
            if g.user.check_password(old_password):
                g.user.set_password(new_password)
                db.session.commit()
                
                log = Log(
                    user_id=g.user.id,
                    action="Changed account password",
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Password changed successfully.', 'success')
            else:
                flash('Incorrect current password.', 'danger')
                
        return redirect(url_for('routes.settings'))
        
    return render_template('settings.html')

# --- ADMIN PANEL ---

@routes_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if g.admin:
        return redirect(url_for('routes.admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session.clear()
            session['admin_id'] = admin.id
            
            # Log admin login
            log = Log(
                admin_id=admin.id,
                action="Admin logged in via Web UI",
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(log)
            db.session.commit()
            
            flash('Admin dashboard loaded successfully.', 'success')
            return redirect(url_for('routes.admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')
            
    return render_template('admin_login.html')

@routes_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_predictions = Prediction.query.count()
    eligible_count = Prediction.query.filter_by(is_eligible=1).count()
    
    # Model comparison details for Admin
    model_comparison_file = os.path.join(current_app.config['BASE_DIR'], 'models', 'model_comparison.json')
    comparison_data = []
    if os.path.exists(model_comparison_file):
        with open(model_comparison_file, 'r') as f:
            comparison_data = json.load(f)
            
    # Recent logs
    recent_logs = Log.query.order_by(Log.created_at.desc()).limit(10).all()
    
    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_predictions=total_predictions,
        eligible_count=eligible_count,
        comparison_data=comparison_data,
        logs=recent_logs
    )

@routes_bp.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@routes_bp.route('/admin/user/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(id):
    user = db.get_or_404(User, id)
    db.session.delete(user)
    
    log = Log(
        admin_id=g.admin.id,
        action=f"Deleted User account: {user.username} (ID: {id})",
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)
    db.session.commit()
    
    flash('User account and associated records deleted.', 'success')
    return redirect(url_for('routes.admin_users'))

@routes_bp.route('/admin/predictions')
@admin_required
def admin_predictions():
    predictions = Prediction.query.order_by(Prediction.created_at.desc()).all()
    return render_template('admin_predictions.html', predictions=predictions)

@routes_bp.route('/admin/prediction/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_prediction(id):
    prediction = db.get_or_404(Prediction, id)
    db.session.delete(prediction)
    
    log = Log(
        admin_id=g.admin.id,
        action=f"Deleted Loan Prediction #{id}",
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)
    db.session.commit()
    
    flash('Prediction record deleted.', 'success')
    return redirect(url_for('routes.admin_predictions'))

@routes_bp.route('/admin/logs')
@admin_required
def admin_logs():
    logs = Log.query.order_by(Log.created_at.desc()).all()
    return render_template('admin_logs.html', logs=logs)

@routes_bp.route('/admin/predictions/export')
@admin_required
def admin_export_csv():
    predictions = Prediction.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        'Prediction ID', 'User ID', 'Gender', 'Married', 'Dependents', 
        'Education', 'Self Employed', 'Applicant Income', 'Coapplicant Income', 
        'Loan Amount', 'Loan Amount Term', 'Credit History', 'Property Area', 
        'Is Eligible', 'Approval Probability', 'Timestamp'
    ])
    
    for p in predictions:
        writer.writerow([
            p.id, p.user_id, p.gender, p.married, p.dependents,
            p.education, p.self_employed, p.applicant_income, p.coapplicant_income,
            p.loan_amount, p.loan_amount_term, p.credit_history, p.property_area,
            p.is_eligible, p.approval_probability, p.created_at
        ])
        
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='SmartLender_AllPredictions_Export.csv'
    )

# --- BONUS TOOLS ---

@routes_bp.route('/emi-calculator', methods=['POST'])
def emi_calc():
    data = request.get_json() or {}
    principal = data.get('principal', 100000)
    rate = data.get('rate', 9.5)
    term = data.get('term', 240)
    
    res = calculate_emi(principal, rate, term)
    return jsonify(res)

@routes_bp.route('/compare-loans', methods=['POST'])
def compare():
    data = request.get_json() or {}
    principal = data.get('principal', 100000)
    term = data.get('term', 240)
    rates = data.get('rates', [8.0, 9.5, 11.0])
    
    res = compare_loans(principal, term, rates)
    return jsonify(res)

@routes_bp.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json() or {}
    message = data.get('message', '').lower()
    
    response = "I am Smart Lender's AI Assistant. I can help you with questions about loan eligibility criteria, interest rates, or calculating monthly repayments."
    
    if "eligible" in message or "qualification" in message or "criteria" in message:
        response = "To qualify for a loan, our model evaluates multiple parameters: a good credit history (usually 1.0), stable applicant/co-applicant income, a balanced debt-to-income ratio (loan requested should match income), and graduate education status."
    elif "rate" in message or "interest" in message:
        response = "Currently, our standard home loan interest rates range from 7.5% to 11.5% annually, depending on credit history and applicant profile."
    elif "term" in message or "duration" in message:
        response = "We offer flexible loan terms ranging from 12 months up to 30 years (360 months). The most common term selected is 30 years."
    elif "emi" in message or "calculate" in message:
        response = "You can calculate your EMI instantly using the 'EMI Calculator' tool available on our Home page or Dashboard. Just input the principal, term, and rate."
    elif "admin" in message:
        response = "Administrative roles allow viewing user activity, modifying databases, exporting records in CSV format, and auditing system logs."
        
    return jsonify({'response': response})
