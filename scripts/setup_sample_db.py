"""
Sample Database Setup Script

This script creates a sample analytics database with tables and data
for testing the DataChat. Supports PostgreSQL and SQLite.

Usage:
    python setup_sample_db.py

Requirements:
    - Database credentials in .env file
    - psycopg2-binary installed (for PostgreSQL)
"""

import os
import sys
import sqlite3
from typing import List, Dict, Any
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


def get_db_type():
    return os.getenv('DB_TYPE', 'postgres').lower()


def setup_postgresql():
    """Setup PostgreSQL database."""
    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
        return

    # Connection parameters
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', 5432))
    database = os.getenv('DB_NAME', 'analytics')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    
    logger.info(f"Connecting to PostgreSQL at {host}:{port}")
    
    try:
        # Connect to default database to create target DB
        conn = psycopg2.connect(
            host=host, port=port, database='postgres', user=user, password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [database])
        if not cursor.fetchone():
            logger.info(f"Creating database: {database}")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        else:
            logger.info(f"Database {database} already exists")
        
        cursor.close()
        conn.close()
        
        # Connect to the analytics database
        conn = psycopg2.connect(
            host=host, port=port, database=database, user=user, password=password
        )
        cursor = conn.cursor()
        
        create_tables_and_data(cursor, 'postgres')
        
        conn.commit()
        logger.info("PostgreSQL setup complete!")
        conn.close()
        
    except Exception as e:
        logger.error(f"PostgreSQL setup failed: {e}")
        raise


