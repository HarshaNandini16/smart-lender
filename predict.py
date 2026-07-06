import os
import joblib
import numpy as np
import pandas as pd
import json

class LoanPredictor:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(self.base_dir, 'models', 'best_model.joblib')
        self.prep_path = os.path.join(self.base_dir, 'models', 'preprocessors.joblib')
        
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.numeric_cols = None
        
        # Mappings
        self.gender_map = {'Male': 1, 'Female': 0}
        self.married_map = {'Yes': 1, 'No': 0}
        self.dependents_map = {'0': 0, '1': 1, '2': 2, '3+': 3}
        self.education_map = {'Graduate': 1, 'Not Graduate': 0}
        self.self_employed_map = {'Yes': 1, 'No': 0}
        self.property_area_map = {'Rural': 0, 'Semiurban': 1, 'Urban': 2}
        
        self.load_artifacts()
        
    def load_artifacts(self):
        """Loads serialized model and scaler from joblib files."""
        if os.path.exists(self.model_path) and os.path.exists(self.prep_path):
            try:
                self.model = joblib.load(self.model_path)
                preprocessors = joblib.load(self.prep_path)
                self.scaler = preprocessors['scaler']
                self.feature_names = preprocessors['feature_names']
                self.numeric_cols = preprocessors['numeric_cols']
                print("Model and preprocessors successfully loaded.")
            except Exception as e:
                print(f"Error loading model artifacts: {e}")
        else:
            print("Model artifacts not found. Please train models first using train_model.py.")

    def preprocess_input(self, data):
        """Converts raw input dictionary into processed feature array."""
        if not self.scaler:
            self.load_artifacts()
            if not self.scaler:
                raise ValueError("Model has not been trained. Preprocessors are missing.")
                
        # Handle mappings with defaults for safety
        gender_val = self.gender_map.get(data.get('Gender', 'Male'), 1)
        married_val = self.married_map.get(data.get('Married', 'No'), 0)
        dependents_val = self.dependents_map.get(str(data.get('Dependents', '0')), 0)
        education_val = self.education_map.get(data.get('Education', 'Graduate'), 1)
        self_employed_val = self.self_employed_map.get(data.get('Self_Employed', 'No'), 0)
        property_area_val = self.property_area_map.get(data.get('Property_Area', 'Semiurban'), 1)
        
        # Numeric values
        applicant_income = float(data.get('ApplicantIncome', 5000))
        coapplicant_income = float(data.get('CoapplicantIncome', 0))
        loan_amount = float(data.get('LoanAmount', 150))
        loan_amount_term = float(data.get('Loan_Amount_Term', 360))
        credit_history = float(data.get('Credit_History', 1.0))
        
        # Create dictionary in exact sequence
        features_dict = {
            'Gender': gender_val,
            'Married': married_val,
            'Dependents': dependents_val,
            'Education': education_val,
            'Self_Employed': self_employed_val,
            'ApplicantIncome': applicant_income,
            'CoapplicantIncome': coapplicant_income,
            'LoanAmount': loan_amount,
            'Loan_Amount_Term': loan_amount_term,
            'Credit_History': credit_history,
            'Property_Area': property_area_val
        }
        
        # Construct DataFrame
        df_row = pd.DataFrame([features_dict], columns=self.feature_names)
        
        # Scale numeric features
        df_scaled = df_row.copy()
        df_scaled[self.numeric_cols] = self.scaler.transform(df_row[self.numeric_cols])
        
        return df_row.iloc[0], df_scaled.iloc[0]

    def predict(self, raw_data):
        """Runs predictions, calculates probabilities, and computes explainability factors."""
        # Preprocess features
        raw_features, scaled_features = self.preprocess_input(raw_data)
        
        # Run prediction
        features_df = pd.DataFrame([scaled_features], columns=self.feature_names)
        is_eligible = int(self.model.predict(features_df)[0])
        probabilities = self.model.predict_proba(features_df)[0]
        
        approval_prob = float(probabilities[1])
        rejection_prob = float(probabilities[0])
        
        # Compute AI Explainability (SHAP-like contribution weights)
        explanation = self.generate_explainability(raw_features, scaled_features, is_eligible, approval_prob)
        
        return {
            'is_eligible': is_eligible,
            'approval_probability': approval_prob,
            'rejection_probability': rejection_prob,
            'explanation': explanation
        }

    def generate_explainability(self, raw_features, scaled_features, is_eligible, approval_prob):
        """Generates local explainability by computing feature contributions and feedback."""
        # Get global feature importances
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_[0])
            # Normalize importances
            importances = importances / np.sum(importances)
        else:
            # Default fallback importances (Credit History is highest, then income and amount)
            importances = np.array([0.02, 0.03, 0.03, 0.04, 0.02, 0.15, 0.08, 0.12, 0.05, 0.40, 0.06])
            importances = importances / np.sum(importances)
            
        feature_importance_map = dict(zip(self.feature_names, importances))
        
        contributions = {}
        
        # Calculate individual feature contributions based on values
        # Credit history (strongest factor)
        credit_history_val = raw_features['Credit_History']
        if credit_history_val == 1.0:
            contributions['Credit_History'] = 0.45 * feature_importance_map['Credit_History']
        else:
            contributions['Credit_History'] = -0.60 * feature_importance_map['Credit_History']
            
        # Income ratio
        applicant_income = raw_features['ApplicantIncome']
        coapplicant_income = raw_features['CoapplicantIncome']
        total_income = applicant_income + coapplicant_income
        loan_amount = raw_features['LoanAmount']
        loan_term = raw_features['Loan_Amount_Term']
        
        # Scale values contribution
        scaled_income = scaled_features['ApplicantIncome']
        contributions['ApplicantIncome'] = float(scaled_income * feature_importance_map['ApplicantIncome'] * 0.15)
        
        scaled_coincome = scaled_features['CoapplicantIncome']
        contributions['CoapplicantIncome'] = float(scaled_coincome * feature_importance_map['CoapplicantIncome'] * 0.12)
        
        # Debt-to-income ratio contribution
        monthly_payment = (loan_amount * 1000) / loan_term
        dti_ratio = monthly_payment / (total_income / 12.0)
        
        # Higher debt reduces probability, lower debt increases it
        if dti_ratio > 0.40:
            contributions['LoanAmount'] = -0.30 * feature_importance_map['LoanAmount']
        elif dti_ratio < 0.20:
            contributions['LoanAmount'] = 0.15 * feature_importance_map['LoanAmount']
        else:
            contributions['LoanAmount'] = 0.02 * feature_importance_map['LoanAmount']
            
        contributions['Loan_Amount_Term'] = float(-scaled_features['Loan_Amount_Term'] * feature_importance_map['Loan_Amount_Term'] * 0.05)
        
        # Demographics & settings
        contributions['Education'] = 0.08 * feature_importance_map['Education'] if raw_features['Education'] == 1 else -0.05 * feature_importance_map['Education']
        contributions['Property_Area'] = 0.05 * feature_importance_map['Property_Area'] if raw_features['Property_Area'] == 1 else (-0.03 * feature_importance_map['Property_Area'] if raw_features['Property_Area'] == 0 else 0.01)
        contributions['Married'] = 0.03 * feature_importance_map['Married'] if raw_features['Married'] == 1 else -0.01 * feature_importance_map['Married']
        contributions['Gender'] = 0.005 * feature_importance_map['Gender'] if raw_features['Gender'] == 1 else -0.005
        contributions['Dependents'] = float(-0.02 * raw_features['Dependents'] * feature_importance_map['Dependents'])
        contributions['Self_Employed'] = -0.04 * feature_importance_map['Self_Employed'] if raw_features['Self_Employed'] == 1 else 0.02 * feature_importance_map['Self_Employed']
        
        # Normalize contributions to sum up to approval probability (roughly)
        sum_contribs = sum(contributions.values())
        if sum_contribs != 0:
            factor = (approval_prob - 0.5) / abs(sum_contribs)
            for k in contributions:
                contributions[k] = round(contributions[k] * factor * 100, 2)
                
        # Split into positive and negative features
        positive_features = []
        negative_features = []
        
        feature_labels = {
            'Gender': 'Gender (Male/Female)',
            'Married': 'Marital Status (Married/Single)',
            'Dependents': 'Number of Dependents',
            'Education': 'Education Level (Graduate/Undergrad)',
            'Self_Employed': 'Employment Type (Self-Employed/Salaried)',
            'ApplicantIncome': 'Applicant Monthly Income',
            'CoapplicantIncome': 'Co-applicant Monthly Income',
            'LoanAmount': 'Requested Loan Amount',
            'Loan_Amount_Term': 'Loan Repayment Term',
            'Credit_History': 'Credit History Score',
            'Property_Area': 'Property Location (Rural/Semiurban/Urban)'
        }
        
        # Explanation statements
        explanations = []
        for feat, val in contributions.items():
            lbl = feature_labels.get(feat, feat)
            if val >= 0:
                positive_features.append({'feature': feat, 'label': lbl, 'value': val})
            else:
                negative_features.append({'feature': feat, 'label': lbl, 'value': val})
                
            # Create a user-friendly descriptive sentence
            if feat == 'Credit_History':
                msg = "Excellent credit history record boosts your eligibility." if credit_history_val == 1.0 else "Absence of a clean credit history record is a major risk factor."
            elif feat == 'ApplicantIncome':
                msg = f"Applicant income of ${applicant_income:,.2f} provides a strong repayment capability." if val >= 0 else f"Applicant income of ${applicant_income:,.2f} is relatively low for the loan request."
            elif feat == 'LoanAmount':
                msg = f"Requested loan amount of ${loan_amount * 1000:,.2f} is well-proportioned." if val >= 0 else f"Requested loan amount of ${loan_amount * 1000:,.2f} is high relative to your income."
            elif feat == 'Education':
                msg = "Graduate education status represents low risk profile." if raw_features['Education'] == 1 else "Non-graduate status slightly reduces standard scoring points."
            elif feat == 'Property_Area':
                msg = "Property located in Semi-urban area provides premium collateral value." if raw_features['Property_Area'] == 1 else ("Property in Rural area has lower valuation rating." if raw_features['Property_Area'] == 0 else "Property in Urban area has stable valuation rating.")
            else:
                msg = f"{lbl} has a {'positive' if val >= 0 else 'negative'} impact on application scoring."
                
            explanations.append({'feature': feat, 'impact': val, 'text': msg})
            
        # Sort positive and negative features by impact magnitude
        positive_features = sorted(positive_features, key=lambda x: x['value'], reverse=True)
        negative_features = sorted(negative_features, key=lambda x: x['value'])
        
        # Confidence score mapping
        if approval_prob > 0.85 or approval_prob < 0.15:
            confidence = "High Confidence"
        elif approval_prob > 0.65 or approval_prob < 0.35:
            confidence = "Medium Confidence"
        else:
            confidence = "Low Confidence (Borderline Case)"
            
        return {
            'confidence': confidence,
            'contributions': contributions,
            'positive_features': positive_features,
            'negative_features': negative_features,
            'explanations': explanations
        }

# Global instance for use in routes
predictor = LoanPredictor()
