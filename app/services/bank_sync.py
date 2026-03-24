"""
Bank Sync Module — Pluggable provider architecture.
Add new providers by subclassing BankProvider and registering in PROVIDERS dict.
"""
import csv
import io
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class BankProvider(ABC):
    """Abstract base class for all bank providers."""

    @abstractmethod
    def fetch_transactions(self, user_id: int, days: int = 30) -> list[dict]:
        """
        Fetch transactions from the bank.
        Returns list of dicts with keys:
          external_id, amount, type, description, date, category_hint
        """
        pass

    @abstractmethod
    def fetch_balance(self, user_id: int) -> dict:
        """
        Fetch account balance.
        Returns dict with keys: available, current, currency
        """
        pass


class MockBankProvider(BankProvider):
    """
    Simulates a bank for development/testing.
    Replace this with Plaid, Mono, Stitch, or any real provider.
    """

    MOCK_MERCHANTS = [
        ('Shoprite Supermarket', 'Food & Dining', 'debit', 3500),
        ('Shell Filling Station', 'Transport', 'debit', 8000),
        ('Netflix Subscription', 'Entertainment', 'debit', 4400),
        ('Salary - ACME Corp', 'Salary', 'credit', 250000),
        ('Konga Online Shopping', 'Shopping', 'debit', 15000),
        ('DSTV Subscription', 'Entertainment', 'debit', 5000),
        ('Uber Nigeria', 'Transport', 'debit', 2500),
        ('Freelance Payment', 'Freelance', 'credit', 75000),
        ('Pharmacy', 'Health', 'debit', 3200),
        ('Electricity Bill', 'Utilities', 'debit', 12000),
        ('ATM Withdrawal', 'Miscellaneous', 'debit', 20000),
        ('Transfer Received', 'Gift', 'credit', 10000),
    ]

    def fetch_transactions(self, user_id: int, days: int = 30) -> list[dict]:
        transactions = []
        now = datetime.utcnow()
        random.seed(user_id + days)

        for i in range(random.randint(8, 15)):
            merchant = random.choice(self.MOCK_MERCHANTS)
            name, cat, t_type, base_amount = merchant
            amount = base_amount * random.uniform(0.8, 1.3)
            days_ago = random.randint(0, days)
            txn_date = now - timedelta(days=days_ago)

            transactions.append({
                'external_id': f'MOCK-{user_id}-{i}-{days_ago}',
                'amount': round(amount, 2),
                'type': t_type,
                'description': name,
                'date': txn_date,
                'category_hint': cat,
            })

        return sorted(transactions, key=lambda x: x['date'], reverse=True)

    def fetch_balance(self, user_id: int) -> dict:
        random.seed(user_id)
        return {
            'available': round(random.uniform(50000, 500000), 2),
            'current': round(random.uniform(50000, 500000), 2),
            'currency': 'NGN',
        }


