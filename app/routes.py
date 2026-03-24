import csv, io, json
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from flask import (Blueprint, render_template, request, jsonify,
                   session, redirect, url_for, current_app, Response, g)

from .db import get_db, close_db
from .models import UserModel, CategoryModel, TransactionModel
from .services.bank_sync import get_provider, CSVImportProvider, auto_categorize

main = Blueprint('main', __name__)

# Register teardown
@main.teardown_app_request
def teardown_db(exc):
    close_db(exc)

# ─── Auth Decorator ───────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/transactions') or request.path.startswith('/dashboard') or request.path.startswith('/categories') or request.path.startswith('/export') or request.path.startswith('/bank') or request.path.startswith('/upload') or request.path.startswith('/push') or request.path.startswith('/user'):
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('main.login_page'))
        g.user = UserModel.get_by_id(session['user_id'])
        if not g.user:
            session.clear()
            return redirect(url_for('main.login_page'))
        return f(*args, **kwargs)
    return decorated

# ─── Pages ────────────────────────────────────────────────

@main.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard_page'))
    return redirect(url_for('main.login_page'))

@main.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard_page'))
    return render_template('auth.html')

@main.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('dashboard.html', user=g.user)

@main.route('/transactions-page')
@login_required
def transactions_page():
    return render_template('transactions.html', user=g.user)

@main.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html', user=g.user)

# ─── Auth API ─────────────────────────────────────────────

@main.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if UserModel.get_by_email(email):
        return jsonify({'error': 'Email already registered'}), 409
    if UserModel.get_by_username(username):
        return jsonify({'error': 'Username already taken'}), 409

    user = UserModel.create(username, email, password)
    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'success': True, 'user': UserModel.to_public(user)}), 201


@main.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = UserModel.get_by_email(email)
    if not user or not UserModel.check_password(user, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'success': True, 'user': UserModel.to_public(user)})


@main.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@main.route('/user/me', methods=['GET'])
@login_required
def get_me():
    return jsonify(UserModel.to_public(g.user))

# ─── Categories ───────────────────────────────────────────

@main.route('/categories', methods=['GET'])
@login_required
def get_categories():
    cats = CategoryModel.list_for_user(g.user['id'])
    return jsonify(cats)


@main.route('/categories', methods=['POST'])
@login_required
def create_category():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    if CategoryModel.get_by_name(name):
        return jsonify({'error': 'Category already exists'}), 409
    cat = CategoryModel.create(name, data.get('icon', '📦'),
                                data.get('color', '#D3D3D3'), g.user['id'])
    return jsonify(cat), 201

# ─── Transactions ─────────────────────────────────────────

@main.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    txn_type = request.args.get('type')
    category_id = request.args.get('category_id', type=int)

    txns, total, pages = TransactionModel.list_for_user(
        g.user['id'], page=page, per_page=per_page,
        month=month, year=year, txn_type=txn_type, category_id=category_id
    )
    return jsonify({'transactions': txns, 'total': total, 'pages': pages, 'current_page': page})


@main.route('/transactions', methods=['POST'])
@login_required
def create_transaction():
    data = request.get_json() or {}
    try:
        amount = float(data.get('amount', 0))
        if amount <= 0: raise ValueError()
    except (ValueError, TypeError):
        return jsonify({'error': 'Valid positive amount required'}), 400

    txn_type = data.get('type')
    if txn_type not in ('credit', 'debit'):
        return jsonify({'error': 'Type must be credit or debit'}), 400

    date_str = data.get('date')
    try:
        txn_date = datetime.strptime(date_str, '%Y-%m-%d').isoformat() if date_str else datetime.utcnow().isoformat()
    except ValueError:
        txn_date = datetime.utcnow().isoformat()

    txn = TransactionModel.create(
        user_id=g.user['id'], amount=amount, txn_type=txn_type,
        category_id=data.get('category_id') or None,
        description=data.get('description', ''), date=txn_date
    )
    return jsonify(txn), 201


