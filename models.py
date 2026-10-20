from datetime import datetime

from sqlalchemy import (
    Numeric,
    DateTime,
    String,
    Integer,
    BigInteger,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from extensions import db


# 1. Account Types
class AccountType(db.Model):
    __tablename__ = "account_types"

    account_type_id = db.Column(Integer, primary_key=True)
    type_name = db.Column(String(30), nullable=False, unique=True)
    description = db.Column(String(200))
    minimum_balance = db.Column(
        Numeric(12, 2), nullable=False, default=0
    )
    created_at = db.Column(
        DateTime, server_default=db.func.current_timestamp()
    )

    accounts = relationship(
        "Account", back_populates="account_type"
    )


# 2. Accounts
class Account(db.Model):
    __tablename__ = "accounts"

    account_id = db.Column(Integer, primary_key=True)
    account_name = db.Column(String(100))
    balance = db.Column(Numeric(12, 2))
    created_at = db.Column(DateTime)

    account_type_id = db.Column(
        Integer,
        ForeignKey("account_types.account_type_id"),
        nullable=True
    )

    account_type = relationship(
        "AccountType", back_populates="accounts"
    )

    transactions_sent = relationship(
        "Transaction",
        foreign_keys="Transaction.from_account",
        back_populates="source_account"
    )

    transactions_received = relationship(
        "Transaction",
        foreign_keys="Transaction.to_account",
        back_populates="destination_account"
    )


# 3. Inventory Categories
class InventoryCategory(db.Model):
    __tablename__ = "inventory_categories"

    category_id = db.Column(Integer, primary_key=True)
    category_name = db.Column(
        String(80), nullable=False, unique=True
    )
    description = db.Column(String(200))
    created_at = db.Column(
        DateTime, server_default=db.func.current_timestamp()
    )

    products = relationship(
        "Product", back_populates="category"
    )


# 4. Inventory Products
class Product(db.Model):
    __tablename__ = "inventory"

    product_id = db.Column(Integer, primary_key=True)
    product_name = db.Column(String(100))
    quantity = db.Column(Integer)
    price = db.Column(Numeric(10, 2))
    updated_at = db.Column(DateTime)

    category_id = db.Column(
        Integer,
        ForeignKey("inventory_categories.category_id"),
        nullable=True
    )

    category = relationship(
        "InventoryCategory", back_populates="products"
    )


# 5. Transactions
class Transaction(db.Model):
    __tablename__ = "transactions"

    transaction_id = db.Column(Integer, primary_key=True)

    from_account = db.Column(
        Integer, ForeignKey("accounts.account_id")
    )

    to_account = db.Column(
        Integer, ForeignKey("accounts.account_id")
    )

    amount = db.Column(Numeric(12, 2))
    transaction_type = db.Column(String(20))
    created_at = db.Column(DateTime)

    source_account = relationship(
        "Account",
        foreign_keys=[from_account],
        back_populates="transactions_sent"
    )

    destination_account = relationship(
        "Account",
        foreign_keys=[to_account],
        back_populates="transactions_received"
    )


# 6. Audit Events
class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    event_id = db.Column(BigInteger, primary_key=True)

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


# 7. Merkle Batches
class MerkleBatch(db.Model):
    __tablename__ = "merkle_batches"

    batch_id = db.Column(Integer, primary_key=True)

    start_event_id = db.Column(BigInteger)
    end_event_id = db.Column(BigInteger)
    leaf_count = db.Column(Integer)

    merkle_root = db.Column(String(64))
    previous_root_hash = db.Column(String(64))
    chained_root_hash = db.Column(String(64))

    created_at = db.Column(DateTime)


# 8. Users
class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(Integer, primary_key=True)

    username = db.Column(
        String(80), unique=True, nullable=False
    )

    password_hash = db.Column(
        String(255), nullable=False
    )

    role = db.Column(
        String(20), nullable=False, default="staff"
    )

    created_at = db.Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
