"""
app.py - Multi-Agent Simulated Real-Time Banking Dashboard.
Streamlit application integrating:
- Supervisor / Orchestrator Agent
- Banking / Customer Agent
- Risk / Fraud Agent (Explainable Detection Rules)
- Credit / Loan Agent (EMI & Underwriting)
- SQLite Core Banking Database
- Ollama local model integration with transparent Deterministic Fallback
"""

import streamlit as st
import pandas as pd
import datetime

import database
from agents import SupervisorAgent, check_ollama_availability
import banking_tools

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Banking Architecture",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished financial dashboard
st.markdown("""
<style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .agent-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.82rem;
        margin-right: 6px;
    }
    .agent-supervisor { background-color: #e0e7ff; color: #3730a3; }
    .agent-banking { background-color: #dbeafe; color: #1e40af; }
    .agent-fraud { background-color: #fee2e2; color: #991b1b; }
    .agent-loan { background-color: #fef3c7; color: #92400e; }
    .agent-faq { background-color: #f3e8ff; color: #6b21a8; }
</style>
""", unsafe_allow_html=True)


# Initialize Database
@st.cache_resource
def get_db():
    return database.init_db()

get_db()

# Initialize Supervisor Agent
if "supervisor" not in st.session_state:
    st.session_state.supervisor = SupervisorAgent()

# Initialize Chat & Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Check Ollama AI Engine Status
llm_status = check_ollama_availability()

# ==============================================================================
# SIDEBAR CONTROLS
# ==============================================================================
with st.sidebar:
    st.title("🏦 Synthetic Core Banking")
    st.caption("Wrench Wise EduTech AI/ML Internship MVP")
    st.divider()

    # 1. AI Engine Status Badge
    st.subheader("🤖 AI Engine Status")
    if llm_status["available"]:
        st.success(f"**Local LLM Active**\nModel: `{llm_status['model']}`")
        st.caption("Ollama local service is connected and phrasing responses.")
    else:
        st.info("**Deterministic Fallback Active**")
        st.caption(
            "Ollama is offline or not installed. The system is running in **100% Deterministic AI mode**, "
            "providing accurate factual banking calculations and explainable fraud rules with zero downtime."
        )

    st.divider()

    # 2. Customer Profile Switcher
    st.subheader("👤 Active Customer")
    customers = database.get_all_customers()
    cust_options = {c["customer_id"]: f"{c['name']} ({c['customer_id']})" for c in customers}
    
    selected_cust_id = st.selectbox(
        "Switch Customer Account:",
        options=list(cust_options.keys()),
        format_func=lambda x: cust_options[x],
        index=0
    )

    # Fetch active customer accounts
    cust_accounts = database.get_customer_accounts(selected_cust_id)
    if cust_accounts:
        active_account = cust_accounts[0]
        active_account_num = active_account["account_number"]
    else:
        active_account = None
        active_account_num = "ACC-982104"

    current_customer = database.get_customer_by_id(selected_cust_id)
    
    st.divider()
    
    # 3. Database Reset Button
    if st.button("🔄 Reset Simulated Database", use_container_width=True):
        database.init_db(force_reset=True)
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("### 🏛️ Agent Architecture")
    st.markdown("""
    - **Supervisor Agent**: Intent analysis & routing.
    - **Banking/Customer Agent**: Balances & statements.
    - **Risk/Fraud Agent**: Explainable rule-based surveillance.
    - **Credit/Loan Agent**: EMI math & DTI underwriting.
    - **General FAQ Agent**: Retail policies & hours.
    """)

# ==============================================================================
# MAIN DASHBOARD CONTENT
# ==============================================================================

# Header & Customer Overview Cards
st.header(f"Welcome, {current_customer['name']}")
st.caption(f"Registered Country: {current_customer['home_country']} | Customer ID: {current_customer['customer_id']} | Email: {current_customer['email']}")

# KPI Metrics Bar
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        label=f"Account Balance ({active_account['account_type']})",
        value=f"${active_account['balance']:,.2f}",
        delta=f"Status: {active_account['status']}"
    )
with col2:
    st.metric(
        label="Monthly Income",
        value=f"${current_customer['monthly_income']:,.2f}",
        delta="Verified Salary"
    )
with col3:
    score = current_customer['credit_score']
    rating = "Prime" if score >= 720 else ("Fair" if score >= 620 else "High Risk")
    st.metric(
        label="Credit Score",
        value=f"{score}",
        delta=f"Tier: {rating}"
    )
with col4:
    # Check current flagged items
    flagged = database.get_flagged_transactions(active_account_num)
    flagged_count = len(flagged)
    delta_color = "inverse" if flagged_count > 0 else "normal"
    st.metric(
        label="Security Flagged Alerts",
        value=f"{flagged_count} Alert(s)" if flagged_count else "0 Clean",
        delta="Action Needed" if flagged_count > 0 else "Safe",
        delta_color=delta_color
    )

st.divider()

