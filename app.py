from flask import Flask, render_template, request, redirect, url_for, flash
from decimal import Decimal, InvalidOperation

from database import (
    get_accounts,
    get_inventory,
    get_transaction_count,
    deposit_money,
    withdraw_money,
    transfer_money,
    update_product,
    get_transactions
)

app = Flask(__name__)
app.secret_key = "codeforge-demo-key"


@app.route("/")
def home():
    accounts = get_accounts()
    products = get_inventory()
    transaction_count = get_transaction_count()

    return render_template(
        "dashboard.html",
        account_count=len(accounts),
        product_count=len(products),
        transaction_count=transaction_count
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

            deposit_money(account_id, amount)

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

            withdraw_money(account_id, amount)

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

            transfer_money(from_account, to_account, amount)

            flash("Transfer completed successfully.", "success")
            return redirect(url_for("accounts"))

        except (ValueError, InvalidOperation) as e:
            if isinstance(e, InvalidOperation):
                flash("Please enter a valid amount.", "error")
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

            update_product(product_id, quantity, price)

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


if __name__ == "__main__":
    app.run(debug=True)