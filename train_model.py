import os
import numpy as np
import pandas as pd
import joblib
import time

# Scikit-learn models and utilities
from sklearn.model_selection import train_test_split, cross_val_score, learning_curve
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, confusion_matrix, roc_curve, precision_recall_curve
)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, 
    AdaBoostClassifier, ExtraTreesClassifier
)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV

# XGBoost
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

# Visualization
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# Fix seed for reproducibility
np.random.seed(42)

def generate_synthetic_dataset(filepath, num_records=800):
    """Generates a high-quality synthetic loan eligibility dataset."""
    print(f"Generating synthetic dataset with {num_records} records...")
    
    # Pre-allocating arrays
    gender = np.random.choice(['Male', 'Female'], size=num_records, p=[0.78, 0.22])
    married = np.random.choice(['Yes', 'No'], size=num_records, p=[0.65, 0.35])
    dependents = np.random.choice(['0', '1', '2', '3+'], size=num_records, p=[0.57, 0.17, 0.16, 0.10])
    education = np.random.choice(['Graduate', 'Not Graduate'], size=num_records, p=[0.78, 0.22])
    self_employed = np.random.choice(['Yes', 'No'], size=num_records, p=[0.14, 0.86])
    
    # Numeric distributions
    applicant_income = np.random.lognormal(mean=8.5, sigma=0.6, size=num_records).astype(int)
    # Clip applicant income to reasonable bounds
    applicant_income = np.clip(applicant_income, 1500, 81000)
    
    coapplicant_income_choice = np.random.choice([0, 1], size=num_records, p=[0.45, 0.55])
    coapplicant_income = np.zeros(num_records)
    for i in range(num_records):
        if coapplicant_income_choice[i] == 1:
            coapplicant_income[i] = int(np.random.exponential(scale=3000))
    coapplicant_income = np.clip(coapplicant_income, 0, 41000)
    
    # Loan Amount (correlated with income)
    loan_amount = []
    for i in range(num_records):
        total_income = applicant_income[i] + coapplicant_income[i]
        base_amt = total_income * np.random.uniform(0.015, 0.035)
        # Add some noise
        amt = int(base_amt + np.random.normal(0, 15))
        loan_amount.append(max(9, min(amt, 700)))
    loan_amount = np.array(loan_amount)
    
    # Loan Amount Term (mostly 360)
    loan_amount_term = np.random.choice([12, 36, 60, 84, 120, 180, 240, 300, 360, 480], 
                                        size=num_records, 
                                        p=[0.005, 0.005, 0.005, 0.005, 0.01, 0.08, 0.02, 0.01, 0.85, 0.01])
    
    # Credit History (critical predictor)
    credit_history = np.random.choice([1.0, 0.0], size=num_records, p=[0.84, 0.16])
    
    # Property Area
    property_area = np.random.choice(['Urban', 'Semiurban', 'Rural'], size=num_records, p=[0.33, 0.38, 0.29])
    
    # Base Loan Status on logical rules with some random noise
    loan_status = []
    for i in range(num_records):
        score = 0.0
        
        # Credit history is the strongest factor
        if credit_history[i] == 1.0:
            score += 0.65
        else:
            score -= 0.50
            
        # Income vs Debt evaluation
        total_income = applicant_income[i] + coapplicant_income[i]
        debt_ratio = (loan_amount[i] * 1000) / (total_income * (loan_amount_term[i] / 12.0) + 1.0)
        
        if debt_ratio > 0.40:
            score -= 0.20
        elif debt_ratio < 0.20:
            score += 0.10
            
        # Property Area factor (Semiurban is preferred, Rural is penalized slightly)
        if property_area[i] == 'Semiurban':
            score += 0.08
        elif property_area[i] == 'Rural':
            score -= 0.05
            
        # Education status
        if education[i] == 'Graduate':
            score += 0.05
            
        # Add random noise
        score += np.random.normal(0, 0.12)
        
        if score >= 0.25:
            loan_status.append('Y')
        else:
            loan_status.append('N')
            
    df = pd.DataFrame({
        'Gender': gender,
        'Married': married,
        'Dependents': dependents,
        'Education': education,
        'Self_Employed': self_employed,
        'ApplicantIncome': applicant_income,
        'CoapplicantIncome': coapplicant_income,
        'LoanAmount': loan_amount,
        'Loan_Amount_Term': loan_amount_term,
        'Credit_History': credit_history,
        'Property_Area': property_area,
        'Loan_Status': loan_status
    })
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"Dataset successfully created at {filepath} ({len(df)} records).")
    return df

