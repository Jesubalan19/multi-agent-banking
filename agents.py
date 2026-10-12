"""
agents.py - Multi-Agent Architecture for Real-Time Indian Banking Simulation (INR / ₹).
Implements:
1. Supervisor/Orchestrator Agent (Routing & Execution Trace)
2. Banking/Customer Agent (INR Balances & Transaction History)
3. Risk/Fraud Agent (Explainable Indian Banking Surveillance & Location Anomaly Rules)
4. Credit/Loan Agent (Reducing-Balance EMI Math & DTI Underwriting Simulation in INR)
5. General FAQ Agent (Indian Retail Banking Knowledge: IFSC, DICGC, UPI)

Supports local LLM (Ollama Qwen 2.5 3B) when online, and automatically
falls back to deterministic AI with full INR functionality and zero downtime.
"""

import re
import socket
import datetime
from typing import Dict, Any, List, Optional, Tuple

import banking_tools
from banking_tools import format_inr, format_inr_lakh_crore
import database

# Configuration
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
PREFERRED_MODEL = "qwen2.5:3b"


def check_ollama_availability(timeout: float = 0.2) -> Dict[str, Any]:
    """
    Rapid, non-blocking check to determine if Ollama is accessible locally.
    Never hangs the UI.
    """
    is_socket_open = False
    try:
        with socket.create_connection((OLLAMA_HOST, OLLAMA_PORT), timeout=timeout):
            is_socket_open = True
    except (socket.timeout, ConnectionRefusedError, OSError):
        is_socket_open = False

    if not is_socket_open:
        return {
            "available": False,
            "model": None,
            "mode": "Deterministic Fallback",
            "message": "Ollama local service is offline or not installed. Running on 100% Deterministic AI rules."
        }

    try:
        import ollama
        models_response = ollama.list()
        model_names = []
        if isinstance(models_response, dict) and "models" in models_response:
            model_names = [m.get("name", "") for m in models_response["models"]]
        elif hasattr(models_response, "models"):
            model_names = [getattr(m, "model", getattr(m, "name", "")) for m in models_response.models]

        selected_model = PREFERRED_MODEL if any(PREFERRED_MODEL in name for name in model_names) else (model_names[0] if model_names else None)

        if selected_model:
            return {
                "available": True,
                "model": selected_model,
                "mode": "Local LLM Active",
                "message": f"Connected to Ollama ({selected_model}). AI phrasing in INR active."
            }
        else:
            return {
                "available": False,
                "model": None,
                "mode": "Deterministic Fallback",
                "message": "Ollama is running, but no models found. Running on Deterministic AI rules."
            }
    except Exception as e:
        return {
            "available": False,
            "model": None,
            "mode": "Deterministic Fallback",
            "message": f"Ollama connection error: {str(e)}. Running on Deterministic AI rules."
        }


def _call_ollama(prompt: str, system_prompt: str, model_name: str) -> Optional[str]:
    """Helper to query local Ollama model safely with error handling."""
    try:
        import ollama
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.2}
        )
        if isinstance(response, dict) and "message" in response:
            return response["message"]["content"]
        elif hasattr(response, "message") and hasattr(response.message, "content"):
            return response.message.content
        return None
    except Exception:
        return None


# ==============================================================================
# SPECIALIZED AGENTS
# ==============================================================================

