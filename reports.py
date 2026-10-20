
from sqlalchemy import func
from extensions import db
from models import Account, AccountType, Product, InventoryCategory, Transaction


def account_type_summary():
    """Count accounts and total balance by account type."""
    return (
        db.session.query(
            AccountType.type_name,
            func.count(Account.account_id).label("account_count"),
            func.coalesce(func.sum(Account.balance), 0).label("total_balance")
        )
        .outerjoin(Account, Account.account_type_id == AccountType.account_type_id)
        .group_by(AccountType.account_type_id, AccountType.type_name)
        .order_by(AccountType.type_name)
        .all()
    )


def inventory_category_summary():
    """Count products and stock value by category."""
    return (
        db.session.query(
            InventoryCategory.category_name,
            func.count(Product.product_id).label("product_count"),
            func.coalesce(
                func.sum(Product.quantity * Product.price), 0
            ).label("stock_value")
        )
        .outerjoin(
            Product,
            Product.category_id == InventoryCategory.category_id
        )
        .group_by(
            InventoryCategory.category_id,
            InventoryCategory.category_name
        )
        .order_by(InventoryCategory.category_name)
        .all()
    )


def transaction_summary():
    """Count transactions and sum transaction amounts by type."""
    return (
        db.session.query(
            Transaction.transaction_type,
            func.count(Transaction.transaction_id).label("transaction_count"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount")
        )
        .group_by(Transaction.transaction_type)
        .order_by(Transaction.transaction_type)
        .all()
    )
