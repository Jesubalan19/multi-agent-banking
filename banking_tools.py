"""
banking_tools.py - Deterministic Core Banking Tools.
Provides factual data retrieval, explainable fraud rule evaluations,
and mathematical EMI / loan eligibility calculations.
These functions serve as the ground truth for all agent reasoning.
"""

from typing import Dict, Any, List, Optional
import math
from database import (
    get_account_by_number,
    get_customer_by_id,
    get_transactions,
    flag_transaction,
    get_all_customers,
)


def check_balance(account_number: str) -> Dict[str, Any]:
    """
    Retrieve factual account balance and status from the core banking database.
    """
    account = get_account_by_number(account_number)
    if not account:
        return {
            "success": False,
            "error": f"Account '{account_number}' not found in banking system."
        }
    
    return {
        "success": True,
        "account_number": account["account_number"],
        "customer_name": account["customer_name"],
        "account_type": account["account_type"],
        "balance": float(account["balance"]),
        "currency": account["currency"],
        "status": account["status"],
        "formatted_balance": f"{account['currency']} {float(account['balance']):,.2f}",
    }


def get_transaction_history(account_number: str, limit: int = 5) -> Dict[str, Any]:
    """
    Fetch the recent transaction history for an account.
    """
    account = get_account_by_number(account_number)
    if not account:
        return {
            "success": False,
            "error": f"Account '{account_number}' not found."
        }

    txns = get_transactions(account_number=account_number, limit=limit)
    return {
        "success": True,
        "account_number": account_number,
        "customer_name": account["customer_name"],
        "count": len(txns),
        "transactions": txns,
    }


def inspect_transactions_for_fraud(
    account_number: str,
    large_amount_threshold: float = 3000.0,
    balance_ratio_threshold: float = 0.50
) -> Dict[str, Any]:
    """
    Deterministic Rule-Based Fraud Detection Engine.
    Inspects account transactions against explainable banking security rules:
    - Rule 1: High Transaction Amount Threshold ($3,000 default)
    - Rule 2: Sudden Balance Depletion (>50% of available account balance)
    - Rule 3: Geo-Velocity / International Location Mismatch (Foreign country vs Home country)
    - Rule 4: High-Risk Category Pattern (Wire Transfer, International ATM)
    """
    account = get_account_by_number(account_number)
    if not account:
        return {
            "success": False,
            "error": f"Account '{account_number}' not found."
        }

    customer_country = account.get("home_country", "United States").lower()
    current_balance = float(account["balance"])
    txns = get_transactions(account_number=account_number, limit=20)

    inspected_count = len(txns)
    flagged_records: List[Dict[str, Any]] = []

    for t in txns:
        amount = float(t["amount"])
        location = t["location"].lower()
        category = t["category"]
        triggered_rules = []
        risk_score = 10  # Baseline low risk

        # Rule 1: High Absolute Amount
        if amount >= large_amount_threshold:
            triggered_rules.append(f"High-Value Spike: Amount (${amount:,.2f}) >= ${large_amount_threshold:,.2f} threshold")
            risk_score += 40

        # Rule 2: High Ratio of Current Account Balance
        if current_balance > 0 and (amount / (current_balance + amount)) >= balance_ratio_threshold:
            ratio_pct = (amount / (current_balance + amount)) * 100
            triggered_rules.append(f"Balance Depletion Risk: Transaction represents {ratio_pct:.1f}% of total funds")
            risk_score += 25

        # Rule 3: Geographic Discrepancy
        if customer_country not in location:
            triggered_rules.append(f"Location Mismatch: Executed in '{t['location']}', outside registered '{account.get('home_country')}'")
            risk_score += 35

        # Rule 4: High Risk Category
        if category in ["Wire Transfer", "Cash Withdrawal"] and amount >= 1000.0:
            triggered_rules.append(f"High-Risk Channel: {category} exceeding $1,000 without prior travel notification")
            risk_score += 20

        # Assign risk level and flag if rules triggered
        if triggered_rules:
            risk_level = "CRITICAL" if risk_score >= 80 else ("HIGH" if risk_score >= 50 else "MEDIUM")
            reason_str = " | ".join(triggered_rules)
            flag_transaction(t["txn_id"], reason_str)

            flagged_records.append({
                "txn_id": t["txn_id"],
                "merchant": t["merchant"],
                "amount": amount,
                "formatted_amount": f"${amount:,.2f}",
                "category": category,
                "location": t["location"],
                "timestamp": t["timestamp"],
                "risk_score": min(risk_score, 100),
                "risk_level": risk_level,
                "triggered_rules": triggered_rules,
                "explanation": f"Transaction of ${amount:,.2f} at '{t['merchant']}' triggered {len(triggered_rules)} security rule(s): {reason_str}",
            })

    return {
        "success": True,
        "account_number": account_number,
        "customer_name": account["customer_name"],
        "home_country": account.get("home_country"),
        "total_evaluated": inspected_count,
        "flagged_count": len(flagged_records),
        "overall_status": "SECURITY_ALERT" if flagged_records else "CLEAN",
        "flagged_transactions": flagged_records,
    }


