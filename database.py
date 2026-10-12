"""
database.py - SQLite-based Simulated Core Banking Data Store.
Provides synthetic customer, account, and transaction records for the banking simulation.
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
    Initialize SQLite database tables and seed with realistic synthetic banking records.
    Safe to call multiple times (idempotent unless force_reset is True).
    """
    path = db_path or DEFAULT_DB_PATH
    
    if force_reset and os.path.exists(path):
        os.remove(path)

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
            currency TEXT DEFAULT 'USD',
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

    # Check if seed data exists
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        _seed_synthetic_data(cursor)
        conn.commit()

    conn.close()
    return path


def _seed_synthetic_data(cursor: sqlite3.Cursor):
    """Populate realistic synthetic customers, accounts, and transactions."""
    now = datetime.now()

    # Seed Customers
    customers = [
        (
            "CUST101",
            "Alex Rivera",
            "alex.rivera@syntheticbank.com",
            "+1-555-019-2831",
            745,
            7500.0,
            "United States",
        ),
        (
            "CUST102",
            "Priya Sharma",
            "priya.sharma@syntheticbank.com",
            "+1-555-014-9921",
            630,
            3500.0,
            "United States",
        ),
        (
            "CUST103",
            "Marcus Vance",
            "marcus.vance@syntheticbank.com",
            "+1-555-018-4432",
            790,
            11000.0,
            "United States",
        ),
    ]
    cursor.executemany(
        """
        INSERT INTO customers (customer_id, name, email, phone, credit_score, monthly_income, home_country)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        customers,
    )

    # Seed Accounts
    accounts = [
        ("ACC-982104", "CUST101", "Checking", 14250.75, "USD", "ACTIVE"),
        ("ACC-441209", "CUST102", "Savings", 4820.00, "USD", "ACTIVE"),
        ("ACC-110943", "CUST103", "Premier Checking", 28900.00, "USD", "ACTIVE"),
    ]
    cursor.executemany(
        """
        INSERT INTO accounts (account_number, customer_id, account_type, balance, currency, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        accounts,
    )

    # Helper for relative timestamps
    def fmt_time(hours_ago: int) -> str:
        return (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")

    # Seed Transactions (Includes deliberate normal & fraudulent patterns)
    transactions = [
        # Customer 1 (Alex Rivera: ACC-982104)
        (
            "TXN-1001",
            "ACC-982104",
            fmt_time(2),
            "Whole Foods Market",
            84.50,
            "Groceries",
            "New York, United States",
            0,
            None,
        ),
        (
            "TXN-1002",
            "ACC-982104",
            fmt_time(5),
            "Blue Bottle Coffee",
            12.75,
            "Dining",
            "New York, United States",
            0,
            None,
        ),
        (
            "TXN-1003",
            "ACC-982104",
            fmt_time(14),
            "Shell Gas Station",
            62.00,
            "Transportation",
            "Jersey City, United States",
            0,
            None,
        ),
        (
            "TXN-1004",
            "ACC-982104",
            fmt_time(20),
            "Apex Offshore Holdings",
            9200.00,
            "Wire Transfer",
            "Kyiv, Ukraine",
            1,
            "High-value overseas wire transfer exceeding normal baseline.",
        ),
        (
            "TXN-1005",
            "ACC-982104",
            fmt_time(36),
            "Euronet Lisbon ATM",
            1500.00,
            "Cash Withdrawal",
            "Lisbon, Portugal",
            1,
            "Foreign ATM withdrawal detected outside registered country.",
        ),
        (
            "TXN-1006",
            "ACC-982104",
            fmt_time(50),
            "Netflix Subscription",
            19.99,
            "Entertainment",
            "Online, United States",
            0,
            None,
        ),
        # Customer 2 (Priya Sharma: ACC-441209)
        (
            "TXN-2001",
            "ACC-441209",
            fmt_time(1),
            "CVS Pharmacy",
            34.20,
            "Health",
            "San Jose, United States",
            0,
            None,
        ),
        (
            "TXN-2002",
            "ACC-441209",
            fmt_time(4),
            "Trader Joe's",
            78.60,
            "Groceries",
            "San Jose, United States",
            0,
            None,
        ),
        (
            "TXN-2003",
            "ACC-441209",
            fmt_time(9),
            "Tokyo Ginza Gadgets",
            3600.00,
            "Electronics",
            "Tokyo, Japan",
            1,
            "Transaction amount ($3,600) consumes >70% of total balance with foreign IP/location.",
        ),
        (
            "TXN-2004",
            "ACC-441209",
            fmt_time(28),
            "Uber Rides",
            24.50,
            "Transportation",
            "San Jose, United States",
            0,
            None,
        ),
        # Customer 3 (Marcus Vance: ACC-110943)
        (
            "TXN-3001",
            "ACC-110943",
            fmt_time(3),
            "Equinox Fitness Club",
            280.00,
            "Health & Fitness",
            "New York, United States",
            0,
            None,
        ),
        (
            "TXN-3002",
            "ACC-110943",
            fmt_time(12),
            "Delta Air Lines",
            650.00,
            "Travel",
            "Atlanta, United States",
            0,
            None,
        ),
        (
            "TXN-3003",
            "ACC-110943",
            fmt_time(22),
            "Apple Store 5th Ave",
            1299.00,
            "Electronics",
            "New York, United States",
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
    print(f"Database successfully initialized at: {db_file}")
    customers = get_all_customers()
    print(f"Loaded {len(customers)} synthetic customers.")
