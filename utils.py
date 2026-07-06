import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def calculate_emi(principal, annual_rate, term_months):
    """Calculates EMI (Equated Monthly Installment) and total repayment details."""
    p = float(principal)
    r = float(annual_rate) / 12.0 / 100.0  # Monthly interest rate
    n = float(term_months)
    
    if r == 0:
        emi_val = p / n
        emi_rounded = round(emi_val, 2)
        total_payment = emi_rounded * n
        total_interest = total_payment - p
        emi = emi_rounded
    else:
        emi_val = p * r * ((1 + r)**n) / (((1 + r)**n) - 1)
        emi_rounded = round(emi_val, 2)
        total_payment = emi_rounded * n
        total_interest = total_payment - p
        emi = emi_rounded
        
    return {
        'emi': emi,
        'total_payment': round(total_payment, 2),
        'total_interest': round(total_interest, 2),
        'principal': round(p, 2),
        'rate': annual_rate,
        'term': int(term_months)
    }

def compare_loans(principal, term_months, rates_list):
    """Compares loan offers with different interest rates."""
    comparison = []
    for rate in rates_list:
        emi_details = calculate_emi(principal, rate, term_months)
        comparison.append(emi_details)
    return comparison

def generate_pdf_report(prediction, user_name):
    """Generates a professional PDF report for a loan prediction request."""
    # We will return bytes of the PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E1B4B'),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=25
    )
    
    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1E1B4B'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=8
    )
    
    status_yes_style = ParagraphStyle(
        'StatusYes',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#16A34A'),
        spaceAfter=10
    )
    
    status_no_style = ParagraphStyle(
        'StatusNo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#DC2626'),
        spaceAfter=10
    )

    story = []
    
    # 1. Header
    story.append(Paragraph("Smart Lender Assessment Report", title_style))
    story.append(Paragraph(f"AI-Powered Loan Eligibility Analysis  |  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Status Summary
    story.append(Paragraph("Evaluation Summary", h2_style))
    is_eligible = prediction.is_eligible
    status_text = "ELIGIBLE - Approved for Review" if is_eligible == 1 else "INELIGIBLE - Standard Requirements Not Met"
    status_paragraph_style = status_yes_style if is_eligible == 1 else status_no_style
    story.append(Paragraph(f"Application Status: {status_text}", status_paragraph_style))
    
    prob = prediction.approval_probability * 100
    story.append(Paragraph(f"Approval Probability Score: <b>{prob:.2f}%</b>", body_style))
    
    explanation_dict = prediction.get_explanation()
    confidence = explanation_dict.get('confidence', 'N/A')
    story.append(Paragraph(f"Decision Confidence Level: <b>{confidence}</b>", body_style))
    story.append(Spacer(1, 15))
    
    # 3. Applicant Parameters Table
    story.append(Paragraph("Applicant Profile Details", h2_style))
    
    data = [
        [Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style), Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style)],
        ["Applicant Name", user_name, "Credit History Status", "Satisfactory (1.0)" if prediction.credit_history == 1.0 else "Unsatisfactory (0.0)"],
        ["Gender", prediction.gender, "Education Status", prediction.education],
        ["Marital Status", "Married" if prediction.married == "Yes" else "Single", "Employment Status", "Self-Employed" if prediction.self_employed == "Yes" else "Salaried / Other"],
        ["Dependents Count", prediction.dependents, "Property Location Type", prediction.property_area],
        ["Applicant Income ($)", f"{int(prediction.applicant_income)}", "Co-applicant Income ($)", f"{int(prediction.coapplicant_income)}"],
        ["Requested Loan Amount ($ Thousands)", f"{int(prediction.loan_amount)}", "Loan Repayment Term", f"{int(prediction.loan_amount_term)} Months"]
    ]
    
    t = Table(data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # 4. Explainability Section
    story.append(Paragraph("AI Explainability & Decision Logic", h2_style))
    story.append(Paragraph("The analysis below highlights the positive and negative key parameters contributing to this recommendation:", body_style))
    story.append(Spacer(1, 5))
    
    # Detail contributions
    positive_feats = explanation_dict.get('positive_features', [])
    negative_feats = explanation_dict.get('negative_features', [])
    
    expl_data = [[Paragraph("<b>Key Decision Driver</b>", body_style), Paragraph("<b>Scoring Impact</b>", body_style)]]
    
    for f in positive_feats[:3]:
        expl_data.append([
            Paragraph(f"• {f.get('label', f.get('feature'))} (Positive Driver)", body_style),
            Paragraph(f"+{f.get('value')}%", ParagraphStyle('Green', parent=body_style, textColor=colors.HexColor('#16A34A')))
        ])
        
    for f in negative_feats[:3]:
        expl_data.append([
            Paragraph(f"• {f.get('label', f.get('feature'))} (Negative Driver)", body_style),
            Paragraph(f"{f.get('value')}%", ParagraphStyle('Red', parent=body_style, textColor=colors.HexColor('#DC2626')))
        ])
        
    t_expl = Table(expl_data, colWidths=[5.0 * inch, 2.2 * inch])
    t_expl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_expl)
    story.append(Spacer(1, 25))
    
    # 5. Disclaimer / Sign-off
    story.append(Paragraph("<b>Disclaimer:</b> This decision scoring estimation is generated using a validated Machine Learning algorithm trained on historical bank databases. Final manual documentation verification is mandatory for administrative disbursement.", ParagraphStyle('Disclaimer', parent=body_style, fontSize=8, leading=10, textColor=colors.HexColor('#9CA3AF'))))
    
    # Build Document
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()

def send_mock_email(email, subject, body):
    """Simulates sending an email notification, printing the logs."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[EMAIL MOCK] [{timestamp}] To: {email} | Subject: {subject} | Body Summary: {body[:80]}..."
    print(log_msg)
    # Return message content to display to the user if needed
    return log_msg

def send_mock_sms(phone, message):
    """Simulates sending an SMS notification, printing the logs."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[SMS MOCK] [{timestamp}] To: {phone} | Content: {message}"
    print(log_msg)
    return log_msg
