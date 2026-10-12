"""
tests/test_agents.py - Unit and Integration Tests for Multi-Agent Banking Architecture.
Tests:
1. Supervisor intent classification and routing to specialized agents.
2. Core banking tools (Account balance check, transaction history).
3. Risk/Fraud explainable rules engine (threshold, location mismatch).
4. Credit/Loan agent (EMI formula accuracy, DTI loan underwriting).
5. Deterministic fallback mode resilience when Ollama is unavailable.
"""

import pytest
import os
import math
from database import init_db, get_account_by_number, get_transactions, DEFAULT_DB_PATH
from banking_tools import (
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
    """Ensure database is freshly seeded for test runs."""
    init_db(force_reset=True)


# -----------------------------------------------------------------------------
# Test 1: Banking Tools Factual Ground Truth
# -----------------------------------------------------------------------------
def test_banking_tools_balance_and_transactions():
    """Verify factual balance check and transaction history queries."""
    res = check_balance("ACC-982104")
    assert res["success"] is True
    assert res["customer_name"] == "Alex Rivera"
    assert res["balance"] == 14250.75
    assert res["status"] == "ACTIVE"

    tx_res = get_transaction_history("ACC-982104", limit=5)
    assert tx_res["success"] is True
    assert tx_res["count"] > 0
    assert len(tx_res["transactions"]) <= 5


# -----------------------------------------------------------------------------
# Test 2: Risk / Fraud Explainable Rules Engine
# -----------------------------------------------------------------------------
def test_fraud_detection_explainable_rules():
    """Verify explainable fraud rules identify high-value and foreign location anomalies."""
    fraud_res = inspect_transactions_for_fraud("ACC-982104", large_amount_threshold=3000.0)
    assert fraud_res["success"] is True
    assert fraud_res["flagged_count"] >= 2
    assert fraud_res["overall_status"] == "SECURITY_ALERT"

    flagged_merchants = [item["merchant"] for item in fraud_res["flagged_transactions"]]
    assert "Apex Offshore Holdings" in flagged_merchants
    assert "Euronet Lisbon ATM" in flagged_merchants

    # Check that explanation and triggered rules exist
    first_flagged = fraud_res["flagged_transactions"][0]
    assert "triggered_rules" in first_flagged
    assert len(first_flagged["triggered_rules"]) >= 1
    assert "explanation" in first_flagged
    assert first_flagged["risk_score"] > 50


# -----------------------------------------------------------------------------
# Test 3: Credit / Loan EMI and Eligibility Underwriting
# -----------------------------------------------------------------------------
def test_loan_emi_and_eligibility():
    """Verify standard financial EMI calculation and DTI underwriting rules."""
    # Principal: $10,000, 12% APR, 12 months
    # Monthly rate r = 0.12/12 = 0.01. Factor = (1.01)^12 = 1.126825.
    # EMI = 10000 * 0.01 * 1.126825 / 0.126825 = $888.49
    emi = calculate_loan_emi(principal=10000.0, annual_interest_rate=12.0, tenure_months=12)
    assert emi["success"] is True
    assert math.isclose(emi["monthly_emi"], 888.49, abs_tol=0.5)
    assert emi["total_payment"] > 10000.0

    # Prime customer (Credit score 750, Monthly income $8,000) -> Should be APPROVED
    approved_check = evaluate_loan_eligibility(
        monthly_income=8000.0,
        credit_score=750,
        requested_loan_amount=10000.0,
        tenure_months=24,
        annual_interest_rate=9.0
    )
    assert approved_check["status"] == "APPROVED"
    assert approved_check["dti_ratio"] < 45.0

    # High-risk customer (Credit score 550) -> Should be REJECTED
    rejected_check = evaluate_loan_eligibility(
        monthly_income=3000.0,
        credit_score=550,
        requested_loan_amount=50000.0,
        tenure_months=24,
        annual_interest_rate=12.0
    )
    assert rejected_check["status"] == "REJECTED"


# -----------------------------------------------------------------------------
# Test 4: Supervisor Agent Routing & Intent Classification
# -----------------------------------------------------------------------------
def test_supervisor_agent_routing():
    """Verify Supervisor routes queries to the correct specialized agents."""
    supervisor = SupervisorAgent()

    # Case A: Balance inquiry -> Banking/Customer Agent
    res_balance = supervisor.process_request("What is my current account balance?", account_number="ACC-982104")
    assert res_balance["success"] is True
    assert res_balance["selected_agent"] == "Banking/Customer Agent"
    assert res_balance["intent"] == "CUSTOMER_BANKING"

    # Case B: Fraud query -> Risk/Fraud Agent
    res_fraud = supervisor.process_request("Audit my account for any fraudulent or suspicious transactions", account_number="ACC-982104")
    assert res_fraud["success"] is True
    assert res_fraud["selected_agent"] == "Risk/Fraud Agent"
    assert res_fraud["intent"] == "FRAUD_DETECTION"

    # Case C: Loan query -> Credit/Loan Agent
    res_loan = supervisor.process_request("Calculate EMI for a $15,000 loan for 3 years", account_number="ACC-982104")
    assert res_loan["success"] is True
    assert res_loan["selected_agent"] == "Credit/Loan Agent"
    assert res_loan["intent"] == "LOAN_CREDIT"

    # Case D: FAQ query -> General Banking/FAQ Agent
    res_faq = supervisor.process_request("What are your branch opening hours?", account_number="ACC-982104")
    assert res_faq["success"] is True
    assert res_faq["selected_agent"] == "General Banking/FAQ Agent"


# -----------------------------------------------------------------------------
# Test 5: Execution Trace Completeness & Fallback Resilience
# -----------------------------------------------------------------------------
def test_execution_trace_and_fallback_resilience():
    """Verify execution trace captures step-by-step audit without failing when LLM is offline."""
    supervisor = SupervisorAgent()
    status = check_ollama_availability()
    # Confirm status check does not raise exceptions
    assert "available" in status
    assert "mode" in status

    res = supervisor.process_request("Show me my recent spending transactions", account_number="ACC-982104")
    trace = res["execution_trace"]
    assert len(trace) >= 3
    assert any(t["stage"] == "Supervisor Intent Classification" for t in trace)
    assert any(t["stage"] == "Agent Routing" for t in trace)
    assert any(t["stage"] == "Response Finalization" for t in trace)
    assert res["response_text"] is not None
    assert len(res["response_text"]) > 10