def preprocess_data(df):
    """Clean, impute, encode and scale dataset."""
    df_clean = df.copy()
    
    # Handle duplicates if any
    df_clean = df_clean.drop_duplicates()
    
    # Explicit mapping dictionary for manual consistency
    gender_map = {'Male': 1, 'Female': 0}
    married_map = {'Yes': 1, 'No': 0}
    dependents_map = {'0': 0, '1': 1, '2': 2, '3+': 3}
    education_map = {'Graduate': 1, 'Not Graduate': 0}
    self_employed_map = {'Yes': 1, 'No': 0}
    property_area_map = {'Rural': 0, 'Semiurban': 1, 'Urban': 2}
    status_map = {'Y': 1, 'N': 0}
    
    # Impute missing values (just in case)
    df_clean['Gender'] = df_clean['Gender'].fillna(df_clean['Gender'].mode()[0])
    df_clean['Married'] = df_clean['Married'].fillna(df_clean['Married'].mode()[0])
    df_clean['Dependents'] = df_clean['Dependents'].fillna(df_clean['Dependents'].mode()[0])
    df_clean['Education'] = df_clean['Education'].fillna(df_clean['Education'].mode()[0])
    df_clean['Self_Employed'] = df_clean['Self_Employed'].fillna(df_clean['Self_Employed'].mode()[0])
    
    df_clean['ApplicantIncome'] = df_clean['ApplicantIncome'].fillna(df_clean['ApplicantIncome'].median())
    df_clean['CoapplicantIncome'] = df_clean['CoapplicantIncome'].fillna(df_clean['CoapplicantIncome'].median())
    df_clean['LoanAmount'] = df_clean['LoanAmount'].fillna(df_clean['LoanAmount'].median())
    df_clean['Loan_Amount_Term'] = df_clean['Loan_Amount_Term'].fillna(df_clean['Loan_Amount_Term'].mode()[0])
    df_clean['Credit_History'] = df_clean['Credit_History'].fillna(df_clean['Credit_History'].mode()[0])
    df_clean['Property_Area'] = df_clean['Property_Area'].fillna(df_clean['Property_Area'].mode()[0])
    
    # Apply maps
    df_clean['Gender'] = df_clean['Gender'].map(gender_map)
    df_clean['Married'] = df_clean['Married'].map(married_map)
    df_clean['Dependents'] = df_clean['Dependents'].map(dependents_map)
    df_clean['Education'] = df_clean['Education'].map(education_map)
    df_clean['Self_Employed'] = df_clean['Self_Employed'].map(self_employed_map)
    df_clean['Property_Area'] = df_clean['Property_Area'].map(property_area_map)
    df_clean['Loan_Status'] = df_clean['Loan_Status'].map(status_map)
    
    return df_clean

