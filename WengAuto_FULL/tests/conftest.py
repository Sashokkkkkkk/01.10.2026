import os
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.pop('SQLITE_PATH', None)

from app import create_app
from models import db, User, Car


@pytest.fixture()
def app():
    application = create_app()
    application.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
    with application.app_context():
        db.create_all()
        admin = User(username='admin', email='admin@test.local', full_name='Admin', role='admin')
        admin.set_password('AdminPass123!')
        manager = User(username='manager', email='mgr@test.local', full_name='Manager', role='manager')
        manager.set_password('ManagerPass123!')
        warehouse = User(username='warehouse', email='wh@test.local', full_name='WH', role='warehouse')
        warehouse.set_password('Warehouse1!')
        car_pub = Car(
            vin='TESTVIN000000001', brand='Toyota', model='Camry', year=2024,
            price=1000000, status='in_stock', published=True,
        )
        car_hidden = Car(
            vin='TESTVIN000000002', brand='BMW', model='X5', year=2023,
            price=2000000, status='sold', published=False,
        )
        db.session.add_all([admin, manager, warehouse, car_pub, car_hidden])
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def browser_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/json',
        'Accept-Language': 'ru-RU,ru;q=0.9',
    }


@pytest.fixture()
def login(client, browser_headers):
    def _login(username, password):
        return client.post(
            '/login',
            data={'username': username, 'password': password},
            headers=browser_headers,
            follow_redirects=False,
        )
    return _login