# Primary Navigation Tabs
tab_chat, tab_txns, tab_loan = st.tabs([
    "💬 Multi-Agent AI Assistant",
    "🛡️ Risk & Fraud Surveillance",
    "🧮 Interactive Loan & EMI Calculator"
])

# ------------------------------------------------------------------------------
# TAB 1: MULTI-AGENT CHAT & EXECUTION TRACE
# ------------------------------------------------------------------------------
with tab_chat:
    st.subheader("Natural Language Banking Assistant")
    st.markdown("Type any natural language request or use one of the quick actions below to trigger the multi-agent pipeline.")

    # Quick Action Buttons
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    quick_query = None
    with q_col1:
        if st.button("💰 Check Balance", use_container_width=True):
            quick_query = "What is my current account balance and status?"
    with q_col2:
        if st.button("📜 Recent Transactions", use_container_width=True):
            quick_query = "Show my recent transactions history."
    with q_col3:
        if st.button("🚨 Audit For Fraud", use_container_width=True):
            quick_query = "Check my account for any suspicious transactions or fraud flags."
    with q_col4:
        if st.button("📊 Loan Eligibility", use_container_width=True):
            quick_query = "Can I qualify for a $15,000 personal loan for 3 years at 9%?"

    # Render previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "trace" in msg and msg["trace"]:
                agent_name = msg.get("selected_agent", "Agent")
                with st.expander(f"🔍 Orchestration Trace | Selected: **{agent_name}** ({msg.get('duration_ms', 0)} ms)", expanded=False):
                    st.markdown(f"**Intent**: `{msg.get('intent', 'UNKNOWN')}` | **Confidence**: `{msg.get('confidence', 1.0)*100:.0f}%`")
                    st.markdown(f"**AI Engine**: `{msg.get('llm_mode', 'Deterministic')}`")
                    st.markdown("#### Execution Steps:")
                    for step in msg["trace"]:
                        st.markdown(f"**Step {step['step']} [{step['stage']}]**: {step['detail']}")

    # Handle Input from Chat or Quick Buttons
    user_input = st.chat_input("Ask a question, e.g., 'What is my balance?', 'Audit suspicious activity', 'Calculate EMI for $20000'")
    query_to_run = quick_query or user_input

    if query_to_run:
        # Append User Message
        st.session_state.messages.append({"role": "user", "content": query_to_run})
        with st.chat_message("user"):
            st.markdown(query_to_run)

        # Process via Supervisor Agent
        with st.spinner("Supervisor Agent analyzing request and delegating..."):
            result = st.session_state.supervisor.process_request(
                query=query_to_run,
                account_number=active_account_num
            )

        # Append Assistant Response
        assistant_entry = {
            "role": "assistant",
            "content": result["response_text"],
            "selected_agent": result["selected_agent"],
            "intent": result["intent"],
            "confidence": result["confidence"],
            "trace": result["execution_trace"],
            "duration_ms": result["duration_ms"],
            "llm_mode": result["llm_status"]["mode"],
            "tool_data": result.get("tool_data")
        }
        st.session_state.messages.append(assistant_entry)

        with st.chat_message("assistant"):
            st.markdown(result["response_text"])

            # Execution Trace Expander
            with st.expander(f"🔍 Orchestration Trace | Selected: **{result['selected_agent']}** ({result['duration_ms']} ms)", expanded=True):
                st.markdown(f"**Intent Identified**: `{result['intent']}` (Confidence: `{result['confidence']*100:.0f}%`)")
                st.markdown(f"**Execution Mode**: `{result['llm_status']['mode']}`")
                st.markdown("#### Detailed Execution Steps:")
                for step in result["execution_trace"]:
                    st.markdown(f"**Step {step['step']} [{step['stage']}]**: {step['detail']}")

            # If transactions were fetched, display dataframe
            if result.get("action") == "transaction_history" and result.get("tool_data"):
                tx_list = result["tool_data"]["transactions"]
                if tx_list:
                    df = pd.DataFrame(tx_list)[["timestamp", "merchant", "amount", "category", "location", "is_flagged"]]
                    st.dataframe(df, use_container_width=True)

            # If fraud audit, show cards
            if result.get("action") == "fraud_inspection" and result.get("tool_data"):
                flagged_list = result["tool_data"]["flagged_transactions"]
                if flagged_list:
                    st.warning(f"Surveillance system detected {len(flagged_list)} suspicious item(s).")

