from flask import Flask, render_template, request, redirect, url_for, flash
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
        account_id = int(request.form["account_id"])
        amount = float(request.form["amount"])

        if amount > 0:
            deposit_money(account_id, amount)

        return redirect(url_for("accounts"))

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
            amount = float(request.form["amount"])

            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")

            withdraw_money(account_id, amount)

            flash("Withdrawal completed successfully.", "success")
            return redirect(url_for("accounts"))

        except ValueError as e:
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
            amount = float(request.form["amount"])

            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")

            transfer_money(from_account, to_account, amount)

            flash("Transfer completed successfully.", "success")
            return redirect(url_for("accounts"))

        except ValueError as e:
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
        product_id = int(request.form["product_id"])
        quantity = int(request.form["quantity"])
        price = float(request.form["price"])

        if quantity >= 0 and price >= 0:
            update_product(product_id, quantity, price)

        return redirect(url_for("inventory"))

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