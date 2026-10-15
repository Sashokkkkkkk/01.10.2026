# models.py — модели данных АИС «WengAuto» (п. 4.3.2 Информационное обеспечение)
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Пользователи системы (роли из Приложения А)"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(50), nullable=False, default='manager')  # admin, manager, warehouse, service, marketing, client
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Car(db.Model):
    """Автомобили склада / каталога (подсистема «Склад/автопарк» п. 4.2.3)"""
    __tablename__ = 'cars'
    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), unique=True, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    body_type = db.Column(db.String(40))  # седан, кроссовер, хэтчбек...
    transmission = db.Column(db.String(30))  # АКПП, МКПП
    drive = db.Column(db.String(30))  # передний, задний, полный
    engine = db.Column(db.String(50))
    power_hp = db.Column(db.Integer)
    color_body = db.Column(db.String(40))
    color_interior = db.Column(db.String(40))
    mileage = db.Column(db.Integer, default=0)
    is_new = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(30), default='in_stock')  # in_stock, in_transit, reserved, sold
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255), default='/static/img/car-placeholder.jpg')
    published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Локальные фото без интернета (даже если в БД старый URL Unsplash)
    _BRAND_IMG = {
        'Toyota': '/static/img/camry.jpg',
        'BMW': '/static/img/bmw.jpg',
        'Hyundai': '/static/img/tucson.jpg',
        'Kia': '/static/img/sportage.jpg',
        'Mercedes-Benz': '/static/img/mercedes.jpg',
        'Volkswagen': '/static/img/tiguan.jpg',
        'Lada': '/static/img/vesta.jpg',
        'Audi': '/static/img/audi.jpg',
        'Porsche': '/static/img/cayenne.jpg',
        'Tesla': '/static/img/tesla.jpg',
        'Lexus': '/static/img/lexus.jpg',
        'Skoda': '/static/img/octavia.jpg',
    }

    @property
    def display_image(self):
        # Всегда локальный файл по марке — без интернета и без старых URL из БД
        return self._BRAND_IMG.get(self.brand, '/static/img/car-placeholder.jpg')

class Client(db.Model):
    """Клиенты CRM (п. 4.2.2)"""
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    source = db.Column(db.String(50))  # site, call, messenger, social
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    leads = db.relationship('Lead', backref='client', lazy=True)
    deals = db.relationship('Deal', backref='client', lazy=True)

class Lead(db.Model):
    """Лиды / заявки"""
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    type = db.Column(db.String(40))  # callback, test_drive, credit, trade_in, service
    status = db.Column(db.String(30), default='new')  # new, in_progress, completed, rejected
    message = db.Column(db.Text)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    car = db.relationship('Car', backref='leads')

class Deal(db.Model):
    """Сделки (воронка продаж)"""
    __tablename__ = 'deals'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'))
    stage = db.Column(db.String(40), default='lead')  # lead, consultation, test_drive, agreement, contract, sold
    amount = db.Column(db.Float)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    car = db.relationship('Car', backref='deals')

class ServiceBooking(db.Model):
    """Записи на сервис (п. 4.2.4)"""
    __tablename__ = 'service_bookings'
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    car_info = db.Column(db.String(100))
    service_type = db.Column(db.String(80))
    preferred_date = db.Column(db.DateTime)
    status = db.Column(db.String(30), default='pending')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Promo(db.Model):
    """Акции и спецпредложения"""
    __tablename__ = 'promos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    discount_percent = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    valid_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    """Журнал аудита (п. 4.1.5)"""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
