"""
Data access layer — raw SQLite queries.
Each class is a namespace for DB operations (no ORM).
"""
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db, row_to_dict, rows_to_list
from datetime import datetime


class UserModel:
    @staticmethod
    def create(username, email, password):
        db = get_db()
        pw_hash = generate_password_hash(password)
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
            (username, email, pw_hash)
        )
        db.commit()
        return UserModel.get_by_id(cur.lastrowid)

    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return row_to_dict(row)

    @staticmethod
    def get_by_email(email):
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return row_to_dict(row)

    @staticmethod
    def get_by_username(username):
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return row_to_dict(row)

    @staticmethod
    def check_password(user_dict, password):
        return check_password_hash(user_dict['password_hash'], password)

    @staticmethod
    def update_push(user_id, subscription_json, enabled):
        db = get_db()
        db.execute(
            "UPDATE users SET push_subscription=?, notifications_enabled=? WHERE id=?",
            (subscription_json, 1 if enabled else 0, user_id)
        )
        db.commit()

    @staticmethod
    def to_public(user):
        if not user:
            return None
        return {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'notifications_enabled': bool(user.get('notifications_enabled', 0)),
        }


class CategoryModel:
    @staticmethod
    def list_for_user(user_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM categories WHERE user_id IS NULL OR user_id=? ORDER BY name",
            (user_id,)
        ).fetchall()
        return rows_to_list(rows)

    @staticmethod
    def get_by_id(cat_id):
        db = get_db()
        row = db.execute("SELECT * FROM categories WHERE id=?", (cat_id,)).fetchone()
        return row_to_dict(row)

    @staticmethod
    def get_by_name(name):
        db = get_db()
        row = db.execute("SELECT * FROM categories WHERE name=?", (name,)).fetchone()
        return row_to_dict(row)

    @staticmethod
    def create(name, icon, color, user_id=None):
        db = get_db()
        cur = db.execute(
            "INSERT INTO categories (name, icon, color, user_id) VALUES (?,?,?,?)",
            (name, icon, color, user_id)
        )
        db.commit()
        return CategoryModel.get_by_id(cur.lastrowid)


class TransactionModel:
    @staticmethod
    def _enrich(row_dict):
        if not row_dict:
            return None
        cat = CategoryModel.get_by_id(row_dict['category_id']) if row_dict.get('category_id') else None
        row_dict['category'] = cat or {'name': 'Uncategorized', 'icon': '📦', 'color': '#D3D3D3'}
        try:
            dt = datetime.fromisoformat(row_dict['date'])
            row_dict['date_display'] = dt.strftime('%b %d, %Y')
        except Exception:
            row_dict['date_display'] = row_dict.get('date', '')
        return row_dict

    @staticmethod
    def list_for_user(user_id, page=1, per_page=20, month=None, year=None,
                      txn_type=None, category_id=None):
        db = get_db()
        conditions = ["user_id=?"]
        params = [user_id]

        if year:
            conditions.append("strftime('%Y', date)=?")
            params.append(str(year))
        if month:
            conditions.append("strftime('%m', date)=?")
            params.append(f"{int(month):02d}")
        if txn_type in ('credit', 'debit'):
            conditions.append("type=?")
            params.append(txn_type)
        if category_id:
            conditions.append("category_id=?")
            params.append(category_id)

        where = " AND ".join(conditions)
        total = db.execute(f"SELECT COUNT(*) FROM transactions WHERE {where}", params).fetchone()[0]
        offset = (page - 1) * per_page
        rows = db.execute(
            f"SELECT * FROM transactions WHERE {where} ORDER BY date DESC LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        txns = [TransactionModel._enrich(row_to_dict(r)) for r in rows]
        pages = max(1, (total + per_page - 1) // per_page)
        return txns, total, pages

    @staticmethod
    def get_by_id(txn_id, user_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM transactions WHERE id=? AND user_id=?", (txn_id, user_id)
        ).fetchone()
        return TransactionModel._enrich(row_to_dict(row))

    @staticmethod
    def create(user_id, amount, txn_type, category_id, description, date, source='manual',
               external_id=None, sync_status='synced'):
        db = get_db()
        cur = db.execute(
            """INSERT INTO transactions
               (user_id, amount, type, category_id, description, date, source,
                external_transaction_id, sync_status)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, amount, txn_type, category_id, description, date, source,
             external_id, sync_status)
        )
        db.commit()
        return TransactionModel.get_by_id(cur.lastrowid, user_id)

    @staticmethod
    def update(txn_id, user_id, **fields):
        db = get_db()
        allowed = {'amount', 'type', 'category_id', 'description', 'date'}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return TransactionModel.get_by_id(txn_id, user_id)
        set_clause = ", ".join(f"{k}=?" for k in updates)
        db.execute(
            f"UPDATE transactions SET {set_clause} WHERE id=? AND user_id=?",
            list(updates.values()) + [txn_id, user_id]
        )
        db.commit()
        return TransactionModel.get_by_id(txn_id, user_id)

    @staticmethod
    def delete(txn_id, user_id):
        db = get_db()
        db.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (txn_id, user_id))
        db.commit()

    @staticmethod
    def get_all_for_user(user_id, year=None, month=None):
        db = get_db()
        conditions = ["user_id=?"]
        params = [user_id]
        if year:
            conditions.append("strftime('%Y', date)=?")
            params.append(str(year))
        if month:
            conditions.append("strftime('%m', date)=?")
            params.append(f"{int(month):02d}")
        where = " AND ".join(conditions)
        rows = db.execute(
            f"SELECT * FROM transactions WHERE {where} ORDER BY date DESC", params
        ).fetchall()
        return [TransactionModel._enrich(row_to_dict(r)) for r in rows]

    @staticmethod
    def check_duplicate(user_id, external_id, amount, date_str):
        db = get_db()
        if external_id:
            row = db.execute(
                "SELECT id FROM transactions WHERE user_id=? AND external_transaction_id=?",
                (user_id, external_id)
            ).fetchone()
            if row:
                return True
        day = date_str[:10] if date_str else ''
        if day:
            row = db.execute(
                """SELECT id FROM transactions
                   WHERE user_id=? AND amount=?
                   AND date(date)=? AND source IN ('bank_sync','csv_import')""",
                (user_id, amount, day)
            ).fetchone()
            if row:
                return True
        return False
