# Smart Lender: AI-Powered Loan Eligibility Prediction System

[![Python Version](https://img.shields.bwt/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Flask Version](https://img.shields.bwt/badge/flask-3.1.x-indigo)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.bwt/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Smart Lender is a production-ready, AI-powered Loan Eligibility Prediction System designed to automate bank underwriting workflows. Built using a robust Flask backend and an optimized Scikit-learn/XGBoost classification pipeline, the application evaluates applicant eligibility and returns local decision impact weights using explainable AI principles.

---

## Key Features

- **Automated ML Classification**: Trains and evaluates 10 classifiers (Random Forest, Gradient Boosting, SVM, XGBoost, etc.) and auto-loads the best performer.
- **Explainable AI (XAI)**: Identifies local positive and negative drivers using feature contribution paths.
- **Professional Banking UI**: Premium glassmorphism design with responsive Bootstrap 5 elements, AOS scroll animations, and dynamic Chart.js dashboards.
- **Auditing Logs & Administration**: Interactive user managers, logs trackers, and CSV logs download tools.
- **Developer REST API**: Secure endpoints secured with JWT tokens and documented via interactive Swagger UI page under `/api/docs`.
- **Extra Tools**: Real-time Loan EMI Calculator, Loan Offers Comparison matrix, and simulated interactive banking Chatbot.

---

## Project Structure

```text
SmartLender/
├── app.py                  # App initialization factory
├── config.py               # Security & directory configs
├── database.py             # SQLAlchemy schema tables (User, Prediction, Log, Admin)
├── predict.py              # ML loader & Explainability engine
├── train_model.py          # Synthetic dataset generator & model training pipeline
├── utils.py                # Repayment formulas, mock email/SMS, ReportLab PDF exporter
├── api.py                  # JWT authentication blueprints & Swagger spec
├── routes.py               # UI blueprints (landing, dashboard, admin panel)
├── requirements.txt        # Package dependencies list
├── Dockerfile              # Docker container recipe
├── docker-compose.yml      # Orchestration yaml
├── Procfile                # Gunicorn runner target for IBM Cloud
├── runtime.txt             # Deployment python engine specification
├── templates/              # HTML layout and user dashboard forms
├── static/                 # Static CSS stylesheets, images, and client JS scripts
├── tests/                  # Automated integration tests suite
└── docs/                   # Full user manual and setup guidelines
```

---

## Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/username/SmartLender.git
   cd SmartLender
   ```

2. **Setup Virtual Environment & Install Packages**:
   ```bash
   python -m venv venv
   venv\Scripts\activate       # On Linux: source venv/bin/activate
   python -m pip install -r requirements.txt
   ```

3. **Train Models and Seed Database**:
   ```bash
   python train_model.py
   python -c "from app import app; from database import db; db.create_all(app=app)"
   ```

4. **Launch Application**:
   ```bash
   python app.py
   ```
   Navigate to `http://127.0.0.1:5000` to interact with the platform.
   - Default Admin credentials: `admin` / `Admin@123456`

---

## REST API Integration

The API endpoints reside under the `/api` prefix:

- **Sign Up**: `POST /api/auth/register`
- **Log In**: `POST /api/auth/login` -> Returns JWT token.
- **Predict**: `POST /api/predict` -> Header: `Authorization: Bearer <JWT_TOKEN>`

### Predict Endpoint Example (cURL):
```bash
curl -X POST http://127.0.0.1:5000/api/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "Gender": "Male",
    "Married": "Yes",
    "Dependents": "0",
    "Education": "Graduate",
    "Self_Employed": "No",
    "ApplicantIncome": 6000,
    "CoapplicantIncome": 2000,
    "LoanAmount": 180,
    "Loan_Amount_Term": 360,
    "Credit_History": 1.0,
    "Property_Area": "Semiurban"
  }'
```

---

## Docker Execution

Build and run containerized locally:
```bash
docker-compose up --build
```
The application container binds to `http://localhost:5000`.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
