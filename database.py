import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
def get_accounts():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT account_id, account_name, balance
            FROM accounts
            ORDER BY account_id;
        """)
        accounts = cur.fetchall()

    conn.close()
    return accounts


def get_inventory():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT product_id, product_name, quantity, price
            FROM inventory
            ORDER BY product_id;
        """)
        products = cur.fetchall()

    conn.close()
    return products

def get_transaction_count():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM transactions;")
        count = cur.fetchone()[0]

    conn.close()
    return count

def deposit_money(account_id, amount):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            # Check that the account exists
            cur.execute(
                "SELECT balance FROM accounts WHERE account_id = %s;",
                (account_id,)
            )

            account = cur.fetchone()

            if account is None:
                raise ValueError("Account not found.")

            # Add money to the account
            cur.execute(
                """
                UPDATE accounts
                SET balance = balance + %s
                WHERE account_id = %s;
                """,
                (amount, account_id)
            )

            # Record the business transaction
            cur.execute(
                """
                INSERT INTO transactions
                (to_account, amount, transaction_type)
                VALUES (%s, %s, 'DEPOSIT');
                """,
                (account_id, amount)
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def withdraw_money(account_id, amount):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            # Get current balance
            cur.execute(
                "SELECT balance FROM accounts WHERE account_id = %s;",
                (account_id,)
            )

            account = cur.fetchone()

            if account is None:
                raise ValueError("Account not found.")

            current_balance = account[0]

            # Prevent overdrawing
            if amount > current_balance:
                raise ValueError("Insufficient balance.")

            # Deduct money
            cur.execute(
                """
                UPDATE accounts
                SET balance = balance - %s
                WHERE account_id = %s;
                """,
                (amount, account_id)
            )

            # Record business transaction
            cur.execute(
                """
                INSERT INTO transactions
                (from_account, amount, transaction_type)
                VALUES (%s, %s, 'WITHDRAW');
                """,
                (account_id, amount)
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def transfer_money(from_account, to_account, amount):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            if from_account == to_account:
                raise ValueError("Source and destination accounts cannot be the same.")

            # Get sender balance
            cur.execute(
                "SELECT balance FROM accounts WHERE account_id = %s;",
                (from_account,)
            )

            sender = cur.fetchone()

            if sender is None:
                raise ValueError("Sender account not found.")

            # Check receiver exists
            cur.execute(
                "SELECT account_id FROM accounts WHERE account_id = %s;",
                (to_account,)
            )

            receiver = cur.fetchone()

            if receiver is None:
                raise ValueError("Receiver account not found.")

            # Check sender has enough money
            if amount > sender[0]:
                raise ValueError("Insufficient balance.")

            # Deduct from sender
            cur.execute(
                """
                UPDATE accounts
                SET balance = balance - %s
                WHERE account_id = %s;
                """,
                (amount, from_account)
            )

            # Add to receiver
            cur.execute(
                """
                UPDATE accounts
                SET balance = balance + %s
                WHERE account_id = %s;
                """,
                (amount, to_account)
            )

            # Record one business transaction
            cur.execute(
                """
                INSERT INTO transactions
                (from_account, to_account, amount, transaction_type)
                VALUES (%s, %s, %s, 'TRANSFER');
                """,
                (from_account, to_account, amount)
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def update_product(product_id, quantity, price):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            # Check that product exists
            cur.execute(
                """
                SELECT product_id
                FROM inventory
                WHERE product_id = %s;
                """,
                (product_id,)
            )

            product = cur.fetchone()

            if product is None:
                raise ValueError("Product not found.")

            # Update quantity and price
            cur.execute(
                """
                UPDATE inventory
                SET quantity = %s,
                    price = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s;
                """,
                (quantity, price, product_id)
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def get_transactions():
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                t.transaction_id,
                t.transaction_type,
                t.from_account,
                fa.account_name,
                t.to_account,
                ta.account_name,
                t.amount,
                t.created_at
            FROM transactions t

            LEFT JOIN accounts fa
                ON t.from_account = fa.account_id

            LEFT JOIN accounts ta
                ON t.to_account = ta.account_id

            ORDER BY t.transaction_id DESC;
        """)

        transactions = cur.fetchall()

    conn.close()
    return transactions

def add_product(product_name, quantity, price):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO inventory
                (product_name, quantity, price)
                VALUES (%s, %s, %s);
                """,
                (product_name, quantity, price)
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def delete_product(product_id):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM inventory
                WHERE product_id = %s;
                """,
                (product_id,)
            )

            if cur.rowcount == 0:
                raise ValueError("Product not found.")

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    try:
        accounts = get_accounts()
        products = get_inventory()

        print("Database connected successfully!")
        print("Total accounts:", len(accounts))
        print("Total inventory products:", len(products))

        print("\nFirst 3 accounts:")
        for account in accounts[:3]:
            print(account)

        print("\nFirst 3 products:")
        for product in products[:3]:
            print(product)

    except Exception as e:
        print("Error!")
        print(e)