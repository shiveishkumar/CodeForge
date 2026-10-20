import os
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g, abort, make_response
)
from functools import wraps
from werkzeug.security import check_password_hash
from models import User 
from decimal import Decimal, InvalidOperation
from datetime import datetime
from extensions import db
from services import (
    create_audit_event,
    verify_system_integrity,
    get_integrity_breakdown,
    initialize_trusted_baseline
)
from reports import (
    account_type_summary,
    inventory_category_summary,
    transaction_summary
)
from database import (
    get_accounts,
    get_inventory,
    get_transaction_count,
    deposit_money,
    withdraw_money,
    transfer_money,
    update_product,
    get_transactions,
    add_product,
    delete_product,
    get_account_by_id,
    get_product_by_id,
    get_dashboard_security_data,
    get_audit_history,
    restore_business_record,
    get_connection
)

app = Flask(__name__)

app.config["SECRET_KEY"] = (
    os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql+psycopg://"
    f"{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('DB_NAME')}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


@app.before_request
def require_login():
    # Public endpoints
    if request.endpoint in ("login", "static", None):
        return None

    # Require an authenticated session
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    g.current_user = user

    admin_only = {
        "restore_trusted_state",
        "initialize_baseline",
    }

    if (
        request.endpoint in admin_only
        and user.role != "admin"
    ):
        abort(403)

    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password_hash, password
        ):
            session.clear()
            session["user_id"] = user.user_id

            flash("Login successful.", "success")
            return redirect(url_for("home"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.after_request
def prevent_sensitive_page_caching(response):
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, private"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def home():
    accounts = get_accounts()
    products = get_inventory()
    transaction_count = get_transaction_count()

    integrity_result = verify_system_integrity()
    integrity_breakdown = get_integrity_breakdown()

    security_data = get_dashboard_security_data()

    checked_at = datetime.now().strftime("%H:%M:%S")

    return render_template(
        "dashboard.html",

        account_count=len(accounts),
        product_count=len(products),
        transaction_count=transaction_count,

        integrity_result=integrity_result,
        integrity_breakdown=integrity_breakdown,
        checked_at=checked_at,

        audit_count=security_data["audit_count"],
        batch_count=security_data["batch_count"],
        latest_root=security_data["latest_root"],

        activity_counts=security_data["activity_counts"],
        recent_activity=security_data["recent_activity"]
    )



@app.route("/accounts")
def accounts():
    from models import Account

    account_records = Account.query.order_by(
        Account.account_id
    ).all()

    # Preserve the tuple format expected by accounts.html.
    accounts = [
        (
            account.account_id,
            account.account_name,
            account.balance
        )
        for account in account_records
    ]

    return render_template(
        "accounts.html",
        accounts=accounts
    )




@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    accounts = get_accounts()

    if request.method == "POST":
        try:
            account_id = int(request.form["account_id"])
            amount = Decimal(request.form["amount"])

            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")

            old_account = get_account_by_id(account_id)

            if old_account is None:
                raise ValueError("Account not found.")

            old_balance = old_account[2]

            deposit_money(account_id, amount)

            new_account = get_account_by_id(account_id)
            new_balance = new_account[2]

            create_audit_event(
                operation="UPDATE",
                table_name="accounts",
                record_key=account_id,
                old_data={
                    "balance": str(old_balance)
                },
                new_data={
                    "balance": str(new_balance)
                },
                actor="demo_user"
            )

            flash("Deposit completed successfully.", "success")
            return redirect(url_for("accounts"))

        except (ValueError, InvalidOperation) as e:
            if isinstance(e, InvalidOperation):
                flash("Please enter a valid amount.", "error")
            else:
                flash(str(e), "error")

            return redirect(url_for("deposit"))

    return render_template(
        "deposit.html",
        accounts=accounts
    )


@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    accounts = get_accounts()

    if request.method == "POST":
        try:
            account_id = int(request.form["account_id"])
            amount = Decimal(request.form["amount"])

            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")

            old_account = get_account_by_id(account_id)

            if old_account is None:
                raise ValueError("Account not found.")

            old_balance = old_account[2]

            withdraw_money(account_id, amount)

            new_account = get_account_by_id(account_id)
            new_balance = new_account[2]

            create_audit_event(
                operation="UPDATE",
                table_name="accounts",
                record_key=account_id,
                old_data={
                    "balance": str(old_balance)
                },
                new_data={
                    "balance": str(new_balance)
                },
                actor="demo_user"
            )

            flash("Withdrawal completed successfully.", "success")
            return redirect(url_for("accounts"))

        except (ValueError, InvalidOperation) as e:
            if isinstance(e, InvalidOperation):
                flash("Please enter a valid amount.", "error")
            else:
                flash(str(e), "error")

            return redirect(url_for("withdraw"))

    return render_template(
        "withdraw.html",
        accounts=accounts
    )


@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    accounts = get_accounts()

    if request.method == "POST":
        try:
            from_account = int(request.form["from_account"])
            to_account = int(request.form["to_account"])
            amount = Decimal(request.form["amount"])

            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")

            if from_account == to_account:
                raise ValueError(
                    "Source and destination accounts cannot be the same."
                )

            old_sender = get_account_by_id(from_account)
            old_receiver = get_account_by_id(to_account)

            if old_sender is None:
                raise ValueError("Sender account not found.")

            if old_receiver is None:
                raise ValueError("Receiver account not found.")

            old_sender_balance = old_sender[2]
            old_receiver_balance = old_receiver[2]

            transfer_money(
                from_account,
                to_account,
                amount
            )

            new_sender = get_account_by_id(from_account)
            new_receiver = get_account_by_id(to_account)

            new_sender_balance = new_sender[2]
            new_receiver_balance = new_receiver[2]

            # Audit sender balance change
            create_audit_event(
                operation="UPDATE",
                table_name="accounts",
                record_key=from_account,
                old_data={
                    "balance": str(old_sender_balance)
                },
                new_data={
                    "balance": str(new_sender_balance)
                },
                actor="demo_user"
            )

            # Audit receiver balance change
            create_audit_event(
                operation="UPDATE",
                table_name="accounts",
                record_key=to_account,
                old_data={
                    "balance": str(old_receiver_balance)
                },
                new_data={
                    "balance": str(new_receiver_balance)
                },
                actor="demo_user"
            )

            flash(
                "Transfer completed successfully.",
                "success"
            )

            return redirect(url_for("accounts"))

        except (ValueError, InvalidOperation) as e:
            if isinstance(e, InvalidOperation):
                flash(
                    "Please enter a valid amount.",
                    "error"
                )
            else:
                flash(str(e), "error")

            return redirect(url_for("transfer"))

    return render_template(
        "transfer.html",
        accounts=accounts
    )



@app.route("/inventory")
def inventory():
    from models import Product

    product_records = Product.query.order_by(
        Product.product_id
    ).all()

    # Preserve the tuple format used by inventory.html.
    products = [
        (
            product.product_id,
            product.product_name,
            product.quantity,
            product.price
        )
        for product in product_records
    ]

    return render_template(
        "inventory.html",
        products=products
    )


@app.route("/inventory/edit", methods=["GET", "POST"])
def edit_product():
    products = get_inventory()

    if request.method == "POST":
        try:
            product_id = int(request.form["product_id"])
            quantity = int(request.form["quantity"])
            price = Decimal(request.form["price"])

            if quantity < 0:
                raise ValueError("Quantity cannot be negative.")

            if price < 0:
                raise ValueError("Price cannot be negative.")

            old_product = get_product_by_id(product_id)

            if old_product is None:
                raise ValueError("Product not found.")

            old_quantity = old_product[2]
            old_price = old_product[3]

            update_product(
                product_id,
                quantity,
                price
            )

            new_product = get_product_by_id(product_id)

            create_audit_event(
                operation="UPDATE",
                table_name="inventory",
                record_key=product_id,
                old_data={
                    "quantity": old_quantity,
                    "price": str(old_price)
                },
                new_data={
                    "quantity": new_product[2],
                    "price": str(new_product[3])
                },
                actor="demo_user"
            )

            flash("Product updated successfully.", "success")
            return redirect(url_for("inventory"))

        except (ValueError, InvalidOperation) as e:
            if isinstance(e, InvalidOperation):
                flash("Please enter a valid price.", "error")
            else:
                flash(str(e), "error")

            return redirect(url_for("edit_product"))

    return render_template(
        "edit_product.html",
        products=products
    )



@app.route("/transactions")
def transactions():
    from models import Transaction

    transaction_records = Transaction.query.order_by(
        Transaction.transaction_id.desc()
    ).all()

    # Preserve the tuple format expected by the template.
    transaction_list = [
        (
            transaction.transaction_id,
            transaction.from_account,
            transaction.to_account,
            transaction.amount,
            transaction.transaction_type,
            transaction.created_at
        )
        for transaction in transaction_records
    ]

    return render_template(
        "transactions.html",
        transactions=transaction_list
    )



@app.route("/inventory/add", methods=["GET", "POST"])
def add_inventory_product():
    if request.method == "POST":
        try:
            product_name = request.form["product_name"].strip()
            quantity = int(request.form["quantity"])
            price = Decimal(request.form["price"])

            if not product_name:
                raise ValueError("Product name cannot be empty.")

            if quantity < 0:
                raise ValueError("Quantity cannot be negative.")

            if price < 0:
                raise ValueError("Price cannot be negative.")

            product_id = add_product(
                product_name,
                quantity,
                price
            )

            create_audit_event(
                operation="INSERT",
                table_name="inventory",
                record_key=product_id,
                old_data=None,
                new_data={
                    "product_name": product_name,
                    "quantity": quantity,
                    "price": str(price)
                },
                actor=g.current_user.username
            )

            flash(
                "Product added and audit event recorded.",
                "success"
            )
            return redirect(url_for("inventory"))

        except (ValueError, InvalidOperation) as e:
            if isinstance(e, InvalidOperation):
                flash("Please enter a valid price.", "error")
            else:
                flash(str(e), "error")

            return redirect(url_for("add_inventory_product"))

    return render_template("add_product.html")


@app.route("/inventory/delete", methods=["GET", "POST"])
def delete_inventory_product():
    products = get_inventory()

    if request.method == "POST":
        try:
            product_id = int(request.form["product_id"])

            old_product = get_product_by_id(product_id)

            if old_product is None:
                raise ValueError("Product not found.")

            delete_product(product_id)

            create_audit_event(
                operation="DELETE",
                table_name="inventory",
                record_key=product_id,
                old_data={
                    "product_name": old_product[1],
                    "quantity": old_product[2],
                    "price": str(old_product[3])
                },
                new_data=None,
                actor=g.current_user.username
            )

            flash(
                "Product deleted and audit event recorded.",
                "success"
            )
            return redirect(url_for("inventory"))

        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("delete_inventory_product"))

    return render_template(
        "delete_product.html",
        products=products
    )


@app.route("/verify-now", methods=["POST"])
def verify_now():
    return redirect(url_for("home"))

@app.route("/audit-history")
def audit_history():

    events = get_audit_history()

    return render_template(
        "audit_history.html",
        events=events
    )

@app.route("/restore-trusted-state", methods=["POST"])
def restore_trusted_state():

    # Re-run verification first.
    # Never trust values sent from the browser.
    result = verify_system_integrity()


    # Only BUSINESS_STATE problems can be restored.
    if (
        result.get("valid")
        or result.get("type") != "BUSINESS_STATE"
    ):

        flash(
            "Automatic restoration is not available for this issue.",
            "error"
        )

        return redirect(
            url_for("home")
        )


    recoverable_violations = result.get(
        "recoverable_violations",
        []
    )


    if not recoverable_violations:

        flash(
            "No recoverable business-state violations were found.",
            "error"
        )

        return redirect(
            url_for("home")
        )


    try:

        # =================================================
        # REMOVE DUPLICATE RECORDS
        # =================================================
        #
        # Example:
        #
        # accounts #2 balance changed
        # accounts #2 account_name changed
        #
        # That is 2 field violations but only 1 record.
        # We restore the whole trusted record once.
        # =================================================

        records_to_restore = {}


        for violation in recoverable_violations:

            table_name = violation.get(
                "table_name"
            )

            record_key = violation.get(
                "record_key"
            )

            trusted_data = violation.get(
                "trusted_data"
            )


            if (
                table_name
                and record_key
                and trusted_data
            ):

                key = (
                    table_name,
                    str(record_key)
                )

                records_to_restore[key] = (
                    trusted_data
                )


        # =================================================
        # RESTORE ALL TAMPERED RECORDS
        # =================================================

        restored_count = 0


        for (
            table_name,
            record_key
        ), trusted_data in records_to_restore.items():

            restored = restore_business_record(
                table_name,
                record_key,
                trusted_data
            )


            if restored:
                restored_count += 1


        # =================================================
        # VERIFY AGAIN AFTER ALL RESTORATIONS
        # =================================================

        verification = verify_system_integrity()


        if verification.get("valid"):

            flash(
                f"{restored_count} trusted record"
                f"{'s' if restored_count != 1 else ''} "
                f"restored successfully.",
                "success"
            )

        else:

            remaining = verification.get(
                "violation_count",
                0
            )

            flash(
                f"{restored_count} record"
                f"{'s' if restored_count != 1 else ''} restored, "
                f"but {remaining} integrity issue"
                f"{'s remain' if remaining != 1 else ' remains'}.",
                "error"
            )


    except Exception as error:

        print(
            "Restore All Trusted States error:",
            error
        )

        flash(
            "An error occurred while restoring trusted states.",
            "error"
        )


    return redirect(
        url_for("home")
    )

@app.route("/initialize-baseline", methods=["POST"])
def initialize_baseline():

    try:

        result = initialize_trusted_baseline()

        created = result["created"]

        if created > 0:

            flash(
                f"Trusted baseline initialized for "
                f"{created} previously unaudited records.",
                "success"
            )

        else:

            flash(
                "All business records already have trusted audit history.",
                "success"
            )

    except Exception as error:

        print(
            "Baseline initialization error:",
            error
        )

        flash(
            "Could not initialize the trusted baseline.",
            "error"
        )

    return redirect(
        url_for("home")
    )

@app.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "reports.html",
        accounts=account_type_summary(),
        inventory=inventory_category_summary(),
        transactions=transaction_summary()
    )

@app.route("/demo/vulnerable-update", methods=["GET", "POST"])
def vulnerable_update():

    if request.method == "POST":

        account_id = request.form["account_id"]
        balance = request.form["balance"]

        conn = get_connection()

        try:
            with conn.cursor() as cur:

                # INTENTIONALLY UNSAFE
                # ONLY FOR PROJECT DEMONSTRATION
                query = f"""
                    UPDATE accounts
                    SET balance = {balance}
                    WHERE account_id = {account_id};
                """

                print("Executing vulnerable query:")
                print(query)

                cur.execute(query)
                conn.commit()

        finally:
            conn.close()

        return "Legacy database update completed."

    return render_template("vulnerable_demo.html")

if __name__ == "__main__":
    app.run(debug=True)