def setup_sqlite():
    """Setup SQLite database."""
    # Get database path from env or default
    db_path = os.getenv('DB_NAME', 'data/analytics.db')
    
    # If path is relative and doesn't start with /, make it relative to project root
    if not os.path.isabs(db_path):
        # Assuming script is in scripts/ and project root is one level up
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        db_path = os.path.join(project_root, db_path)
        
    logger.info(f"Setting up SQLite database: {db_path}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        create_tables_and_data(cursor, 'sqlite')
        
        conn.commit()
        logger.info("SQLite setup complete!")
        conn.close()
        
    except Exception as e:
        logger.error(f"SQLite setup failed: {e}")
        raise


def create_tables_and_data(cursor, db_type):
    """Create tables and insert data."""
    logger.info("Creating tables...")
    
    # Data type mapping
    types = {
        'serial_pk': 'SERIAL PRIMARY KEY' if db_type == 'postgres' else 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'timestamp': 'TIMESTAMP' if db_type == 'postgres' else 'TEXT',
        'bool_true': 'true' if db_type == 'postgres' else '1',
        'bool_false': 'false' if db_type == 'postgres' else '0',
    }
    
    # Create tables
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id {types['serial_pk']},
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            region VARCHAR(50),
            signup_date DATE,
            is_active BOOLEAN DEFAULT {types['bool_true']}
        );
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS products (
            product_id {types['serial_pk']},
            name VARCHAR(100) NOT NULL,
            category VARCHAR(50),
            price DECIMAL(10, 2),
            cost DECIMAL(10, 2),
            stock_quantity INTEGER
        );
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS orders (
            order_id {types['serial_pk']},
            customer_id INTEGER REFERENCES customers(customer_id),
            order_date DATE NOT NULL,
            total_amount DECIMAL(10, 2),
            status VARCHAR(20)
        );
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id {types['serial_pk']},
            order_id INTEGER REFERENCES orders(order_id),
            product_id INTEGER REFERENCES products(product_id),
            quantity INTEGER,
            unit_price DECIMAL(10, 2)
        );
    """)
    
    logger.info("Tables created successfully. Inserting sample data...")
    
    # Helper for ON CONFLICT
    on_conflict_email = "ON CONFLICT (email) DO NOTHING"
    on_conflict_do_nothing = "ON CONFLICT DO NOTHING"
    
    # Customers
    cursor.execute(f"""
        INSERT INTO customers (name, email, region, signup_date, is_active)
        VALUES
            ('John Doe', 'john.doe@email.com', 'North', '2023-01-15', {types['bool_true']}),
            ('Jane Smith', 'jane.smith@email.com', 'South', '2023-02-20', {types['bool_true']}),
            ('Bob Johnson', 'bob.j@email.com', 'East', '2023-03-10', {types['bool_true']}),
            ('Alice Williams', 'alice.w@email.com', 'West', '2023-04-05', {types['bool_true']}),
            ('Charlie Brown', 'charlie.b@email.com', 'North', '2023-05-12', {types['bool_false']}),
            ('Diana Davis', 'diana.d@email.com', 'South', '2023-06-18', {types['bool_true']}),
            ('Eve Martinez', 'eve.m@email.com', 'East', '2023-07-22', {types['bool_true']}),
            ('Frank Wilson', 'frank.w@email.com', 'West', '2023-08-30', {types['bool_true']}),
            ('Grace Lee', 'grace.l@email.com', 'North', '2023-09-14', {types['bool_true']}),
            ('Henry Taylor', 'henry.t@email.com', 'South', '2023-10-25', {types['bool_true']})
        {on_conflict_email};
    """)
    
    # Products
    cursor.execute(f"""
        INSERT INTO products (name, category, price, cost, stock_quantity)
        VALUES
            ('Laptop Pro', 'Electronics', 1299.99, 800.00, 50),
            ('Wireless Mouse', 'Electronics', 29.99, 15.00, 200),
            ('Office Chair', 'Furniture', 249.99, 150.00, 75),
            ('Desk Lamp', 'Furniture', 39.99, 20.00, 150),
            ('Notebook Set', 'Stationery', 12.99, 5.00, 500),
            ('Pen Pack', 'Stationery', 8.99, 3.00, 300),
            ('Monitor 27"', 'Electronics', 349.99, 200.00, 80),
            ('Keyboard', 'Electronics', 79.99, 40.00, 120),
            ('Standing Desk', 'Furniture', 599.99, 350.00, 30),
            ('Webcam HD', 'Electronics', 89.99, 50.00, 100)
        {on_conflict_do_nothing};
    """)
    
    # Orders
    cursor.execute(f"""
        INSERT INTO orders (customer_id, order_date, total_amount, status)
        VALUES
            (1, '2024-01-10', 1329.98, 'completed'),
            (2, '2024-01-15', 249.99, 'completed'),
            (3, '2024-01-20', 89.99, 'completed'),
            (1, '2024-02-05', 429.98, 'completed'),
            (4, '2024-02-10', 1299.99, 'completed'),
            (5, '2024-02-15', 52.98, 'cancelled'),
            (6, '2024-03-01', 349.99, 'completed'),
            (7, '2024-03-10', 599.99, 'completed'),
            (2, '2024-03-20', 109.98, 'completed'),
            (8, '2024-04-05', 1379.98, 'completed'),
            (9, '2024-04-15', 79.99, 'processing'),
            (10, '2024-04-20', 289.98, 'completed')
        {on_conflict_do_nothing};
    """)
    
    # Order Items
    cursor.execute(f"""
        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
        VALUES
            (1, 1, 1, 1299.99),
            (1, 2, 1, 29.99),
            (2, 3, 1, 249.99),
            (3, 10, 1, 89.99),
            (4, 7, 1, 349.99),
            (4, 8, 1, 79.99),
            (5, 1, 1, 1299.99),
            (6, 5, 2, 12.99),
            (6, 6, 3, 8.99),
            (7, 7, 1, 349.99),
            (8, 9, 1, 599.99),
            (9, 4, 1, 39.99),
            (9, 5, 3, 12.99),
            (9, 6, 2, 8.99),
            (10, 1, 1, 1299.99),
            (10, 8, 1, 79.99),
            (11, 8, 1, 79.99),
            (12, 3, 1, 249.99),
            (12, 4, 1, 39.99)
        {on_conflict_do_nothing};
    """)
    
    logger.info("Sample data inserted successfully")


if __name__ == "__main__":
    db_type = get_db_type()
    if db_type == 'sqlite':
        setup_sqlite()
    else:
        setup_postgresql()