class CustomerBankingAgent:
    """Specialized Agent for customer balance and transaction inquiries in INR."""
    name = "Banking/Customer Agent"
    description = "Handles account balance checks, customer verification, and transaction history in INR."

    def execute(self, query: str, account_number: str, customer_info: Dict[str, Any], llm_status: Dict[str, Any]) -> Dict[str, Any]:
        trace_steps = []
        trace_steps.append(f"Customer Agent activated for account {account_number}.")

        q_lower = query.lower()
        is_transaction_query = any(k in q_lower for k in [
            "transaction", "history", "statement", "activity", "spent", "purchases", "passbook", "upi"
        ])

        if is_transaction_query:
            trace_steps.append("Invoking banking_tools.get_transaction_history(limit=5) in INR.")
            tool_res = banking_tools.get_transaction_history(account_number, limit=5)

            if llm_status["available"] and llm_status["model"]:
                system_prompt = (
                    "You are a professional banking assistant for an Indian retail bank. "
                    "Summarize the customer's recent transactions politely and concisely. "
                    "Always use Indian Rupees (₹) with Indian number formatting (e.g. ₹1,25,000.00). "
                    "Never use USD or $ symbol."
                )
                prompt = f"Customer Name: {customer_info['name']}\nTransactions: {tool_res['transactions']}\nOriginal Query: {query}"
                llm_narrative = _call_ollama(prompt, system_prompt, llm_status["model"])
                response_text = llm_narrative or self._deterministic_tx_summary(customer_info, tool_res)
            else:
                response_text = self._deterministic_tx_summary(customer_info, tool_res)

            return {
                "agent": self.name,
                "action": "transaction_history",
                "currency": "INR",
                "tool_data": tool_res,
                "response_text": response_text,
                "trace_steps": trace_steps,
            }
        else:
            trace_steps.append("Invoking banking_tools.check_balance() in INR.")
            tool_res = banking_tools.check_balance(account_number)

            if llm_status["available"] and llm_status["model"]:
                system_prompt = (
                    "You are a professional banking assistant for an Indian retail bank. "
                    "State the customer's balance and status politely. "
                    "Always display amounts in Indian Rupees (₹) with Indian number formatting (e.g., ₹4,85,250.00). "
                    "Never use USD or $ symbol."
                )
                prompt = f"Customer: {customer_info['name']}\nAccount: {tool_res}\nQuery: {query}"
                llm_narrative = _call_ollama(prompt, system_prompt, llm_status["model"])
                response_text = llm_narrative or self._deterministic_balance_summary(customer_info, tool_res)
            else:
                response_text = self._deterministic_balance_summary(customer_info, tool_res)

            return {
                "agent": self.name,
                "action": "balance_check",
                "currency": "INR",
                "tool_data": tool_res,
                "response_text": response_text,
                "trace_steps": trace_steps,
            }

    def _deterministic_balance_summary(self, customer: Dict[str, Any], data: Dict[str, Any]) -> str:
        words = data.get("formatted_balance_words", "")
        desc = f" ({words})" if words else ""
        return (
            f"Hello {customer['name']}, your current balance for {data['account_type']} "
            f"({data['account_number']}) is **{data['formatted_balance']}**{desc}. "
            f"Your account status is currently **{data['status']}**."
        )

    def _deterministic_tx_summary(self, customer: Dict[str, Any], data: Dict[str, Any]) -> str:
        count = data["count"]
        lines = [f"Here are the recent {count} transactions for account {data['account_number']} (in INR):"]
        for idx, t in enumerate(data["transactions"], 1):
            flag_marker = " ⚠️ [FLAGGED]" if t["is_flagged"] else ""
            lines.append(
                f"{idx}. **{t['timestamp'][:10]}**: {t['formatted_amount']} at *{t['merchant']}* ({t['category']}) "
                f"in {t['location']}{flag_marker}"
            )
        return "\n".join(lines)


