from flask import Flask
import os

def create_app():
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod-xyz789')
    app.config['DATABASE'] = os.environ.get(
        'DATABASE',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'expenses.db')
    )
    app.config['VAPID_PUBLIC_KEY'] = os.environ.get('VAPID_PUBLIC_KEY', '')
    app.config['VAPID_PRIVATE_KEY'] = os.environ.get('VAPID_PRIVATE_KEY', '')

    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)

    from .db import init_db
    from .routes import main
    app.register_blueprint(main)

    with app.app_context():
        init_db(app.config['DATABASE'])

    return app
