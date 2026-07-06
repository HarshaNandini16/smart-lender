# User Manual: Smart Lender Portal

This manual explains how to interact with the web interface of the Smart Lender system.

## 1. Landing Page Features

- **Navigation**: Access the landing pages (Home, About, Services, Contact) using the navigation bar.
- **Loan EMI Calculator**: Scroll down the home page, enter the principal, rate, and term to instantly view monthly payments, total interest, and total repayments.
- **Loan Offers Comparison**: Enter principal, term, and multiple comma-separated interest rates to compare the repayment metrics side-by-side.
- **LendBot Assistant**: Click the chat bubble in the bottom right corner, write queries about loan terms or eligibility criteria, and receive instant help.

---

## 2. User Evaluation Portal

1. **Sign Up / Sign In**: Register a new user account or login using existing credentials.
2. **Dashboard**: Track your total submissions, pass ratio, and compare model CV accuracies on the chart dashboards.
3. **Loan Form**: Navigate to "Predict Loan", fill in demographic and financial parameters, and click "Evaluate Eligibility".
4. **Results Analysis**:
   - Status will show **ELIGIBLE** (Approved) or **INELIGIBLE** (Rejected).
   - Read the confidence scores and positive/negative drivers (Explainable AI breakdown).
   - Click "Download PDF" to export the official assessment sheet or "Email Report" to simulate emailing.

---

## 3. Administrator Console

1. **Admin Sign In**: Navigate to the Sign In page and click "Administrator Login". Log in with username `admin` and password `Admin@123456`.
2. **Dashboard Widgets**: Audit total registered users, global predictions, and eligible share distributions.
3. **User Manager**: View all registered users, see user profiles, and delete user accounts.
4. **Predictions DB**: View all prediction metrics submitted by all users. Click the eye icon to view details, or delete logs.
5. **System Logs**: Audit all login attempts, database deletions, and profile updates.
6. **Export Database**: Click "Export Predictions CSV" to download the complete database of evaluations.