class RiskFraudAgent:
    """Specialized Agent for transaction surveillance, pattern detection, and explainable fraud rules in INR."""
    name = "Risk/Fraud Agent"
    description = "Inspects transactions against explainable security rules in INR to safeguard Indian accounts."

    def execute(self, query: str, account_number: str, customer_info: Dict[str, Any], llm_status: Dict[str, Any]) -> Dict[str, Any]:
        trace_steps = []
        trace_steps.append(f"Risk/Fraud Agent initialized surveillance for account {account_number}.")
        trace_steps.append("Invoking banking_tools.inspect_transactions_for_fraud() with INR rule sets.")

        tool_res = banking_tools.inspect_transactions_for_fraud(account_number)
        flagged_count = tool_res["flagged_count"]
        trace_steps.append(f"Evaluated {tool_res['total_evaluated']} transactions. Flagged: {flagged_count}.")

        if llm_status["available"] and llm_status["model"]:
            system_prompt = (
                "You are an AI Bank Security Officer for an Indian bank. Explain the security evaluation clearly. "
                "Always express currency in Indian Rupees (₹) with Indian digit formatting (e.g. ₹3,50,000.00). "
                "Never use $ or USD. Explain each triggered rule exactly as reported by the tools."
            )
            prompt = f"Customer: {customer_info['name']}\nEvaluation Data: {tool_res}\nQuery: {query}"
            llm_narrative = _call_ollama(prompt, system_prompt, llm_status["model"])
            response_text = llm_narrative or self._deterministic_fraud_report(customer_info, tool_res)
        else:
            response_text = self._deterministic_fraud_report(customer_info, tool_res)

        return {
            "agent": self.name,
            "action": "fraud_inspection",
            "currency": "INR",
            "tool_data": tool_res,
            "response_text": response_text,
            "trace_steps": trace_steps,
        }

    def _deterministic_fraud_report(self, customer: Dict[str, Any], data: Dict[str, Any]) -> str:
        if data["flagged_count"] == 0:
            return (
                f"🛡️ **Security Audit Complete**: All {data['total_evaluated']} recent transactions "
                f"for account {data['account_number']} conform to your typical spending patterns. "
                f"No suspicious spikes or geo-velocity anomalies outside India detected."
            )

        report = [
            f"⚠️ **Security Alert**: The Risk Engine flagged **{data['flagged_count']} suspicious transaction(s)** "
            f"out of {data['total_evaluated']} evaluated for {customer['name']} ({data['account_number']}):\n"
        ]
        for item in data["flagged_transactions"]:
            report.append(
                f"- **{item['merchant']}** | **{item['formatted_amount']}** | Risk Level: **{item['risk_level']}** (Score: {item['risk_score']}/100)\n"
                f"  - *Location*: {item['location']} | *Date*: {item['timestamp']}\n"
                f"  - *Reason*: {item['explanation']}"
            )
        report.append("\n💡 *Action Recommended*: Review these transactions immediately. You can freeze your debit card or lock UPI access.")
        return "\n".join(report)


