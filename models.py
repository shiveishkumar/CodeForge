
from extensions import db
from sqlalchemy import Numeric, DateTime, String, Integer


class Account(db.Model):
    __tablename__ = "accounts"

    account_id = db.Column(
        Integer,
        primary_key=True
    )

    account_name = db.Column(
        String(100)
    )

    balance = db.Column(
        Numeric(12, 2)
    )

    created_at = db.Column(
        DateTime
    )


class Product(db.Model):
    __tablename__ = "inventory"

    product_id = db.Column(
        Integer,
        primary_key=True
    )

    product_name = db.Column(
        String(100)
    )

    quantity = db.Column(
        Integer
    )

    price = db.Column(
        Numeric(10, 2)
    )

    updated_at = db.Column(
        DateTime
    )


class Transaction(db.Model):
    __tablename__ = "transactions"

    transaction_id = db.Column(
        Integer,
        primary_key=True
    )

    from_account = db.Column(
        Integer,
        db.ForeignKey("accounts.account_id")
    )

    to_account = db.Column(
        Integer,
        db.ForeignKey("accounts.account_id")
    )

    amount = db.Column(
        Numeric(12, 2)
    )

    transaction_type = db.Column(
        String(20)
    )

    created_at = db.Column(
        DateTime
    )
