"""
tests/test_agents.py - Unit and Integration Tests for Multi-Agent Banking Architecture (INR / ₹).
Tests:
1. Indian Rupee formatting (format_inr, format_inr_lakh_crore) and digit grouping.
2. Core banking tools in INR (Aarav Sharma balance check, transaction history).
3. Risk/Fraud explainable rules engine with INR thresholds and international surveillance.
4. Credit/Loan agent (reducing-balance EMI calculation in INR, FOIR/DTI loan underwriting).
5. Supervisor agent routing, Indian natural language parsing (Lakhs/Crores), and execution trace integrity.
"""

import pytest
import os
import math
from database import init_db, get_account_by_number, get_transactions
from banking_tools import (
    format_inr,
    format_inr_lakh_crore,
    check_balance,
    get_transaction_history,
    inspect_transactions_for_fraud,
    calculate_loan_emi,
    evaluate_loan_eligibility,
    get_general_banking_faq,
)
from agents import SupervisorAgent, check_ollama_availability


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database is freshly seeded with INR synthetic data."""
    init_db(force_reset=True)


# -----------------------------------------------------------------------------
# Test 1: Indian Rupee (INR) Formatting and Digit Grouping
# -----------------------------------------------------------------------------
def test_inr_formatting():
    """Verify Indian numbering system digit grouping and ₹ currency symbol."""
    assert format_inr(0) == "₹0.00"
    assert format_inr(500) == "₹500.00"
    assert format_inr(1500) == "₹1,500.00"
    assert format_inr(25000) == "₹25,000.00"
    assert format_inr(100000) == "₹1,00,000.00"      # 1 Lakh
    assert format_inr(125000) == "₹1,25,000.00"      # 1.25 Lakh
    assert format_inr(1500000) == "₹15,00,000.00"    # 15 Lakhs
    assert format_inr(10000000) == "₹1,00,00,000.00" # 1 Crore

    # Check without symbol
    assert format_inr(125000, include_symbol=False) == "1,25,000.00"

    # Check Lakh / Crore convenience labels
    assert "Lakh" in format_inr_lakh_crore(500000)
    assert "Crore" in format_inr_lakh_crore(15000000)


# -----------------------------------------------------------------------------
# Test 2: Banking Tools Factual Ground Truth in INR
# -----------------------------------------------------------------------------
def test_banking_tools_balance_and_transactions():
    """Verify factual balance check and transaction history queries in INR."""
    res = check_balance("ACC-982104")
    assert res["success"] is True
    assert res["customer_name"] == "Aarav Sharma"
    assert res["balance"] == 485250.00
    assert res["currency"] == "INR"
    assert res["currency_symbol"] == "₹"
    assert res["formatted_balance"] == "₹4,85,250.00"
    assert res["status"] == "ACTIVE"

    tx_res = get_transaction_history("ACC-982104", limit=5)
    assert tx_res["success"] is True
    assert tx_res["currency"] == "INR"
    assert tx_res["count"] > 0
    # Confirm every transaction has formatted INR amount
    for t in tx_res["transactions"]:
        assert "₹" in t["formatted_amount"]
        assert "$" not in t["formatted_amount"]


# -----------------------------------------------------------------------------
# Test 3: Risk / Fraud Explainable Rules Engine with INR Thresholds
# -----------------------------------------------------------------------------
def test_fraud_detection_explainable_rules():
    """Verify explainable fraud rules identify high-value INR spikes and foreign location anomalies."""
    fraud_res = inspect_transactions_for_fraud("ACC-982104", large_amount_threshold=150000.0)
    assert fraud_res["success"] is True
    assert fraud_res["currency"] == "INR"
    assert fraud_res["flagged_count"] >= 2
    assert fraud_res["overall_status"] == "SECURITY_ALERT"

    flagged_merchants = [item["merchant"] for item in fraud_res["flagged_transactions"]]
    assert "Apex Global Offshore Capital" in flagged_merchants
    assert "Euronet Lisbon ATM" in flagged_merchants

    first_flagged = fraud_res["flagged_transactions"][0]
    assert "₹" in first_flagged["formatted_amount"]
    assert "$" not in first_flagged["formatted_amount"]
    assert "triggered_rules" in first_flagged
    assert len(first_flagged["triggered_rules"]) >= 1
    assert "explanation" in first_flagged
    assert first_flagged["risk_score"] > 50


# -----------------------------------------------------------------------------
# Test 4: Credit / Loan Reducing-Balance EMI & Underwriting Simulation in INR
# -----------------------------------------------------------------------------
def test_loan_emi_and_eligibility():
    """Verify reducing-balance EMI calculation and FOIR/DTI underwriting in INR."""
    # Principal: ₹5,00,000, 12% APR, 12 months
    # Monthly rate r = 0.12/12 = 0.01. Factor = (1.01)^12 = 1.12682503.
    # EMI = 500000 * 0.01 * 1.12682503 / 0.12682503 = ₹44,424.39
    emi = calculate_loan_emi(principal=500000.0, annual_interest_rate=12.0, tenure_months=12)
    assert emi["success"] is True
    assert emi["currency"] == "INR"
    assert math.isclose(emi["monthly_emi"], 44424.39, abs_tol=0.5)
    assert emi["formatted_emi"] == "₹44,424.39"
    assert emi["total_payment"] > 500000.0
    assert "₹" in emi["formatted_total_interest"]
    assert "$" not in emi["formatted_emi"]

    # Prime customer (Credit score 765, Monthly income ₹85,000) -> Should be APPROVED
    approved_check = evaluate_loan_eligibility(
        monthly_income=85000.0,
        credit_score=765,
        requested_loan_amount=500000.0,
        tenure_months=36,
        annual_interest_rate=9.5,
        existing_monthly_debt=5000.0
    )
    assert approved_check["status"] == "APPROVED"
    assert approved_check["is_simulation"] is True
    assert approved_check["dti_ratio"] <= 45.0
    assert "₹" in approved_check["formatted_projected_emi"]

    # High-risk customer (Credit score 550) -> Should be REJECTED
    rejected_check = evaluate_loan_eligibility(
        monthly_income=30000.0,
        credit_score=550,
        requested_loan_amount=2500000.0,
        tenure_months=24,
        annual_interest_rate=14.0
    )
    assert rejected_check["status"] == "REJECTED"


# -----------------------------------------------------------------------------
# Test 5: Supervisor Routing, Indian NLP Parsing, and Fallback Resilience
# -----------------------------------------------------------------------------
def test_supervisor_agent_routing_and_indian_nlp():
    """Verify Supervisor routes queries correctly and parses Indian terms like Lakhs."""
    supervisor = SupervisorAgent()

    # Case A: Balance inquiry in INR
    res_balance = supervisor.process_request("What is my current account balance in Rupees?", account_number="ACC-982104")
    assert res_balance["success"] is True
    assert res_balance["selected_agent"] == "Banking/Customer Agent"
    assert res_balance["intent"] == "CUSTOMER_BANKING"
    assert "₹" in res_balance["response_text"]
    assert "$" not in res_balance["response_text"]

    # Case B: Fraud query in INR
    res_fraud = supervisor.process_request("Check my account for any suspicious transactions or fraud flags", account_number="ACC-982104")
    assert res_fraud["success"] is True
    assert res_fraud["selected_agent"] == "Risk/Fraud Agent"
    assert res_fraud["intent"] == "FRAUD_DETECTION"
    assert "₹" in res_fraud["response_text"]
    assert "$" not in res_fraud["response_text"]

    # Case C: Indian natural language loan query ("5 lakh loan")
    res_loan = supervisor.process_request("Calculate EMI for a 5 lakh loan for 3 years at 9.5%", account_number="ACC-982104")
    assert res_loan["success"] is True
    assert res_loan["selected_agent"] == "Credit/Loan Agent"
    assert res_loan["intent"] == "LOAN_CREDIT"
    assert "₹" in res_loan["response_text"]
    assert "$" not in res_loan["response_text"]

    # Case D: FAQ query
    res_faq = supervisor.process_request("What is your branch IFSC code?", account_number="ACC-982104")
    assert res_faq["success"] is True
    assert res_faq["selected_agent"] == "General Banking/FAQ Agent"

    # Execution trace completeness
    trace = res_balance["execution_trace"]
    assert len(trace) >= 3
    assert any(t["stage"] == "Supervisor Intent Classification" for t in trace)
    assert any(t["stage"] == "Agent Routing" for t in trace)
    assert any(t["stage"] == "Response Finalization" for t in trace)