@main.route('/transactions/<int:txn_id>', methods=['PUT'])
@login_required
def update_transaction(txn_id):
    existing = TransactionModel.get_by_id(txn_id, g.user['id'])
    if not existing:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json() or {}
    fields = {}
    if 'amount' in data:
        try: fields['amount'] = float(data['amount'])
        except: return jsonify({'error': 'Invalid amount'}), 400
    if 'type' in data and data['type'] in ('credit', 'debit'):
        fields['type'] = data['type']
    if 'category_id' in data:
        fields['category_id'] = data['category_id'] or None
    if 'description' in data:
        fields['description'] = data['description']
    if 'date' in data:
        try: fields['date'] = datetime.strptime(data['date'], '%Y-%m-%d').isoformat()
        except: pass

    txn = TransactionModel.update(txn_id, g.user['id'], **fields)
    return jsonify(txn)


@main.route('/transactions/<int:txn_id>', methods=['DELETE'])
@login_required
def delete_transaction(txn_id):
    existing = TransactionModel.get_by_id(txn_id, g.user['id'])
    if not existing:
        return jsonify({'error': 'Not found'}), 404
    TransactionModel.delete(txn_id, g.user['id'])
    return jsonify({'success': True})

# ─── Dashboard ────────────────────────────────────────────

@main.route('/dashboard/data', methods=['GET'])
@login_required
def dashboard_data():
    month = request.args.get('month', type=int)
    year = request.args.get('year', datetime.utcnow().year, type=int)

    txns = TransactionModel.get_all_for_user(g.user['id'], year=year, month=month)

    total_credit = sum(t['amount'] for t in txns if t['type'] == 'credit')
    total_debit  = sum(t['amount'] for t in txns if t['type'] == 'debit')
    balance = total_credit - total_debit

    # Category breakdown
    cat_map = defaultdict(lambda: {'amount': 0, 'color': '#D3D3D3', 'icon': '📦'})
    for t in txns:
        if t['type'] == 'debit' and t.get('category'):
            cn = t['category']['name']
            cat_map[cn]['amount'] += t['amount']
            cat_map[cn]['color'] = t['category']['color']
            cat_map[cn]['icon'] = t['category']['icon']

    category_data = [
        {'name': k, 'amount': round(v['amount'], 2), 'color': v['color'], 'icon': v['icon']}
        for k, v in sorted(cat_map.items(), key=lambda x: -x[1]['amount'])
    ]

    # Daily data
    daily_map = defaultdict(lambda: {'credit': 0, 'debit': 0})
    for t in txns:
        day = t['date'][:10]
        daily_map[day][t['type']] += t['amount']

    # Fill gaps
    if daily_map:
        all_days = sorted(daily_map.keys())
        start = datetime.fromisoformat(all_days[0])
        end = datetime.fromisoformat(all_days[-1])
        cur = start
        while cur <= end:
            _ = daily_map[cur.strftime('%Y-%m-%d')]
            cur += timedelta(days=1)

    daily_data = [
        {'date': d, 'credit': round(v['credit'], 2), 'debit': round(v['debit'], 2)}
        for d, v in sorted(daily_map.items())
    ]

    # Monthly
    monthly = []
    for m in range(1, 13):
        m_txns = TransactionModel.get_all_for_user(g.user['id'], year=year, month=m)
        monthly.append({
            'month': m,
            'label': datetime(year, m, 1).strftime('%b'),
            'credit': round(sum(t['amount'] for t in m_txns if t['type'] == 'credit'), 2),
            'debit':  round(sum(t['amount'] for t in m_txns if t['type'] == 'debit'), 2),
        })

    # Recent
    recent_txns, _, _ = TransactionModel.list_for_user(g.user['id'], page=1, per_page=5)

    return jsonify({
        'summary': {
            'total_credit': round(total_credit, 2),
            'total_debit':  round(total_debit, 2),
            'balance':      round(balance, 2),
            'transaction_count': len(txns),
        },
        'category_data': category_data,
        'daily_data': daily_data,
        'monthly_data': monthly,
        'recent_transactions': recent_txns,
    })

