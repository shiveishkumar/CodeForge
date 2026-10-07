import os
import psycopg
from dotenv import load_dotenv
import json
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

def get_last_event_hash():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_hash
                FROM audit_events
                ORDER BY event_id DESC
                LIMIT 1;
                """
            )

            row = cur.fetchone()

            if row is None:
                return None

            return row[0]

    finally:
        conn.close()


def insert_audit_event(event_record):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_events (
                    operation,
                    table_name,
                    record_key,
                    old_data,
                    new_data,
                    actor,
                    created_at,
                    previous_hash,
                    event_hash
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                RETURNING event_id;
                """,
                (
                    event_record["operation"],
                    event_record["table_name"],
                    event_record["record_key"],
                    json.dumps(event_record["old_data"]),
                    json.dumps(event_record["new_data"]),
                    event_record["actor"],
                    event_record["created_at"],
                    event_record.get("previous_hash"),
                    event_record["event_hash"]
                )
            )

            event_id = cur.fetchone()[0]

        conn.commit()
        return event_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_unbatched_audit_events():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    event_id,
                    operation,
                    table_name,
                    record_key,
                    old_data,
                    new_data,
                    actor,
                    created_at,
                    previous_hash,
                    event_hash,
                    batch_id
                FROM audit_events
                WHERE batch_id IS NULL
                ORDER BY event_id
                LIMIT 4;
                """
            )

            rows = cur.fetchall()

        return rows

    finally:
        conn.close()


def insert_merkle_batch(
    start_event_id,
    end_event_id,
    leaf_count,
    merkle_root,
    previous_root_hash,
    chained_root_hash
):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO merkle_batches (
                    start_event_id,
                    end_event_id,
                    leaf_count,
                    merkle_root,
                    previous_root_hash,
                    chained_root_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING batch_id;
                """,
                (
                    start_event_id,
                    end_event_id,
                    leaf_count,
                    merkle_root,
                    previous_root_hash,
                    chained_root_hash
                )
            )

            batch_id = cur.fetchone()[0]

            cur.execute(
                """
                UPDATE audit_events
                SET batch_id = %s
                WHERE event_id BETWEEN %s AND %s;
                """,
                (
                    batch_id,
                    start_event_id,
                    end_event_id
                )
            )

        conn.commit()
        return batch_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_last_chained_root():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chained_root_hash
                FROM merkle_batches
                ORDER BY batch_id DESC
                LIMIT 1;
                """
            )

            row = cur.fetchone()

            if row is None:
                return None

            return row[0]

    finally:
        conn.close()

def get_account_by_id(account_id):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT account_id, account_name, balance
                FROM accounts
                WHERE account_id = %s;
                """,
                (account_id,)
            )

            return cur.fetchone()

    finally:
        conn.close()

def get_all_audit_events():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    event_id,
                    operation,
                    table_name,
                    record_key,
                    old_data,
                    new_data,
                    actor,
                    created_at,
                    previous_hash,
                    event_hash,
                    batch_id
                FROM audit_events
                ORDER BY event_id;
                """
            )

            rows = cur.fetchall()

            events = []

            for row in rows:
                events.append({
                    "event_id": row[0],
                    "operation": row[1],
                    "table_name": row[2],
                    "record_key": row[3],
                    "old_data": row[4],
                    "new_data": row[5],
                    "actor": row[6],
                    "created_at": row[7],
                    "previous_hash": (row[8] or "").strip(),
                    "event_hash": row[9].strip(),
                    "batch_id": row[10]
                })

            return events

    finally:
        conn.close()


def get_all_merkle_batches():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    batch_id,
                    start_event_id,
                    end_event_id,
                    leaf_count,
                    merkle_root,
                    previous_root_hash,
                    chained_root_hash,
                    created_at
                FROM merkle_batches
                ORDER BY batch_id;
                """
            )

            rows = cur.fetchall()

            batches = []

            for row in rows:
                batches.append({
                    "batch_id": row[0],
                    "start_event_id": row[1],
                    "end_event_id": row[2],
                    "leaf_count": row[3],
                    "merkle_root": row[4].strip(),
                    "previous_root_hash": (row[5] or "").strip(),
                    "chained_root_hash": row[6].strip(),
                    "created_at": row[7]
                })

            return batches

    finally:
        conn.close()

def get_latest_audited_states():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (table_name, record_key)
                    table_name,
                    record_key,
                    new_data,
                    operation
                FROM audit_events
                ORDER BY table_name, record_key, event_id DESC;
                """
            )

            rows = cur.fetchall()

            states = []

            for row in rows:
                states.append({
                    "table_name": row[0],
                    "record_key": row[1],
                    "new_data": row[2],
                    "operation": row[3]
                })

            return states

    finally:
        conn.close()


def get_current_business_record(table_name, record_key):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            if table_name == "accounts":
                cur.execute(
                    """
                    SELECT account_id, account_name, balance
                    FROM accounts
                    WHERE account_id = %s;
                    """,
                    (record_key,)
                )

                row = cur.fetchone()

                if row is None:
                    return None

                return {
                    "account_id": row[0],
                    "account_name": row[1],
                    "balance": str(row[2])
                }

            elif table_name == "inventory":
                cur.execute(
                    """
                    SELECT product_id, product_name, quantity, price
                    FROM inventory
                    WHERE product_id = %s;
                    """,
                    (record_key,)
                )

                row = cur.fetchone()

                if row is None:
                    return None

                return {
                    "product_id": row[0],
                    "product_name": row[1],
                    "quantity": row[2],
                    "price": str(row[3])
                }

            return None

    finally:
        conn.close()

def get_product_by_id(product_id):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    product_id,
                    product_name,
                    quantity,
                    price
                FROM inventory
                WHERE product_id = %s;
                """,
                (product_id,)
            )

            return cur.fetchone()

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