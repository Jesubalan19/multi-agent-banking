"""
database.py - SQLite-based Simulated Core Banking Data Store (INR / Indian Banking).
Provides synthetic customer, account, and transaction records denominated in Indian Rupees (₹).
Zero external credentials or real banking APIs required.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banking_sim.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a connection to the SQLite database with Row factory enabled."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None, force_reset: bool = False) -> str:
    """
    Initialize SQLite database tables and seed with realistic synthetic Indian banking records.
    Automatically migrates legacy USD databases to INR.
    """
    path = db_path or DEFAULT_DB_PATH

    if force_reset and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass

    conn = get_connection(path)
    cursor = conn.cursor()

    # 1. Customers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            credit_score INTEGER NOT NULL,
            monthly_income REAL NOT NULL,
            home_country TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_number TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            status TEXT DEFAULT 'ACTIVE',
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        )
    """)

    # 3. Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            txn_id TEXT PRIMARY KEY,
            account_number TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            is_flagged INTEGER DEFAULT 0,
            flag_reason TEXT,
            FOREIGN KEY (account_number) REFERENCES accounts (account_number)
        )
    """)

    conn.commit()

    # Detect legacy USD data or empty database to perform safe migration/reseed
    cursor.execute("SELECT COUNT(*) FROM customers")
    cust_count = cursor.fetchone()[0]

    needs_reseed = cust_count == 0
    if not needs_reseed:
        cursor.execute("SELECT currency FROM accounts LIMIT 1")
        row = cursor.fetchone()
        if row and row["currency"] != "INR":
            needs_reseed = True

    if needs_reseed or force_reset:
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM accounts")
        cursor.execute("DELETE FROM customers")
        _seed_synthetic_inr_data(cursor)
        conn.commit()

    conn.close()
    return path


def _seed_synthetic_inr_data(cursor: sqlite3.Cursor):
    """Populate realistic synthetic Indian customers, accounts, and transactions in INR (₹)."""
    now = datetime.now()

    # Seed Indian Customers
    customers = [
        (
            "CUST101",
            "Aarav Sharma",
            "aarav.sharma@syntheticbank.in",
            "+91-98201-92831",
            765,
            85000.0,  # ₹85,000 / month
            "India",
        ),
        (
            "CUST102",
            "Priya Patel",
            "priya.patel@syntheticbank.in",
            "+91-98765-43210",
            640,
            45000.0,  # ₹45,000 / month
            "India",
        ),
        (
            "CUST103",
            "Vikram Malhotra",
            "vikram.malhotra@syntheticbank.in",
            "+91-99887-76655",
            790,
            210000.0,  # ₹2,10,000 / month
            "India",
        ),
    ]
    cursor.executemany(
        """
        INSERT INTO customers (customer_id, name, email, phone, credit_score, monthly_income, home_country)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        customers,
    )

    # Seed Accounts (in INR)
    accounts = [
        ("ACC-982104", "CUST101", "Savings Account", 485250.00, "INR", "ACTIVE"),  # ₹4,85,250.00
        ("ACC-441209", "CUST102", "Salary Account", 92400.00, "INR", "ACTIVE"),    # ₹92,400.00
        ("ACC-110943", "CUST103", "Wealth Privilege", 1850000.00, "INR", "ACTIVE"), # ₹18,50,000.00 (₹18.5 Lakhs)
    ]
    cursor.executemany(
        """
        INSERT INTO accounts (account_number, customer_id, account_type, balance, currency, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        accounts,
    )

    # Relative timestamp helper
    def fmt_time(hours_ago: int) -> str:
        return (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")

    # Seed Transactions in INR (Normal daily expenses & deliberate explainable suspicious patterns)
    transactions = [
        # Customer 1 (Aarav Sharma: ACC-982104, Balance: ₹4,85,250)
        (
            "TXN-1001",
            "ACC-982104",
            fmt_time(2),
            "Swiggy Food Delivery",
            640.00,
            "Dining",
            "Mumbai, India",
            0,
            None,
        ),
        (
            "TXN-1002",
            "ACC-982104",
            fmt_time(6),
            "Reliance Smart Bazaar",
            3450.00,
            "Groceries",
            "Mumbai, India",
            0,
            None,
        ),
        (
            "TXN-1003",
            "ACC-982104",
            fmt_time(15),
            "Indian Oil Fuel Station",
            2100.00,
            "Fuel & Transportation",
            "Navi Mumbai, India",
            0,
            None,
        ),
        (
            "TXN-1004",
            "ACC-982104",
            fmt_time(22),
            "Apex Global Offshore Capital",
            350000.00,
            "International Wire",
            "Kyiv, Ukraine",
            1,
            "High-value overseas wire transfer of ₹3,50,000.00 exceeding baseline threshold and country discrepancy.",
        ),
        (
            "TXN-1005",
            "ACC-982104",
            fmt_time(38),
            "Euronet Lisbon ATM",
            45000.00,
            "Cash Withdrawal",
            "Lisbon, Portugal",
            1,
            "Foreign ATM withdrawal of ₹45,000.00 detected outside registered country (India).",
        ),
        (
            "TXN-1006",
            "ACC-982104",
            fmt_time(52),
            "Netflix India Subscription",
            649.00,
            "Entertainment",
            "Online, India",
            0,
            None,
        ),
        # Customer 2 (Priya Patel: ACC-441209, Balance: ₹92,400)
        (
            "TXN-2001",
            "ACC-441209",
            fmt_time(1),
            "DMart Supermarket",
            2850.00,
            "Groceries",
            "Bengaluru, India",
            0,
            None,
        ),
        (
            "TXN-2002",
            "ACC-441209",
            fmt_time(5),
            "Apollo Pharmacy",
            680.00,
            "Healthcare",
            "Bengaluru, India",
            0,
            None,
        ),
        (
            "TXN-2003",
            "ACC-441209",
            fmt_time(11),
            "Tokyo Ginza Gadgets",
            78000.00,
            "Electronics",
            "Tokyo, Japan",
            1,
            "Transaction amount (₹78,000.00) consumes >70% of total balance with foreign IP/location.",
        ),
        (
            "TXN-2004",
            "ACC-441209",
            fmt_time(29),
            "Namma Metro Smart Card",
            500.00,
            "Transit",
            "Bengaluru, India",
            0,
            None,
        ),
        # Customer 3 (Vikram Malhotra: ACC-110943, Balance: ₹18,50,000)
        (
            "TXN-3001",
            "ACC-110943",
            fmt_time(4),
            "Taj Lands End Mumbai",
            8500.00,
            "Dining & Hospitality",
            "Mumbai, India",
            0,
            None,
        ),
        (
            "TXN-3002",
            "ACC-110943",
            fmt_time(14),
            "MakeMyTrip Air Ticket",
            24500.00,
            "Travel",
            "New Delhi, India",
            0,
            None,
        ),
        (
            "TXN-3003",
            "ACC-110943",
            fmt_time(24),
            "Tanishq Jewellery",
            65000.00,
            "Shopping",
            "Mumbai, India",
            0,
            None,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO transactions (txn_id, account_number, timestamp, merchant, amount, category, location, is_flagged, flag_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        transactions,
    )


def get_all_customers(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch list of all customers."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY customer_id ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_customer_by_id(customer_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve single customer record by customer_id."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_account_by_number(account_number: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve account details along with customer information."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.account_number, a.customer_id, a.account_type, a.balance, a.currency, a.status,
               c.name as customer_name, c.email, c.credit_score, c.monthly_income, c.home_country
        FROM accounts a
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE a.account_number = ?
    """, (account_number,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_customer_accounts(customer_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all accounts belonging to a given customer."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE customer_id = ?", (customer_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_transactions(account_number: Optional[str] = None, limit: int = 15, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch transactions, optionally filtered by account_number."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if account_number:
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE account_number = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (account_number, limit))
    else:
        cursor.execute("""
            SELECT * FROM transactions 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def flag_transaction(txn_id: str, reason: str, db_path: Optional[str] = None) -> bool:
    """Flag a transaction for suspicious activity."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE transactions 
        SET is_flagged = 1, flag_reason = ? 
        WHERE txn_id = ?
    """, (reason, txn_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_flagged_transactions(account_number: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve flagged transactions."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if account_number:
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE account_number = ? AND is_flagged = 1
            ORDER BY timestamp DESC
        """, (account_number,))
    else:
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE is_flagged = 1 
            ORDER BY timestamp DESC
        """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    db_file = init_db(force_reset=True)
    print(f"Database successfully re-initialized with INR records at: {db_file}")
    customers = get_all_customers()
    print(f"Loaded {len(customers)} synthetic Indian customers.")