# ─── CSV Export ───────────────────────────────────────────

@main.route('/export/csv', methods=['GET'])
@login_required
def export_csv():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    txns = TransactionModel.get_all_for_user(g.user['id'], year=year, month=month)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Type', 'Amount', 'Category', 'Description', 'Source'])
    for t in txns:
        writer.writerow([
            t['id'], t['date'], t['type'], t['amount'],
            t['category']['name'] if t.get('category') else 'Uncategorized',
            t.get('description', ''), t.get('source', 'manual')
        ])

    filename = f"transactions_{year or 'all'}{'_' + str(month) if month else ''}.csv"
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})

# ─── Bank Sync ────────────────────────────────────────────

@main.route('/bank/sync', methods=['POST'])
@login_required
def bank_sync():
    data = request.get_json() or {}
    provider = get_provider(data.get('provider', 'mock'))
    days = int(data.get('days', 30))
    raw_txns = provider.fetch_transactions(g.user['id'], days)
    balance_info = provider.fetch_balance(g.user['id'])

    imported = duplicates = 0
    for raw in raw_txns:
        date_str = raw['date'].isoformat() if hasattr(raw['date'], 'isoformat') else str(raw['date'])
        if TransactionModel.check_duplicate(g.user['id'], raw.get('external_id'), raw['amount'], date_str):
            duplicates += 1
            continue

        cat_name = raw.get('category_hint') or auto_categorize(raw.get('description', ''))
        cat = CategoryModel.get_by_name(cat_name) if cat_name else None

        TransactionModel.create(
            user_id=g.user['id'], amount=raw['amount'], txn_type=raw['type'],
            category_id=cat['id'] if cat else None,
            description=raw.get('description', ''), date=date_str,
            source='bank_sync', external_id=raw.get('external_id')
        )
        imported += 1

    return jsonify({'success': True, 'imported': imported,
                    'duplicates_skipped': duplicates, 'bank_balance': balance_info})


@main.route('/upload/csv', methods=['POST'])
@login_required
def upload_csv():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        return jsonify({'error': 'Valid CSV file required'}), 400

    content = file.read().decode('utf-8', errors='replace')
    parser = CSVImportProvider()
    raw_txns = parser.parse(content)

    imported = duplicates = 0
    for raw in raw_txns:
        date_str = raw['date'].isoformat() if hasattr(raw['date'], 'isoformat') else str(raw['date'])
        if TransactionModel.check_duplicate(g.user['id'], raw.get('external_id'), raw['amount'], date_str):
            duplicates += 1
            continue

        cat_name = auto_categorize(raw.get('description', ''))
        cat = CategoryModel.get_by_name(cat_name) if cat_name else None

        TransactionModel.create(
            user_id=g.user['id'], amount=raw['amount'], txn_type=raw['type'],
            category_id=cat['id'] if cat else None,
            description=raw.get('description', ''), date=date_str,
            source='csv_import', external_id=raw.get('external_id')
        )
        imported += 1

    return jsonify({'success': True, 'imported': imported, 'duplicates_skipped': duplicates})

# ─── Push Notifications ───────────────────────────────────

@main.route('/push/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    data = request.get_json() or {}
    UserModel.update_push(g.user['id'], json.dumps(data), True)
    return jsonify({'success': True})


@main.route('/push/unsubscribe', methods=['POST'])
@login_required
def push_unsubscribe():
    UserModel.update_push(g.user['id'], None, False)
    return jsonify({'success': True})


@main.route('/push/vapid-public-key', methods=['GET'])
@login_required
def vapid_public_key():
    return jsonify({'public_key': current_app.config.get('VAPID_PUBLIC_KEY', '')})
