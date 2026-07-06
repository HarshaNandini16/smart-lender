import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, render_template, g
from database import db, User, Prediction, Log
from predict import predictor
import json

api_bp = Blueprint('api', __name__, url_prefix='/api')

def token_required(f):
    """Decorator to require JWT authentication for API endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format. Use Bearer <token>'}), 401
                
        if not token:
            return jsonify({'message': 'Authentication token is missing!'}), 401
            
        try:
            # Decode token
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
            g.current_user = current_user
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(*args, **kwargs)
        
    return decorated

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user via API."""
    data = request.get_json() or {}
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    phone = data.get('phone')
    address = data.get('address')
    
    if not username or not email or not password:
        return jsonify({'message': 'Missing required fields (username, email, password)'}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400
        
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        phone=phone,
        address=address
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    # Log registration
    log = Log(
        user_id=user.id,
        action="User registered via REST API",
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': 'User registered successfully!',
        'user': user.to_dict()
    }), 201

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
        
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid credentials'}), 401
        
    # Generate JWT token
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.now(timezone.utc) + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")
    
    # Log login
    log = Log(
        user_id=user.id,
        action="User logged in via REST API",
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': 'Login successful!',
        'token': token,
        'user': user.to_dict(),
        'expires_in_seconds': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
    })

@api_bp.route('/predict', methods=['POST'])
@token_required
def predict():
    """Submit a loan prediction request via API."""
    data = request.get_json() or {}
    
    # Required parameters checking
    required_fields = [
        'Gender', 'Married', 'Dependents', 'Education', 'Self_Employed',
        'ApplicantIncome', 'CoapplicantIncome', 'LoanAmount', 
        'Loan_Amount_Term', 'Credit_History', 'Property_Area'
    ]
    
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({'message': f'Missing inputs: {", ".join(missing)}'}), 400
        
    try:
        # Run prediction engine
        res = predictor.predict(data)
        
        # Save to DB
        prediction = Prediction(
            user_id=g.current_user.id,
            gender=data['Gender'],
            married=data['Married'],
            dependents=str(data['Dependents']),
            education=data['Education'],
            self_employed=data['Self_Employed'],
            applicant_income=float(data['ApplicantIncome']),
            coapplicant_income=float(data['CoapplicantIncome']),
            loan_amount=float(data['LoanAmount']),
            loan_amount_term=float(data['Loan_Amount_Term']),
            credit_history=float(data['Credit_History']),
            property_area=data['Property_Area'],
            is_eligible=res['is_eligible'],
            approval_probability=res['approval_probability'],
            explanation_json=json.dumps(res['explanation'])
        )
        
        db.session.add(prediction)
        
        # Log prediction action
        log = Log(
            user_id=g.current_user.id,
            action=f"Created Loan Prediction #{prediction.id} via API (Eligible: {res['is_eligible']})",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'Prediction calculated successfully!',
            'prediction_id': prediction.id,
            'is_eligible': res['is_eligible'],
            'approval_probability': res['approval_probability'],
            'rejection_probability': res['rejection_probability'],
            'explanation': res['explanation']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error processing prediction: {str(e)}'}), 500

@api_bp.route('/predictions', methods=['GET'])
@token_required
def get_predictions():
    """Retrieve current user's prediction history."""
    predictions = Prediction.query.filter_by(user_id=g.current_user.id).order_by(Prediction.created_at.desc()).all()
    return jsonify([p.to_dict() for p in predictions])

@api_bp.route('/analytics', methods=['GET'])
@token_required
def get_analytics():
    """Retrieve summary analytics for current user's historical runs."""
    predictions = Prediction.query.filter_by(user_id=g.current_user.id).all()
    
    total = len(predictions)
    if total == 0:
        return jsonify({
            'total_predictions': 0,
            'eligible_count': 0,
            'ineligible_count': 0,
            'success_rate': 0.0,
            'average_loan_amount': 0.0,
            'average_income': 0.0
        })
        
    eligible = sum(1 for p in predictions if p.is_eligible == 1)
    ineligible = total - eligible
    avg_loan = sum(p.loan_amount for p in predictions) / total
    avg_income = sum(p.applicant_income + p.coapplicant_income for p in predictions) / total
    
    return jsonify({
        'total_predictions': total,
        'eligible_count': eligible,
        'ineligible_count': ineligible,
        'success_rate': round((eligible / total) * 100, 2),
        'average_loan_amount_k': round(avg_loan, 2),
        'average_income': round(avg_income, 2)
    })

# Swagger JSON Spec
@api_bp.route('/docs/swagger.json', methods=['GET'])
def swagger_json():
    """Serve the OpenAPI / Swagger specification JSON."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Smart Lender REST API",
            "version": "1.0.0",
            "description": "API documentation for the AI-Powered Loan Eligibility Prediction System."
        },
        "servers": [
            {"url": "/api", "description": "Current Environment API"}
        ],
        "paths": {
            "/auth/register": {
                "post": {
                    "summary": "Register a new user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                        "full_name": {"type": "string"},
                                        "phone": {"type": "string"},
                                        "address": {"type": "string"}
                                    },
                                    "required": ["username", "email", "password"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "User successfully registered"},
                        "400": {"description": "Invalid input or user already exists"}
                    }
                }
            },
            "/auth/login": {
                "post": {
                    "summary": "Log in and obtain JWT access token",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string"}
                                    },
                                    "required": ["username", "password"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Authentication successful, returns JWT"},
                        "401": {"description": "Invalid credentials"}
                    }
                }
            },
            "/predict": {
                "post": {
                    "summary": "Submit client details for AI loan evaluation",
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "Gender": {"type": "string", "enum": ["Male", "Female"]},
                                        "Married": {"type": "string", "enum": ["Yes", "No"]},
                                        "Dependents": {"type": "string", "enum": ["0", "1", "2", "3+"]},
                                        "Education": {"type": "string", "enum": ["Graduate", "Not Graduate"]},
                                        "Self_Employed": {"type": "string", "enum": ["Yes", "No"]},
                                        "ApplicantIncome": {"type": "number"},
                                        "CoapplicantIncome": {"type": "number"},
                                        "LoanAmount": {"type": "number", "description": "Loan amount in thousands"},
                                        "Loan_Amount_Term": {"type": "number", "description": "Term in months"},
                                        "Credit_History": {"type": "number", "enum": [0.0, 1.0]},
                                        "Property_Area": {"type": "string", "enum": ["Urban", "Semiurban", "Rural"]}
                                    },
                                    "required": ["Gender", "Married", "Dependents", "Education", "Self_Employed", "ApplicantIncome", "CoapplicantIncome", "LoanAmount", "Loan_Amount_Term", "Credit_History", "Property_Area"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Evaluated successfully"},
                        "401": {"description": "Unauthorized"},
                        "400": {"description": "Invalid parameters"}
                    }
                }
            },
            "/predictions": {
                "get": {
                    "summary": "Fetch historical predictions list",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "List of user predictions"},
                        "401": {"description": "Unauthorized"}
                    }
                }
            },
            "/analytics": {
                "get": {
                    "summary": "Fetch dashboard statistics",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "Summary analysis data"},
                        "401": {"description": "Unauthorized"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }
    return jsonify(spec)

@api_bp.route('/docs', methods=['GET'])
def swagger_docs():
    """Renders the HTML UI page for Swagger documentation."""
    # Simple HTML linking to CDN-based Swagger UI
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Smart Lender API Documentation - Swagger UI</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css" />
        <style>
            html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
            *, *:before, *:after { box-sizing: inherit; }
            body { margin:0; background: #fafafa; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js" charset="UTF-8"></script>
        <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-standalone-preset.js" charset="UTF-8"></script>
        <script>
            window.onload = () => {
                window.ui = SwaggerUIBundle({
                    url: '/api/docs/swagger.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true
                });
            };
        </script>
    </body>
    </html>
    """
    return html_content
