# Developer Guide: Smart Lender Architecture

This guide explains the developer workflow, software design patterns, and codebase integration paths for Smart Lender.

## Codebase Architecture

The application is structured into modular layers containing data science pipelines, database structures, web views, and secure REST APIs:

1. **Machine Learning Layer (`train_model.py`, `predict.py`)**:
   - `train_model.py` generates synthetic training data, runs a multi-model grid search comparing 10 models, selects the best, and serializes the model and `StandardScaler` preprocessors.
   - `predict.py` loads the joblib files, scales the incoming inputs, maps the categorical values, runs classification, and calculates the contribution scores.

2. **Database ORM Layer (`database.py`)**:
   - Configures the SQLite database session.
   - Declares SQLAlchemy classes representing Users, Predictions, Logs, and Admins.
   - Implements triggers to hash passwords and deserialize explanation text files.

3. **Routing Layer (`routes.py`, `api.py`)**:
   - `routes.py` manages session-based cookie cookies state for front-end web templates.
   - `api.py` manages token-based authorization using JWT structures for API integrations.

---

## Modifying Features

### How to add a new ML model to the training pipeline:
1. Open `train_model.py`.
2. Import the classifier from scikit-learn.
3. Append the model class instance to the `models` dictionary:
   ```python
   models['New Classifier'] = NewClassifier(random_state=42)
   ```
4. Re-run `python train_model.py` to compare and save the best model.

### How to modify the Database schema:
1. Open `database.py`.
2. Add columns to the desired table class (e.g. `User`).
3. Re-run migrations or delete `instance/smart_lender.db` and start the server so the SQLite database is re-initialized with the new schema columns.