class CreditLoanAgent:
    """Specialized Agent for calculating reducing-balance loan EMIs and underwriting in INR."""
    name = "Credit/Loan Agent"
    description = "Calculates monthly EMI in INR and evaluates simulated credit eligibility using FOIR/DTI ratios."

    def execute(self, query: str, account_number: str, customer_info: Dict[str, Any], llm_status: Dict[str, Any]) -> Dict[str, Any]:
        trace_steps = []
        trace_steps.append(f"Credit/Loan Agent activated for customer {customer_info['name']}.")

        principal, interest_rate, tenure_months = self._parse_loan_parameters(query)
        trace_steps.append(
            f"Extracted loan parameters: Principal={format_inr(principal)}, Interest={interest_rate}%, Tenure={tenure_months}mo."
        )

        emi_data = banking_tools.calculate_loan_emi(principal, interest_rate, tenure_months)
        trace_steps.append(f"Calculated reducing-balance EMI: {emi_data['formatted_emi']}/month.")

        is_eligibility_query = any(k in query.lower() for k in [
            "eligible", "eligibility", "qualify", "can i get", "apply", "approved", "cibil"
        ])
        eligibility_data = None

        if is_eligibility_query or "loan" in query.lower():
            trace_steps.append("Executing simulated underwriting check: banking_tools.evaluate_loan_eligibility().")
            eligibility_data = banking_tools.evaluate_loan_eligibility(
                monthly_income=customer_info["monthly_income"],
                credit_score=customer_info["credit_score"],
                requested_loan_amount=principal,
                tenure_months=tenure_months,
                annual_interest_rate=interest_rate
            )
            trace_steps.append(f"Simulated eligibility decision: {eligibility_data['status']} (FOIR/DTI: {eligibility_data['dti_ratio']}%).")

        tool_data = {
            "emi_calculation": emi_data,
            "eligibility": eligibility_data,
            "customer_profile": {
                "credit_score": customer_info["credit_score"],
                "monthly_income": customer_info["monthly_income"]
            }
        }

        if llm_status["available"] and llm_status["model"]:
            system_prompt = (
                "You are an AI Banking Loan Officer in India. Present the EMI calculation and simulated eligibility assessment clearly. "
                "Always express currency in Indian Rupees (₹) with Indian digit formatting (e.g. ₹15,000.00, ₹5,00,000.00). "
                "Never use USD or $. Never alter calculated numbers returned by the tools. "
                "Clearly label the result as a simulation."
            )
            prompt = f"Customer Profile: {customer_info}\nLoan & Eligibility Data: {tool_data}\nQuery: {query}"
            llm_narrative = _call_ollama(prompt, system_prompt, llm_status["model"])
            response_text = llm_narrative or self._deterministic_loan_summary(customer_info, tool_data)
        else:
            response_text = self._deterministic_loan_summary(customer_info, tool_data)

        return {
            "agent": self.name,
            "action": "loan_analysis",
            "currency": "INR",
            "tool_data": tool_data,
            "response_text": response_text,
            "trace_steps": trace_steps,
        }

    def _parse_loan_parameters(self, query: str) -> Tuple[float, float, int]:
        """Extract principal amount in INR, interest rate, and tenure from natural language string."""
        q = query.lower()

        # Default principal in INR: ₹5,00,000 (5 Lakhs)
        principal = 500000.0

        # 1. Match Indian Crore notation (e.g., "1 crore", "1.5 cr", "2 crores")
        cr_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)', q)
        if cr_match:
            principal = float(cr_match.group(1)) * 10000000.0
        else:
            # 2. Match Indian Lakh notation (e.g., "5 lakh", "5.5 lakhs", "10 lac", "2 lacs")
            lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs)', q)
            if lakh_match:
                principal = float(lakh_match.group(1)) * 100000.0
            else:
                # 3. Match explicit rupee amounts (₹1,50,000 or 500000 or 50k)
                amt_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})+|\d+)(?:\s*(?:k|thousand))?', q)
                if amt_match:
                    raw_val = amt_match.group(1).replace(",", "")
                    try:
                        val = float(raw_val)
                        if "k" in amt_match.group(0).lower() or "thousand" in amt_match.group(0).lower():
                            val *= 1000.0
                        if val >= 5000.0:  # Reasonable minimum loan threshold
                            principal = val
                    except ValueError:
                        pass

        # Parse Tenure (years or months)
        tenure = 36  # Default 36 months (3 years)
        yr_match = re.search(r'(\d+)\s*(?:year|yr|years)', q)
        mo_match = re.search(r'(\d+)\s*(?:month|mo|months)', q)
        if yr_match:
            tenure = int(yr_match.group(1)) * 12
        elif mo_match:
            tenure = int(mo_match.group(1))

        # Parse Interest Rate (e.g., 9.5%, 8.5 percent)
        interest = 10.0  # Default 10.0%
        rate_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent)', q)
        if rate_match:
            interest = float(rate_match.group(1))

        return principal, interest, tenure

    def _deterministic_loan_summary(self, customer: Dict[str, Any], data: Dict[str, Any]) -> str:
        emi_info = data["emi_calculation"]
        elig = data.get("eligibility")

        lines = [
            f"📊 **Loan & Reducing-Balance EMI Summary (INR)**:\n",
            f"- **Principal Amount**: {emi_info['formatted_principal']} ({format_inr_lakh_crore(emi_info['principal'])})",
            f"- **Annual Interest Rate**: {emi_info['annual_interest_rate']}% p.a.",
            f"- **Tenure**: {emi_info['tenure_months']} months ({emi_info['tenure_months'] // 12} years)",
            f"- **Monthly EMI**: **{emi_info['formatted_emi']}**",
            f"- **Total Interest Payable**: {emi_info['formatted_total_interest']}",
            f"- **Total Repayment Amount**: {emi_info['formatted_total_payment']}\n"
        ]

        if elig:
            badge = "✅" if elig["status"] == "APPROVED" else ("⚠️" if elig["status"] == "CONDITIONALLY APPROVED" else "❌")
            lines.append(f"🏦 **Simulated Underwriting Assessment**: {badge} **{elig['status']}** *(Simulation)*")
            lines.append(f"- **Customer CIBIL / Credit Score**: {customer['credit_score']}")
            lines.append(f"- **Verified Monthly Income**: {format_inr(customer['monthly_income'])}")
            lines.append(f"- **Projected FOIR / DTI**: {elig['dti_ratio']}% (Policy ceiling <= 45%)")
            for r in elig["reasons"]:
                lines.append(f"  • {r}")

        return "\n".join(lines)


