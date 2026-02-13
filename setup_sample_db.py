"""
Sample Database Setup Script

This script creates a sample analytics database with tables and data
for testing the DataChat.

Usage:
    python setup_sample_db.py

Requirements:
    - PostgreSQL server running
    - psycopg2-binary installed
    - Database credentials in .env file
"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


def create_sample_database():
    """Create sample database with analytics data."""
    
    # Connection parameters
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', 5432))
    database = os.getenv('DB_NAME', 'analytics')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    
    logger.info(f"Connecting to PostgreSQL at {host}:{port}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=host,
            port=port,
            database='postgres',  # Connect to default database first
            user=user,
            password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
            [database]
        )
        
        if not cursor.fetchone():
            logger.info(f"Creating database: {database}")
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
            )
        else:
            logger.info(f"Database {database} already exists")
        
        cursor.close()
        conn.close()
        
        # Connect to the analytics database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        logger.info("Creating tables...")
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                region VARCHAR(50),
                signup_date DATE,
                is_active BOOLEAN DEFAULT true
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50),
                price DECIMAL(10, 2),
                cost DECIMAL(10, 2),
                stock_quantity INTEGER
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(customer_id),
                order_date DATE NOT NULL,
                total_amount DECIMAL(10, 2),
                status VARCHAR(20)
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(order_id),
                product_id INTEGER REFERENCES products(product_id),
                quantity INTEGER,
                unit_price DECIMAL(10, 2)
            );
        """)
        
        conn.commit()
        logger.info("Tables created successfully")
        
        logger.info("Inserting sample data...")
        
        # Insert sample data
        
        # Customers
        cursor.execute("""
            INSERT INTO customers (name, email, region, signup_date, is_active)
            VALUES
                ('John Doe', 'john.doe@email.com', 'North', '2023-01-15', true),
                ('Jane Smith', 'jane.smith@email.com', 'South', '2023-02-20', true),
                ('Bob Johnson', 'bob.j@email.com', 'East', '2023-03-10', true),
                ('Alice Williams', 'alice.w@email.com', 'West', '2023-04-05', true),
                ('Charlie Brown', 'charlie.b@email.com', 'North', '2023-05-12', false),
                ('Diana Davis', 'diana.d@email.com', 'South', '2023-06-18', true),
                ('Eve Martinez', 'eve.m@email.com', 'East', '2023-07-22', true),
                ('Frank Wilson', 'frank.w@email.com', 'West', '2023-08-30', true),
                ('Grace Lee', 'grace.l@email.com', 'North', '2023-09-14', true),
                ('Henry Taylor', 'henry.t@email.com', 'South', '2023-10-25', true)
            ON CONFLICT (email) DO NOTHING;
        """)
        
        # Products
        cursor.execute("""
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
            ON CONFLICT DO NOTHING;
        """)
        
        # Orders
        cursor.execute("""
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
            ON CONFLICT DO NOTHING;
        """)
        
        # Order Items
        cursor.execute("""
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
            ON CONFLICT DO NOTHING;
        """)
        
        conn.commit()
        logger.info("Sample data inserted successfully")
        
        # Print summary
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM order_items")
        item_count = cursor.fetchone()[0]
        
        logger.info("=" * 50)
        logger.info("Database setup complete!")
        logger.info("=" * 50)
        logger.info(f"Database: {database}")
        logger.info(f"Customers: {customer_count}")
        logger.info(f"Products: {product_count}")
        logger.info(f"Orders: {order_count}")
        logger.info(f"Order Items: {item_count}")
        logger.info("=" * 50)
        logger.info("\nExample questions you can ask:")
        logger.info("  - What are the top 5 customers by total order amount?")
        logger.info("  - Show me sales by product category")
        logger.info("  - Which region has the most customers?")
        logger.info("  - What is the average order value?")
        logger.info("  - Show me monthly revenue trends")
        logger.info("=" * 50)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise


if __name__ == "__main__":
    create_sample_database()