def train_and_evaluate(csv_path, models_dir, charts_dir):
    """Trains 10 ML models, selects the best, saves models and creates visualization charts."""
    df = pd.read_csv(csv_path)
    df_processed = preprocess_data(df)
    
    # Feature Selection / Target definition
    X = df_processed.drop('Loan_Status', axis=1)
    y = df_processed['Loan_Status']
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Scale numeric columns
    numeric_cols = ['ApplicantIncome', 'CoapplicantIncome', 'LoanAmount', 'Loan_Amount_Term']
    
    scaler = StandardScaler()
    X_train_scaled = X_train.copy()
    X_test_scaled = X_test.copy()
    
    X_train_scaled[numeric_cols] = scaler.fit_transform(X_train[numeric_cols])
    X_test_scaled[numeric_cols] = scaler.transform(X_test[numeric_cols])
    
    # Save preprocessors
    os.makedirs(models_dir, exist_ok=True)
    preprocessors = {
        'scaler': scaler,
        'numeric_cols': numeric_cols,
        'feature_names': list(X.columns)
    }
    joblib.dump(preprocessors, os.path.join(models_dir, 'preprocessors.joblib'))
    
    # Models dictionary
    models = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
        'Decision Tree': DecisionTreeClassifier(random_state=42, max_depth=5),
        'Random Forest': RandomForestClassifier(random_state=42, n_estimators=100, max_depth=7),
        'KNN': KNeighborsClassifier(n_neighbors=5),
        'Naive Bayes': GaussianNB(),
        'SVM': CalibratedClassifierCV(SVC(random_state=42), ensemble=False),
        'Gradient Boosting': GradientBoostingClassifier(random_state=42, n_estimators=100, max_depth=3),
        'AdaBoost': AdaBoostClassifier(random_state=42, n_estimators=100),
        'Extra Trees': ExtraTreesClassifier(random_state=42, n_estimators=100, max_depth=7)
    }
    
    if HAS_XGB:
        models['XGBoost'] = XGBClassifier(random_state=42, n_estimators=100, max_depth=3, eval_metric='logloss')
    else:
        print("XGBoost library not found, skipping from comparison.")
        
    results = []
    trained_models = {}
    
    print("\n--- Training and Evaluating Models ---")
    for name, model in models.items():
        start_time = time.time()
        # Train model
        model.fit(X_train_scaled, y_train)
        train_time = time.time() - start_time
        
        start_time = time.time()
        # Predict model
        y_pred = model.predict(X_test_scaled)
        pred_time = time.time() - start_time
        
        y_pred_prob = model.predict_proba(X_test_scaled)[:, 1]
        
        # Scoring metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_pred_prob)
        
        # Cross validation
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='accuracy')
        cv_mean = cv_scores.mean()
        
        results.append({
            'Model': name,
            'Accuracy': acc,
            'Precision': prec,
            'Recall': rec,
            'F1-Score': f1,
            'ROC-AUC': auc,
            'CV Accuracy': cv_mean,
            'Training Time (s)': train_time,
            'Prediction Time (s)': pred_time
        })
        trained_models[name] = model
        print(f"{name:<22} | Acc: {acc:.4f} | F1: {f1:.4f} | AUC: {auc:.4f} | CV: {cv_mean:.4f}")
        
    results_df = pd.DataFrame(results)
    
    # Save model comparison data as JSON for web interface
    results_df.to_json(os.path.join(models_dir, 'model_comparison.json'), orient='records', indent=4)
    
    # Choose best model (priority: CV Accuracy, F1-Score)
    best_row = results_df.sort_values(by=['CV Accuracy', 'F1-Score'], ascending=False).iloc[0]
    best_model_name = best_row['Model']
    best_model = trained_models[best_model_name]
    
    print(f"\nBest Model selected: {best_model_name} (CV Acc: {best_row['CV Accuracy']:.4f})")
    joblib.dump(best_model, os.path.join(models_dir, 'best_model.joblib'))
    
    # Create visualizations
    os.makedirs(charts_dir, exist_ok=True)
    sns.set_theme(style="darkgrid")
    
    # 1. Target countplot
    plt.figure(figsize=(6, 4))
    sns.countplot(x='Loan_Status', data=df)
    plt.title('Distribution of Loan Status (Target)')
    plt.xlabel('Loan Eligible (Y=Yes, N=No)')
    plt.savefig(os.path.join(charts_dir, 'target_distribution.png'), bbox_inches='tight', dpi=150)
    plt.close()
    
    # 2. Correlation matrix heatmap
    plt.figure(figsize=(10, 8))
    corr = df_processed.corr()
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)
    plt.title('Correlation Matrix of Loan Features')
    plt.savefig(os.path.join(charts_dir, 'correlation_matrix.png'), bbox_inches='tight', dpi=150)
    plt.close()
    
    # 3. Model Accuracy Comparison Bar Chart
    plt.figure(figsize=(10, 5))
    sorted_res = results_df.sort_values(by='CV Accuracy', ascending=True)
    bars = plt.barh(sorted_res['Model'], sorted_res['CV Accuracy'], color='#4F46E5')
    plt.title('Model Comparison (5-Fold Cross Validation Accuracy)')
    plt.xlabel('Accuracy')
    plt.xlim(0, 1.0)
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.01, bar.get_y() + bar.get_height()/2, f'{width:.4f}', 
                 va='center', ha='left', fontsize=9, fontweight='bold')
    plt.savefig(os.path.join(charts_dir, 'model_comparison.png'), bbox_inches='tight', dpi=150)
    plt.close()
    
    # 4. Feature Importance for the best model
    plt.figure(figsize=(10, 6))
    if hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
        indices = np.argsort(importances)[::-1]
        feat_imp = pd.DataFrame({
            'Feature': [X.columns[i] for i in indices],
            'Importance': [importances[i] for i in indices]
        })
        sns.barplot(x='Importance', y='Feature', data=feat_imp, hue='Feature', palette='viridis', legend=False)
        plt.title(f'Feature Importances ({best_model_name})')
    elif hasattr(best_model, 'coef_'):
        importances = np.abs(best_model.coef_[0])
        indices = np.argsort(importances)[::-1]
        feat_imp = pd.DataFrame({
            'Feature': [X.columns[i] for i in indices],
            'Importance': [importances[i] for i in indices]
        })
        sns.barplot(x='Importance', y='Feature', data=feat_imp, hue='Feature', palette='viridis', legend=False)
        plt.title(f'Feature Coefficients ({best_model_name})')
    else:
        # For model without importances/coefficients like KNN, default to Random Forest importances
        temp_rf = RandomForestClassifier(random_state=42)
        temp_rf.fit(X_train_scaled, y_train)
        importances = temp_rf.feature_importances_
        indices = np.argsort(importances)[::-1]
        feat_imp = pd.DataFrame({
            'Feature': [X.columns[i] for i in indices],
            'Importance': [importances[i] for i in indices]
        })
        sns.barplot(x='Importance', y='Feature', data=feat_imp, hue='Feature', palette='viridis', legend=False)
        plt.title('Feature Importances (Approximated via Random Forest)')
    plt.savefig(os.path.join(charts_dir, 'feature_importance.png'), bbox_inches='tight', dpi=150)
    plt.close()
    
    # 5. Confusion Matrix for Best Model
    plt.figure(figsize=(6, 5))
    y_pred_best = best_model.predict(X_test_scaled)
    cm = confusion_matrix(y_test, y_pred_best)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, 
                xticklabels=['Not Eligible', 'Eligible'], yticklabels=['Not Eligible', 'Eligible'])
    plt.title(f'Confusion Matrix ({best_model_name})')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.savefig(os.path.join(charts_dir, 'confusion_matrix.png'), bbox_inches='tight', dpi=150)
    plt.close()
    
    # 6. ROC and Precision-Recall Curves
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # ROC
    y_best_prob = best_model.predict_proba(X_test_scaled)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, y_best_prob)
    ax1.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {best_row["ROC-AUC"]:.4f})')
    ax1.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    ax1.set_xlim([0.0, 1.0])
    ax1.set_ylim([0.0, 1.05])
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('Receiver Operating Characteristic (ROC)')
    ax1.legend(loc="lower right")
    
    # Precision-Recall
    precision, recall, _ = precision_recall_curve(y_test, y_best_prob)
    ax2.plot(recall, precision, color='blue', lw=2, label='Precision-Recall curve')
    ax2.set_xlabel('Recall')
    ax2.set_ylabel('Precision')
    ax2.set_title('Precision-Recall Curve')
    ax2.set_xlim([0.0, 1.0])
    ax2.set_ylim([0.0, 1.05])
    ax2.legend(loc="lower left")
    
    plt.savefig(os.path.join(charts_dir, 'evaluation_curves.png'), bbox_inches='tight', dpi=150)
    plt.close()
    
    # 7. Learning Curve
    plt.figure(figsize=(8, 5))
    train_sizes, train_scores, test_scores = learning_curve(
        best_model, X_train_scaled, y_train, cv=5, n_jobs=-1,
        train_sizes=np.linspace(0.1, 1.0, 5), scoring='accuracy'
    )
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)
    
    plt.plot(train_sizes, train_mean, 'o-', color="r", label="Training score")
    plt.plot(train_sizes, test_mean, 'o-', color="g", label="Cross-validation score")
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")
    plt.title(f'Learning Curve ({best_model_name})')
    plt.xlabel('Training Examples')
    plt.ylabel('Accuracy Score')
    plt.legend(loc="best")
    plt.savefig(os.path.join(charts_dir, 'learning_curve.png'), bbox_inches='tight', dpi=150)
    plt.close()
    
    print("\nAll visualization charts successfully saved under static/images/charts/")
    print("Machine Learning training pipeline complete!")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'dataset', 'loan_data.csv')
    models_dir = os.path.join(base_dir, 'models')
    charts_dir = os.path.join(base_dir, 'static', 'images', 'charts')
    
    # Generate dataset if not present
    if not os.path.exists(csv_path):
        generate_synthetic_dataset(csv_path, num_records=1000)
        
    train_and_evaluate(csv_path, models_dir, charts_dir)