class GeneralFaqAgent:
    """Specialized Agent for general retail banking information in India (IFSC, DICGC, UPI)."""
    name = "General Banking/FAQ Agent"
    description = "Provides retail banking guidance on operational hours, IFSC codes, DICGC insurance, and UPI security."

    def execute(self, query: str, account_number: str, customer_info: Dict[str, Any], llm_status: Dict[str, Any]) -> Dict[str, Any]:
        trace_steps = [
            "General FAQ Agent activated for retail banking guidance in India.",
            "Invoking banking_tools.get_general_banking_faq()."
        ]
        tool_res = banking_tools.get_general_banking_faq(query)

        if llm_status["available"] and llm_status["model"]:
            system_prompt = (
                "You are a friendly Indian retail banking support assistant. Answer the user's question clearly. "
                "Always use Indian Rupees (₹) where monetary amounts apply."
            )
            prompt = f"Knowledge: {tool_res['answer']}\nUser Query: {query}"
            response_text = _call_ollama(prompt, system_prompt, llm_status["model"]) or tool_res["answer"]
        else:
            response_text = tool_res["answer"]

        return {
            "agent": self.name,
            "action": "faq_guidance",
            "currency": "INR",
            "tool_data": tool_res,
            "response_text": response_text,
            "trace_steps": trace_steps,
        }


# ==============================================================================
# SUPERVISOR / ORCHESTRATOR AGENT
# ==============================================================================

