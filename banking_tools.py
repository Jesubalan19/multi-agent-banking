"""
banking_tools.py - Deterministic Core Banking Tools (INR / Indian Banking).
Provides factual data retrieval, explainable fraud rule evaluations,
and mathematical EMI / loan underwriting calculations denominated in Indian Rupees (₹).
Features full Indian number formatting (lakhs & crores) and deterministic rule execution.
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


def format_inr(number: Optional[float], include_symbol: bool = True, include_decimal: bool = True) -> str:
    """
    Format a numeric amount according to the Indian numbering system.
    Examples:
        50000 -> ₹50,000.00
        125000 -> ₹1,25,000.00
        1500000 -> ₹15,00,000.00 (15 Lakhs)
        10000000 -> ₹1,00,00,000.00 (1 Crore)
    """
    if number is None:
        return "₹0.00" if include_symbol else "0.00"

    is_negative = number < 0
    abs_num = abs(float(number))

    parts = f"{abs_num:.2f}".split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ",".join(groups) + "," + last_three

    res = f"{formatted_int}.{decimal_part}" if include_decimal else formatted_int
    prefix = "-" if is_negative else ""
    sym = "₹" if include_symbol else ""
    return f"{prefix}{sym}{res}"


def format_inr_lakh_crore(number: float) -> str:
    """
    Format large INR figures using convenient Lakh / Crore descriptors.
    Example:
        485250 -> ₹4,85,250 (₹4.85 Lakhs)
        1850000 -> ₹18,50,000 (₹18.50 Lakhs)
        12000000 -> ₹1,20,00,000 (₹1.20 Crores)
    """
    base = format_inr(number, include_symbol=True, include_decimal=False)
    abs_val = abs(number)
    if abs_val >= 10000000:
        cr = abs_val / 10000000.0
        return f"{base} ({cr:.2f} Crores)"
    elif abs_val >= 100000:
        lakh = abs_val / 100000.0
        return f"{base} ({lakh:.2f} Lakhs)"
    return base


def check_balance(account_number: str) -> Dict[str, Any]:
    """
    Retrieve factual account balance and status from the core banking database in INR.
    """
    account = get_account_by_number(account_number)
    if not account:
        return {
            "success": False,
            "error": f"Account '{account_number}' not found in banking system."
        }

    balance_val = float(account["balance"])
    return {
        "success": True,
        "account_number": account["account_number"],
        "customer_name": account["customer_name"],
        "account_type": account["account_type"],
        "balance": balance_val,
        "currency": "INR",
        "currency_symbol": "₹",
        "status": account["status"],
        "formatted_balance": format_inr(balance_val),
        "formatted_balance_words": format_inr_lakh_crore(balance_val),
    }


def get_transaction_history(account_number: str, limit: int = 5) -> Dict[str, Any]:
    """
    Fetch the recent transaction history for an account in INR.
    """
    account = get_account_by_number(account_number)
    if not account:
        return {
            "success": False,
            "error": f"Account '{account_number}' not found."
        }

    raw_txns = get_transactions(account_number=account_number, limit=limit)
    formatted_txns = []
    for t in raw_txns:
        txn_dict = dict(t)
        txn_dict["formatted_amount"] = format_inr(float(t["amount"]))
        formatted_txns.append(txn_dict)

    return {
        "success": True,
        "account_number": account_number,
        "customer_name": account["customer_name"],
        "count": len(formatted_txns),
        "currency": "INR",
        "transactions": formatted_txns,
    }


def inspect_transactions_for_fraud(
    account_number: str,
    large_amount_threshold: float = 150000.0,  # Default ₹1,50,000 threshold
    balance_ratio_threshold: float = 0.50
) -> Dict[str, Any]:
    """
    Deterministic Rule-Based Fraud Detection Engine for Indian Banking.
    Inspects account transactions against explainable security rules:
    - Rule 1: High Transaction Amount Spike (default >= ₹1,50,000)
    - Rule 2: Sudden Balance Depletion (>50% of available account funds)
    - Rule 3: Geo-Velocity / International Location Mismatch (Foreign country vs India)
    - Rule 4: High-Risk Channel Spike (International Wire, Foreign ATM >= ₹30,000)
    """
    account = get_account_by_number(account_number)
    if not account:
        return {
            "success": False,
            "error": f"Account '{account_number}' not found."
        }

    customer_country = account.get("home_country", "India").lower()
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

        # Rule 1: High Absolute Amount in INR
        if amount >= large_amount_threshold:
            triggered_rules.append(
                f"High-Value Spike: Amount ({format_inr(amount)}) >= {format_inr(large_amount_threshold)} threshold"
            )
            risk_score += 40

        # Rule 2: Balance Depletion Risk
        if current_balance > 0 and (amount / (current_balance + amount)) >= balance_ratio_threshold:
            ratio_pct = (amount / (current_balance + amount)) * 100
            triggered_rules.append(
                f"Balance Depletion Risk: Transaction represents {ratio_pct:.1f}% of total account liquidity"
            )
            risk_score += 25

        # Rule 3: Geographic Discrepancy (International transaction outside India)
        if customer_country not in location:
            triggered_rules.append(
                f"Location Mismatch: Executed in '{t['location']}', outside registered home country '{account.get('home_country')}'"
            )
            risk_score += 35

        # Rule 4: High Risk International Channel
        if ("Wire" in category or "ATM" in category or "Withdrawal" in category) and amount >= 30000.0 and customer_country not in location:
            triggered_rules.append(
                f"High-Risk Channel: Overseas {category} of {format_inr(amount)} without pre-authorized international travel flag"
            )
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
                "formatted_amount": format_inr(amount),
                "category": category,
                "location": t["location"],
                "timestamp": t["timestamp"],
                "risk_score": min(risk_score, 100),
                "risk_level": risk_level,
                "triggered_rules": triggered_rules,
                "explanation": (
                    f"Transaction of {format_inr(amount)} at '{t['merchant']}' triggered "
                    f"{len(triggered_rules)} security rule(s): {reason_str}"
                ),
            })

    return {
        "success": True,
        "account_number": account_number,
        "customer_name": account["customer_name"],
        "home_country": account.get("home_country"),
        "currency": "INR",
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
    Standard Reducing-Balance Equated Monthly Installment (EMI) Formula in INR:
    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    where:
      P = Principal loan amount in INR (₹)
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
        # Standard reducing-balance annuity formula
        factor = math.pow(1 + monthly_rate, tenure_months)
        monthly_emi = principal * monthly_rate * factor / (factor - 1)
        total_payment = monthly_emi * tenure_months
        total_interest = total_payment - principal

    return {
        "success": True,
        "principal": float(principal),
        "annual_interest_rate": float(annual_interest_rate),
        "tenure_months": int(tenure_months),
        "currency": "INR",
        "monthly_emi": round(monthly_emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(total_payment, 2),
        "formatted_emi": format_inr(monthly_emi),
        "formatted_principal": format_inr(principal),
        "formatted_total_interest": format_inr(total_interest),
        "formatted_total_payment": format_inr(total_payment),
        "formatted_principal_lakhs": format_inr_lakh_crore(principal),
        "explanation": (
            f"For a principal of {format_inr(principal)} ({format_inr_lakh_crore(principal)}) at "
            f"{annual_interest_rate}% annual reducing interest over {tenure_months} months, "
            f"the calculated monthly EMI is {format_inr(monthly_emi)}. "
            f"Total interest payable over the term will be {format_inr(total_interest)}."
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
    Explainable Credit & Loan Underwriting Rule Engine for Indian Banking:
    - Debt-to-Income / FOIR (Fixed Obligation to Income Ratio) limit <= 45% of net monthly income
    - Credit Score tiers (CIBIL / Experian benchmark):
        - 720+ : Prime (Fast-track approval)
        - 620-719: Moderate (Standard underwriting)
        - Below 620: High Risk (Unfavorable)
    Clearly labeled as a simulation.
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

    reasons = []
    if credit_score >= 700 and dti_ratio <= 45.0:
        status = "APPROVED"
        reasons.append(f"Credit score ({credit_score}) meets prime Indian retail banking benchmark (>= 700).")
        reasons.append(f"Fixed Obligation / DTI ratio is healthy at {dti_ratio:.1f}% (policy ceiling: <= 45%).")
    elif credit_score >= 620 and dti_ratio <= 40.0:
        status = "CONDITIONALLY APPROVED"
        reasons.append(f"Credit score ({credit_score}) is moderate; qualifies subject to salary slip verification.")
        reasons.append(f"Fixed Obligation / DTI ratio is {dti_ratio:.1f}%, within acceptable threshold.")
    else:
        status = "REJECTED"
        if credit_score < 620:
            reasons.append(f"Credit score ({credit_score}) is below minimum requirement of 620.")
        if dti_ratio > 45.0:
            reasons.append(f"DTI / FOIR ratio ({dti_ratio:.1f}%) exceeds the responsible lending cap of 45%.")

    return {
        "success": True,
        "status": status,
        "is_simulation": True,
        "simulation_note": "Simulated underwriting evaluation for demonstration purposes.",
        "monthly_income": monthly_income,
        "credit_score": credit_score,
        "requested_loan_amount": requested_loan_amount,
        "formatted_requested_amount": format_inr(requested_loan_amount),
        "projected_emi": projected_emi,
        "formatted_projected_emi": format_inr(projected_emi),
        "dti_ratio": round(dti_ratio, 1),
        "max_affordable_emi": round(max_affordable_emi, 2),
        "formatted_max_affordable_emi": format_inr(max_affordable_emi),
        "reasons": reasons,
        "explanation": (
            f"Simulated Loan Decision: {status}. Projected EMI: {format_inr(projected_emi)}/month. "
            f"FOIR/DTI: {dti_ratio:.1f}%. " + " ".join(reasons)
        )
    }


def get_general_banking_faq(query: str) -> Dict[str, Any]:
    """
    Deterministic FAQ responder for Indian retail banking inquiries.
    """
    q = query.lower()
    if any(k in q for k in ["hour", "time", "open", "close"]):
        answer = (
            "Branch banking hours are Monday to Saturday (excluding 2nd and 4th Saturdays), "
            "10:00 AM – 4:00 PM IST. UPI, IMPS, RTGS, NetBanking, and ATM services are operational 24/7."
        )
        topic = "Banking Hours"
    elif any(k in q for k in ["ifsc", "micr", "routing", "swift", "neft", "branch code"]):
        answer = (
            "Simulated Bank IFSC Code is SYNTH0001234 (Nariman Point Branch, Mumbai). "
            "MICR Code: 400024012. Swift Code: SYNTINBBXXX."
        )
        topic = "IFSC & Routing Details"
    elif any(k in q for k in ["dicgc", "insure", "protection", "deposit safe", "fdic"]):
        answer = (
            "All customer deposits are simulated as insured up to ₹5,00,000 (₹5 Lakhs) per depositor "
            "under Reserve Bank / DICGC deposit insurance guidelines."
        )
        topic = "Deposit Insurance (DICGC)"
    elif any(k in q for k in ["card lost", "stolen", "freeze", "lock", "upi block"]):
        answer = (
            "To immediately freeze your debit card or block your UPI handle, go to the Security Tab or "
            "call toll-free 1800-SYNTHETIC. Immediate zero-liability protection is active."
        )
        topic = "Card & UPI Security"
    else:
        answer = (
            "Welcome to Synthetic Core Bank. You can check your account balance, audit transactions for suspicious activity, "
            "or simulate loan EMI eligibility in Indian Rupees (₹)."
        )
        topic = "General Inquiry"

    return {
        "success": True,
        "topic": topic,
        "answer": answer
    }