class CSVImportProvider:
    """
    Parse bank statement CSVs.
    Supports common Nigerian bank export formats.
    """

    COLUMN_ALIASES = {
        'amount': ['amount', 'value', 'naira amount', 'transaction amount'],
        'type': ['type', 'transaction type', 'cr/dr', 'debit/credit'],
        'description': ['description', 'narration', 'remarks', 'memo', 'details'],
        'date': ['date', 'transaction date', 'value date', 'txn date'],
        'debit': ['debit', 'debit amount', 'withdrawal'],
        'credit': ['credit', 'credit amount', 'deposit'],
    }

    def parse(self, file_content: str) -> list[dict]:
        reader = csv.DictReader(io.StringIO(file_content))
        headers = {h.lower().strip(): h for h in (reader.fieldnames or [])}
        transactions = []

        def find_col(aliases):
            for alias in aliases:
                if alias in headers:
                    return headers[alias]
            return None

        amount_col = find_col(self.COLUMN_ALIASES['amount'])
        type_col = find_col(self.COLUMN_ALIASES['type'])
        desc_col = find_col(self.COLUMN_ALIASES['description'])
        date_col = find_col(self.COLUMN_ALIASES['date'])
        debit_col = find_col(self.COLUMN_ALIASES['debit'])
        credit_col = find_col(self.COLUMN_ALIASES['credit'])

        for row in reader:
            try:
                txn = {}

                # Determine amount and type
                if debit_col and credit_col:
                    debit_val = self._parse_amount(row.get(debit_col, ''))
                    credit_val = self._parse_amount(row.get(credit_col, ''))
                    if credit_val > 0:
                        txn['amount'] = credit_val
                        txn['type'] = 'credit'
                    elif debit_val > 0:
                        txn['amount'] = debit_val
                        txn['type'] = 'debit'
                    else:
                        continue
                elif amount_col:
                    txn['amount'] = self._parse_amount(row.get(amount_col, '0'))
                    raw_type = (row.get(type_col, '') or '').lower()
                    txn['type'] = 'credit' if any(k in raw_type for k in ['cr', 'credit', 'deposit']) else 'debit'
                else:
                    continue

                txn['description'] = row.get(desc_col, '') if desc_col else ''
                txn['date'] = self._parse_date(row.get(date_col, '')) if date_col else datetime.utcnow()
                txn['external_id'] = f'CSV-{hash(str(row))}'
                txn['category_hint'] = None

                if txn['amount'] > 0:
                    transactions.append(txn)
            except Exception:
                continue

        return transactions

    def _parse_amount(self, value: str) -> float:
        if not value:
            return 0.0
        cleaned = str(value).replace(',', '').replace('₦', '').replace('NGN', '').strip()
        try:
            return abs(float(cleaned))
        except ValueError:
            return 0.0

    def _parse_date(self, value: str) -> datetime:
        formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d',
                   '%d %b %Y', '%d-%b-%Y', '%b %d, %Y']
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt)
            except (ValueError, AttributeError):
                continue
        return datetime.utcnow()


# Auto-categorization keyword map
CATEGORY_KEYWORDS = {
    'Food & Dining': ['food', 'restaurant', 'cafe', 'coffee', 'eat', 'lunch', 'dinner', 'breakfast',
                      'shoprite', 'chicken republic', 'mr biggs', 'pizza', 'kitchen', 'canteen'],
    'Transport': ['uber', 'bolt', 'taxi', 'fuel', 'petrol', 'shell', 'total', 'bus', 'keke', 'okada', 'transport'],
    'Shopping': ['shop', 'store', 'mall', 'market', 'konga', 'jumia', 'amazon', 'purchase', 'buy'],
    'Entertainment': ['netflix', 'spotify', 'dstv', 'gotv', 'cinema', 'movie', 'game', 'showmax'],
    'Health': ['hospital', 'clinic', 'pharmacy', 'doctor', 'medical', 'health', 'drug'],
    'Utilities': ['electricity', 'water', 'internet', 'airtime', 'data', 'nepa', 'phcn', 'ikedc', 'eko electric'],
    'Savings': ['save', 'savings', 'piggybank', 'cowrywise', 'investment', 'piggyvest'],
    'Salary': ['salary', 'wages', 'payroll', 'pay'],
    'Freelance': ['freelance', 'contract', 'upwork', 'fiverr', 'project payment'],
    'Gift': ['gift', 'donation', 'transfer from', 'sent from'],
}


def auto_categorize(description: str) -> str | None:
    if not description:
        return None
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return None


def detect_duplicate(user_id: int, external_id: str, amount: float, date: datetime) -> bool:
    """Check if a transaction is a duplicate based on external_id or amount+date proximity."""
    from app.models import Transaction
    from app import db

    if external_id:
        existing = Transaction.query.filter_by(
            user_id=user_id,
            external_transaction_id=external_id
        ).first()
        if existing:
            return True

    # Check same amount within same day
    day_start = date.replace(hour=0, minute=0, second=0)
    day_end = date.replace(hour=23, minute=59, second=59)
    duplicate = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.amount == amount,
        Transaction.date >= day_start,
        Transaction.date <= day_end,
        Transaction.source.in_(['bank_sync', 'csv_import'])
    ).first()

    return duplicate is not None


# Registry of available providers
PROVIDERS = {
    'mock': MockBankProvider,
    # 'plaid': PlaidProvider,   # future
    # 'mono': MonoProvider,     # future
    # 'stitch': StitchProvider, # future
}


def get_provider(name: str = 'mock') -> BankProvider:
    cls = PROVIDERS.get(name, MockBankProvider)
    return cls()