class SupervisorAgent:
    """
    Supervisor / Orchestrator Agent.
    - Analyzes incoming user requests in real time.
    - Classifies intent using local LLM (or robust deterministic NLP rule engine if offline).
    - Routes requests to specialized agents:
        - CustomerBankingAgent
        - RiskFraudAgent
        - CreditLoanAgent
        - GeneralFaqAgent
    - Captures an end-to-end Execution Trace for full explainability.
    """

    def __init__(self):
        self.banking_agent = CustomerBankingAgent()
        self.fraud_agent = RiskFraudAgent()
        self.loan_agent = CreditLoanAgent()
        self.faq_agent = GeneralFaqAgent()

    def classify_intent(self, query: str, llm_status: Dict[str, Any]) -> Tuple[str, str, float]:
        """
        Classify query intent with Indian banking vocabulary support.
        Returns: (intent_category, rationale, confidence)
        Categories: FRAUD_DETECTION, LOAN_CREDIT, CUSTOMER_BANKING, GENERAL_FAQ
        """
        q = query.lower()

        fraud_keywords = [
            "fraud", "suspicious", "flag", "unusual", "stolen", "hack", "scam", "audit", "alert",
            "weird", "compromised", "risk", "anomaly", "unauthorized", "foreign"
        ]
        loan_keywords = [
            "loan", "emi", "borrow", "interest", "eligible", "eligibility", "mortgage", "repay",
            "installment", "underwrite", "credit score", "cibil", "lakh", "lakhs", "crore", "crores"
        ]
        banking_keywords = [
            "balance", "funds", "how much money", "account", "transaction", "history", "statement",
            "spent", "passbook", "deposit", "recent", "rupees", "inr"
        ]
        faq_keywords = [
            "hour", "open", "close", "ifsc", "micr", "routing", "swift", "neft", "rtgs", "upi",
            "dicgc", "fdic", "insure", "branch", "help", "hello", "hi", "hey", "contact"
        ]

        if any(w in q for w in fraud_keywords):
            return "FRAUD_DETECTION", "Keywords matched security, fraud detection, or suspicious activity.", 0.95
        if any(w in q for w in loan_keywords):
            return "LOAN_CREDIT", "Keywords matched loan underwriting, interest, or EMI calculation.", 0.95
        if any(w in q for w in banking_keywords):
            return "CUSTOMER_BANKING", "Keywords matched account balance or transaction history inquiry.", 0.92
        if any(w in q for w in faq_keywords):
            return "GENERAL_FAQ", "Keywords matched general retail banking guidance or FAQs.", 0.88

        if llm_status["available"] and llm_status["model"]:
            system_prompt = (
                "You are an intent routing classifier for a banking multi-agent system. "
                "Classify the input into exactly one of: FRAUD_DETECTION, LOAN_CREDIT, CUSTOMER_BANKING, GENERAL_FAQ. "
                "Reply with only the category name."
            )
            raw = _call_ollama(query, system_prompt, llm_status["model"])
            if raw:
                for cat in ["FRAUD_DETECTION", "LOAN_CREDIT", "CUSTOMER_BANKING", "GENERAL_FAQ"]:
                    if cat in raw.upper():
                        return cat, f"Classified by local LLM ({llm_status['model']}).", 0.90

        return "CUSTOMER_BANKING", "Defaulted to customer account agent for general banking query.", 0.70

    def process_request(
        self,
        query: str,
        account_number: str = "ACC-982104"
    ) -> Dict[str, Any]:
        """
        Orchestrate the full multi-agent workflow:
        1. Query analysis & intent classification
        2. Agent selection
        3. Specialized agent execution
        4. Assembly of trace and structured response in INR
        """
        start_time = datetime.datetime.now()
        llm_status = check_ollama_availability()

        account_info = database.get_account_by_number(account_number)
        if not account_info:
            return {
                "success": False,
                "error": f"Account {account_number} not found.",
                "execution_trace": []
            }

        customer_info = {
            "name": account_info["customer_name"],
            "account_number": account_number,
            "monthly_income": account_info["monthly_income"],
            "credit_score": account_info["credit_score"],
            "home_country": account_info["home_country"],
            "balance": account_info["balance"],
        }

        # Step 1: Supervisor Intent Classification
        intent, rationale, confidence = self.classify_intent(query, llm_status)

        execution_trace = [
            {
                "step": 1,
                "stage": "Supervisor Intent Classification",
                "detail": f"Classified intent as '{intent}' with {confidence*100:.0f}% confidence. Rationale: {rationale}"
            }
        ]

        # Step 2: Route to Specialized Agent
        if intent == "FRAUD_DETECTION":
            selected_agent_name = self.fraud_agent.name
            execution_trace.append({
                "step": 2,
                "stage": "Agent Routing",
                "detail": f"Supervisor routed request to {selected_agent_name}."
            })
            agent_output = self.fraud_agent.execute(query, account_number, customer_info, llm_status)

        elif intent == "LOAN_CREDIT":
            selected_agent_name = self.loan_agent.name
            execution_trace.append({
                "step": 2,
                "stage": "Agent Routing",
                "detail": f"Supervisor routed request to {selected_agent_name}."
            })
            agent_output = self.loan_agent.execute(query, account_number, customer_info, llm_status)

        elif intent == "GENERAL_FAQ":
            selected_agent_name = self.faq_agent.name
            execution_trace.append({
                "step": 2,
                "stage": "Agent Routing",
                "detail": f"Supervisor routed request to {selected_agent_name}."
            })
            agent_output = self.faq_agent.execute(query, account_number, customer_info, llm_status)

        else:  # CUSTOMER_BANKING
            selected_agent_name = self.banking_agent.name
            execution_trace.append({
                "step": 2,
                "stage": "Agent Routing",
                "detail": f"Supervisor routed request to {selected_agent_name}."
            })
            agent_output = self.banking_agent.execute(query, account_number, customer_info, llm_status)

        # Step 3: Record Agent's Sub-steps
        for idx, sub_step in enumerate(agent_output.get("trace_steps", []), start=3):
            execution_trace.append({
                "step": idx,
                "stage": "Tool & Logic Execution",
                "detail": sub_step
            })

        duration_ms = round((datetime.datetime.now() - start_time).total_seconds() * 1000, 2)
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "stage": "Response Finalization",
            "detail": f"Response completed in {duration_ms}ms using {llm_status['mode']} (INR / ₹)."
        })

        return {
            "success": True,
            "query": query,
            "account_number": account_number,
            "customer_name": customer_info["name"],
            "currency": "INR",
            "currency_symbol": "₹",
            "intent": intent,
            "selected_agent": selected_agent_name,
            "confidence": confidence,
            "llm_status": llm_status,
            "response_text": agent_output["response_text"],
            "tool_data": agent_output.get("tool_data"),
            "action": agent_output.get("action"),
            "execution_trace": execution_trace,
            "duration_ms": duration_ms
        }