def calculate_loan_emi(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int
) -> Dict[str, Any]:
    """
    Standard Banking Equated Monthly Installment (EMI) Formula:
    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    where:
      P = Principal loan amount
      r = Monthly interest rate (annual_rate / 12 / 100)
      n = Tenure in months
    """
    if principal <= 0 or tenure_months <= 0:
        return {
            "success": False,
            "error": "Principal and tenure must be strictly greater than zero."
        }

    if annual_interest_rate <= 0:
        # Zero interest edge case
        monthly_emi = principal / tenure_months
        total_payment = principal
        total_interest = 0.0
    else:
        monthly_rate = (annual_interest_rate / 100.0) / 12.0
        # Standard annuity formula
        factor = math.pow(1 + monthly_rate, tenure_months)
        monthly_emi = principal * monthly_rate * factor / (factor - 1)
        total_payment = monthly_emi * tenure_months
        total_interest = total_payment - principal

    return {
        "success": True,
        "principal": float(principal),
        "annual_interest_rate": float(annual_interest_rate),
        "tenure_months": int(tenure_months),
        "monthly_emi": round(monthly_emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(total_payment, 2),
        "formatted_emi": f"${monthly_emi:,.2f}",
        "formatted_total_interest": f"${total_interest:,.2f}",
        "formatted_total_payment": f"${total_payment:,.2f}",
        "explanation": (
            f"For a principal of ${principal:,.2f} at {annual_interest_rate}% annual interest "
            f"over {tenure_months} months, the calculated monthly EMI is ${monthly_emi:,.2f}. "
            f"Total interest payable over the term will be ${total_interest:,.2f}."
        ),
    }


def evaluate_loan_eligibility(
    monthly_income: float,
    credit_score: int,
    requested_loan_amount: float,
    tenure_months: int = 36,
    annual_interest_rate: float = 10.5,
    existing_monthly_debt: float = 0.0
) -> Dict[str, Any]:
    """
    Explainable Credit & Loan Underwriting Rule Engine:
    - Debt-to-Income (DTI) ratio benchmark <= 45% of gross monthly income
    - Credit Score tiers:
        - 720+ : Tier 1 (Prime)
        - 650-719: Tier 2 (Near Prime)
        - Below 650: Tier 3 (Subprime / High Risk)
    """
    if monthly_income <= 0:
        return {"success": False, "error": "Monthly income must be positive."}

    emi_calc = calculate_loan_emi(requested_loan_amount, annual_interest_rate, tenure_months)
    if not emi_calc["success"]:
        return emi_calc

    projected_emi = emi_calc["monthly_emi"]
    total_monthly_obligations = existing_monthly_debt + projected_emi
    dti_ratio = (total_monthly_obligations / monthly_income) * 100.0

    max_affordable_emi = max(0.0, (monthly_income * 0.45) - existing_monthly_debt)
    
    # Underwriting Decision Matrix
    reasons = []
    if credit_score >= 700 and dti_ratio <= 45.0:
        status = "APPROVED"
        reasons.append(f"Credit score ({credit_score}) meets prime lending benchmark (>= 700).")
        reasons.append(f"Debt-to-Income (DTI) ratio is healthy at {dti_ratio:.1f}% (limit: <= 45%).")
    elif credit_score >= 620 and dti_ratio <= 40.0:
        status = "CONDITIONALLY APPROVED"
        reasons.append(f"Credit score ({credit_score}) is moderate; qualifies subject to income verification.")
        reasons.append(f"DTI ratio is {dti_ratio:.1f}%, within acceptable threshold.")
    else:
        status = "REJECTED"
        if credit_score < 620:
            reasons.append(f"Credit score ({credit_score}) is below minimum requirement of 620.")
        if dti_ratio > 45.0:
            reasons.append(f"DTI ratio ({dti_ratio:.1f}%) exceeds the responsible lending cap of 45%.")

    return {
        "success": True,
        "status": status,
        "monthly_income": monthly_income,
        "credit_score": credit_score,
        "requested_loan_amount": requested_loan_amount,
        "projected_emi": projected_emi,
        "dti_ratio": round(dti_ratio, 1),
        "max_affordable_emi": round(max_affordable_emi, 2),
        "reasons": reasons,
        "explanation": f"Loan decision: {status}. Projected EMI: ${projected_emi:,.2f}/mo. DTI: {dti_ratio:.1f}%. " + " ".join(reasons)
    }


def get_general_banking_faq(query: str) -> Dict[str, Any]:
    """
    Deterministic FAQ responder for standard retail banking inquiries.
    """
    q = query.lower()
    if any(k in q for k in ["hour", "time", "open", "close"]):
        answer = "Branch banking hours are Monday to Friday, 9:00 AM – 5:00 PM EST. Digital banking and ATM access are operational 24/7."
        topic = "Banking Hours"
    elif any(k in q for k in ["routing", "swift", "bic", "wire code"]):
        answer = "Synthetic Bank Domestic Routing Transit Number is 021000089. International SWIFT code is SYNTUS33XXX."
        topic = "Routing Information"
    elif any(k in q for k in ["fdic", "insure", "protection", "deposit safe"]):
        answer = "All customer deposits are simulated as insured up to $250,000 per depositor under standard FDIC banking guidelines."
        topic = "Deposit Insurance"
    elif any(k in q for k in ["card lost", "stolen", "freeze", "lock"]):
        answer = "To immediately lock a lost card, navigate to the Security Tab or call 1-800-SYNTHETIC. Immediate zero-liability protection is active."
        topic = "Card Security"
    else:
        answer = "Welcome to Synthetic Bank. You can check your account balance, audit transactions for suspicious activity, or simulate loan eligibility."
        topic = "General Inquiry"

    return {
        "success": True,
        "topic": topic,
        "answer": answer
    }
