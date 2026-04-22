import os
import psycopg2
from psycopg2 import pool
from datetime import datetime
import time

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'bank_app'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Create a connection pool
connection_pool = None

def init_connection_pool(min_connections=1, max_connections=10, max_retries=5, retry_delay=2):
    global connection_pool
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_connections,
                max_connections,
                **DB_CONFIG
            )
            print("Database connection pool created successfully")
            return
        except Exception as e:
            retry_count += 1
            print(f"Failed to connect to database (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Could not establish database connection.")
                raise e

def get_connection():
    if connection_pool:
        return connection_pool.getconn()
    raise Exception("Connection pool not initialized")

def return_connection(connection):
    if connection_pool:
        connection_pool.putconn(connection)

def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    account_number TEXT NOT NULL UNIQUE,
                    balance DECIMAL(15, 2) DEFAULT 1000.0,
                    is_admin BOOLEAN DEFAULT FALSE,
                    profile_picture TEXT,
                    reset_pin TEXT,
                    bio TEXT,
                    is_suspended BOOLEAN DEFAULT FALSE
                )
            ''')

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE")
            except Exception:
                pass
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS loans (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    amount DECIMAL(15, 2),
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    from_account TEXT NOT NULL,
                    to_account TEXT NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    transaction_type TEXT NOT NULL,
                    description TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS virtual_cards (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    card_number TEXT NOT NULL UNIQUE,
                    cvv TEXT NOT NULL,
                    expiry_date TEXT NOT NULL,
                    card_limit NUMERIC(20, 8) DEFAULT 1000.0,
                    current_balance NUMERIC(20, 8) DEFAULT 0.0,
                    is_frozen BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    card_type TEXT DEFAULT 'standard',
                    currency TEXT DEFAULT 'USD'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS card_transactions (
                    id SERIAL PRIMARY KEY,
                    card_id INTEGER REFERENCES virtual_cards(id) ON DELETE CASCADE,
                    amount NUMERIC(20, 8) NOT NULL,
                    merchant_name TEXT,
                    transaction_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            ''')

            try:
                cursor.execute("ALTER TABLE virtual_cards ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD'")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE virtual_cards ALTER COLUMN card_limit TYPE NUMERIC(20, 8)")
                cursor.execute("ALTER TABLE virtual_cards ALTER COLUMN current_balance TYPE NUMERIC(20, 8)")
                cursor.execute("ALTER TABLE card_transactions ALTER COLUMN amount TYPE NUMERIC(20, 8)")
            except Exception:
                pass
            
            cursor.execute("SELECT * FROM users WHERE username='admin'")
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO users (username, password, account_number, balance, is_admin) 
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    ('admin', 'admin123', 'ADMIN001', 1000000.0, True)
                )
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bill_categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS billers (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER REFERENCES bill_categories(id),
                    name TEXT NOT NULL,
                    account_number TEXT NOT NULL,
                    description TEXT,
                    minimum_amount DECIMAL(15, 2) DEFAULT 0,
                    maximum_amount DECIMAL(15, 2),
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bill_payments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    biller_id INTEGER REFERENCES billers(id),
                    amount DECIMAL(15, 2) NOT NULL,
                    payment_method TEXT NOT NULL,
                    card_id INTEGER REFERENCES virtual_cards(id),
                    reference_number TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    description TEXT
                )
            ''')

            cursor.execute("""
                INSERT INTO bill_categories (name, description) 
                VALUES 
                ('Utilities', 'Water, Electricity, Gas bills'),
                ('Telecommunications', 'Phone, Internet, Cable TV'),
                ('Insurance', 'Life, Health, Auto insurance'),
                ('Credit Cards', 'Credit card bill payments')
                ON CONFLICT (name) DO NOTHING
            """)

            cursor.execute("""
                INSERT INTO billers (category_id, name, account_number, description, minimum_amount) 
                VALUES 
                (1, 'City Water', 'WATER001', 'City Water Utility', 10),
                (1, 'PowerGen Electric', 'POWER001', 'Electricity Provider', 20),
                (2, 'TeleCom Services', 'TEL001', 'Phone and Internet', 25),
                (2, 'CableTV Plus', 'CABLE001', 'Cable TV Services', 30),
                (3, 'HealthFirst Insurance', 'INS001', 'Health Insurance', 100),
                (4, 'Universal Bank Card', 'CC001', 'Credit Card Payments', 50)
                ON CONFLICT DO NOTHING
            """)
            
            conn.commit()
            print("Database initialized successfully")
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        raise e
    finally:
        return_connection(conn)

def execute_query(query, params=None, fetch=True):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            result = None
            if fetch:
                result = cursor.fetchall()
            # Always commit for INSERT, UPDATE, DELETE operations
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
            return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        return_connection(conn)

def execute_transaction(queries_and_params):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for query, params in queries_and_params:
                cursor.execute(query, params)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        return_connection(conn)
