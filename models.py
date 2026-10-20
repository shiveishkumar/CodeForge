from datetime import datetime
from datetime import datetime
from sqlalchemy import (
    Numeric,
    DateTime,
    String,
    Integer,
    BigInteger
)
from sqlalchemy.dialects.postgresql import JSONB
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


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    event_id = db.Column(
        BigInteger,
        primary_key=True
    )

    operation = db.Column(String(20))
    table_name = db.Column(String(100))
    record_key = db.Column(String(100))

    old_data = db.Column(JSONB)
    new_data = db.Column(JSONB)

    actor = db.Column(String(100))
    created_at = db.Column(DateTime)

    previous_hash = db.Column(String(64))
    event_hash = db.Column(String(64))
    batch_id = db.Column(Integer)


class MerkleBatch(db.Model):
    __tablename__ = "merkle_batches"

    batch_id = db.Column(
        Integer,
        primary_key=True
    )

    start_event_id = db.Column(BigInteger)
    end_event_id = db.Column(BigInteger)
    leaf_count = db.Column(Integer)

    merkle_root = db.Column(String(64))
    previous_root_hash = db.Column(String(64))
    chained_root_hash = db.Column(String(64))

    created_at = db.Column(DateTime)




class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(
        Integer,
        primary_key=True
    )

    username = db.Column(
        String(80),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        String(255),
        nullable=False
    )

    role = db.Column(
        String(20),
        nullable=False,
        default="staff"
    )

    created_at = db.Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