# ------------------------------------------------------------------------------
# TAB 2: RISK & FRAUD SURVEILLANCE
# ------------------------------------------------------------------------------
with tab_txns:
    st.subheader("Real-Time Transaction Surveillance & Explainable Fraud Engine")
    st.markdown(
        "The Risk/Fraud Agent applies explainable banking security rules to detect anomalies in real-time. "
        "Every flag is accompanied by a transparent audit rationale."
    )

    t_col1, t_col2 = st.columns([1, 1])
    with t_col1:
        large_thresh = st.slider("High-Value Amount Threshold ($)", min_value=1000.0, max_value=10000.0, value=3000.0, step=500.0)
    with t_col2:
        ratio_thresh = st.slider("Balance Depletion Ratio Threshold (%)", min_value=10, max_value=90, value=50, step=5) / 100.0

    if st.button("🔎 Run Explainable Fraud Scan", use_container_width=True):
        with st.spinner("Analyzing transaction ledger against security rules..."):
            audit_res = banking_tools.inspect_transactions_for_fraud(
                account_number=active_account_num,
                large_amount_threshold=large_thresh,
                balance_ratio_threshold=ratio_thresh
            )
            
            if audit_res["flagged_count"] > 0:
                st.error(f"⚠️ {audit_res['flagged_count']} Suspicious Transaction(s) Identified out of {audit_res['total_evaluated']} evaluated!")
                for item in audit_res["flagged_transactions"]:
                    with st.container():
                        st.markdown(f"""
                        <div class="metric-card" style="border-left: 5px solid #ef4444;">
                            <h4 style="margin: 0; color: #991b1b;">⚠️ {item['merchant']} - ${item['amount']:,.2f}</h4>
                            <p style="margin: 4px 0;"><strong>Risk Level:</strong> {item['risk_level']} (Risk Score: {item['risk_score']}/100) | <strong>Location:</strong> {item['location']}</p>
                            <p style="margin: 4px 0; color: #374151;"><strong>Audit Explanation:</strong> {item['explanation']}</p>
                            <p style="margin: 2px 0; font-size: 0.85rem; color: #6b7280;">Timestamp: {item['timestamp']} | ID: {item['txn_id']}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.success("✅ Clean Record: No suspicious activity detected on this account.")

    st.subheader("Complete Account Transaction Ledger")
    all_txns = database.get_transactions(account_number=active_account_num, limit=20)
    if all_txns:
        df_all = pd.DataFrame(all_txns)
        display_cols = ["txn_id", "timestamp", "merchant", "amount", "category", "location", "is_flagged", "flag_reason"]
        st.dataframe(df_all[display_cols], use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 3: LOAN & EMI CALCULATOR
# ------------------------------------------------------------------------------
with tab_loan:
    st.subheader("Credit & Loan Underwriting Simulator")
    st.markdown(
        "Demonstrates the Credit/Loan Agent's deterministic EMI calculation formula "
        "and automated Debt-To-Income (DTI) underwriting logic."
    )

    l_col1, l_col2, l_col3 = st.columns(3)
    with l_col1:
        principal_input = st.number_input("Requested Loan Principal ($)", min_value=1000.0, max_value=200000.0, value=15000.0, step=1000.0)
    with l_col2:
        interest_input = st.slider("Annual Interest Rate (%)", min_value=3.0, max_value=24.0, value=9.5, step=0.5)
    with l_col3:
        tenure_input = st.selectbox("Tenure (Months)", options=[12, 24, 36, 48, 60, 84], index=2)

    existing_debt_input = st.number_input("Existing Monthly Debt Obligations ($)", min_value=0.0, max_value=5000.0, value=250.0, step=50.0)

    # Compute EMI and Eligibility
    emi_calc = banking_tools.calculate_loan_emi(principal_input, interest_input, tenure_input)
    eligibility_calc = banking_tools.evaluate_loan_eligibility(
        monthly_income=current_customer["monthly_income"],
        credit_score=current_customer["credit_score"],
        requested_loan_amount=principal_input,
        tenure_months=tenure_input,
        annual_interest_rate=interest_input,
        existing_monthly_debt=existing_debt_input
    )

    res_col1, res_col2, res_col3 = st.columns(3)
    with res_col1:
        st.metric("Monthly EMI", emi_calc["formatted_emi"])
    with res_col2:
        st.metric("Total Interest Payable", emi_calc["formatted_total_interest"])
    with res_col3:
        st.metric("Total Repayment Amount", emi_calc["formatted_total_payment"])

    st.markdown("### Automated Underwriting Decision")
    if eligibility_calc["status"] == "APPROVED":
        st.success(f"### ✅ {eligibility_calc['status']}")
    elif eligibility_calc["status"] == "CONDITIONALLY APPROVED":
        st.warning(f"### ⚠️ {eligibility_calc['status']}")
    else:
        st.error(f"### ❌ {eligibility_calc['status']}")

    st.write(f"- **Customer Monthly Income**: ${current_customer['monthly_income']:,.2f}")
    st.write(f"- **Credit Score**: {current_customer['credit_score']}")
    st.write(f"- **Projected Debt-To-Income (DTI)**: **{eligibility_calc['dti_ratio']}%** (Standard policy cap: 45%)")
    st.write(f"- **Maximum Allowable Monthly EMI**: ${eligibility_calc['max_affordable_emi']:,.2f}")
    
    st.markdown("#### Underwriting Rationale:")
    for r in eligibility_calc["reasons"]:
        st.markdown(f"- {r}")

st.markdown("---")
st.caption("Simulated Real-Time Banking System | Synthetic Data Only | Designed for Wrench Wise EduTech AI/ML Internship")
