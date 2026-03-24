"""
Seed the database with demo transactions for testing.
Run after starting the app and creating an account.

Usage:
    python seed_data.py --email your@email.com
"""
import sys
import os
import random
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Transaction, Category

DEMO_TRANSACTIONS = [
    ('Salary - ACME Corp', 'credit', 'Salary', 350000),
    ('Shoprite Supermarket', 'debit', 'Food & Dining', 12500),
    ('Shell Filling Station', 'debit', 'Transport', 18000),
    ('Netflix Subscription', 'debit', 'Entertainment', 4400),
    ('Konga Online Shopping', 'debit', 'Shopping', 25000),
    ('DSTV Subscription', 'debit', 'Entertainment', 5000),
    ('Uber Nigeria', 'debit', 'Transport', 3200),
    ('Freelance Project', 'credit', 'Freelance', 85000),
    ('Pharmacy', 'debit', 'Health', 4500),
    ('Electricity Bill', 'debit', 'Utilities', 15000),
    ('Birthday Gift Received', 'credit', 'Gift', 20000),
    ('Chicken Republic', 'debit', 'Food & Dining', 4800),
    ('Mr Biggs', 'debit', 'Food & Dining', 3200),
    ('Savings Transfer', 'debit', 'Savings', 50000),
    ('ATM Withdrawal', 'debit', 'Miscellaneous', 20000),
    ('Airtime Top-up', 'debit', 'Utilities', 2000),
    ('Transfer Received', 'credit', 'Miscellaneous', 15000),
    ('Investment Return', 'credit', 'Investment', 12000),
]

def seed(email):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"User {email} not found. Create an account first.")
            return

        now = datetime.utcnow()
        count = 0

        for month_offset in range(6):  # Last 6 months
            for desc, t_type, cat_name, base_amount in DEMO_TRANSACTIONS:
                if random.random() < 0.7:  # 70% chance each txn appears
                    category = Category.query.filter_by(name=cat_name).first()
                    days_in_month = random.randint(1, 28)
                    txn_date = (now - timedelta(days=month_offset * 30)).replace(day=1)
                    txn_date = txn_date + timedelta(days=days_in_month)
                    amount = round(base_amount * random.uniform(0.8, 1.2), 2)

                    txn = Transaction(
                        user_id=user.id,
                        amount=amount,
                        type=t_type,
                        category_id=category.id if category else None,
                        description=desc,
                        date=txn_date,
                        source='manual',
                    )
                    db.session.add(txn)
                    count += 1

        db.session.commit()
        print(f"✅ Seeded {count} demo transactions for {email}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True, help='User email to seed data for')
    args = parser.parse_args()
    seed(args.email)
