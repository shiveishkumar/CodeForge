from flask import Flask, render_template, request, redirect, url_for, flash
from decimal import Decimal, InvalidOperation
from services import create_audit_event, verify_system_integrity
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
    get_product_by_id
)

app = Flask(__name__)
app.secret_key = "codeforge-demo-key"


@app.route("/")
def home():
    accounts = get_accounts()
    products = get_inventory()
    transaction_count = get_transaction_count()

    integrity_result = verify_system_integrity()

    return render_template(
        "dashboard.html",
        account_count=len(accounts),
        product_count=len(products),
        transaction_count=transaction_count,
        integrity_result=integrity_result
    )


@app.route("/accounts")
def accounts():
    accounts = get_accounts()

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
    products = get_inventory()

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
    transaction_list = get_transactions()

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

            add_product(product_name, quantity, price)

            flash("Product added successfully.", "success")
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

            delete_product(product_id)

            flash("Product deleted successfully.", "success")
            return redirect(url_for("inventory"))

        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("delete_inventory_product"))

    return render_template(
        "delete_product.html",
        products=products
    )

if __name__ == "__main__":
    app.run(debug=True)