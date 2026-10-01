# modules/warehouse.py — модуль «Склад/автопарк» (п. 4.2.3)
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Car, AuditLog
from modules.auth import role_required
from modules.security import sanitize_text, client_ip
from datetime import datetime

warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/warehouse')

ALLOWED_STATUS = frozenset({'in_stock', 'in_transit', 'reserved', 'sold'})


def _safe_image_url(raw: str | None) -> str:
    """Только локальные /static/ пути — без javascript: и внешних URL."""
    u = (raw or '').strip()
    if u.startswith('/static/') and '//' not in u[1:] and len(u) < 255:
        return u
    return '/static/img/car-placeholder.jpg'


@warehouse_bp.route('/')
@login_required
@role_required('admin', 'warehouse', 'manager')
def index():
    status = sanitize_text(request.args.get('status', ''), 30)
    query = Car.query
    if status in ALLOWED_STATUS:
        query = query.filter_by(status=status)
    cars = query.order_by(Car.updated_at.desc()).all()
    stats = {
        'in_stock': Car.query.filter_by(status='in_stock').count(),
        'in_transit': Car.query.filter_by(status='in_transit').count(),
        'reserved': Car.query.filter_by(status='reserved').count(),
        'sold': Car.query.filter_by(status='sold').count(),
    }
    return render_template('warehouse/index.html', cars=cars, stats=stats, current_status=status)


@warehouse_bp.route('/car/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warehouse')
def add_car():
    if request.method == 'POST':
        vin = sanitize_text(request.form.get('vin', ''), 17).upper()
        brand = sanitize_text(request.form.get('brand', ''), 50)
        model = sanitize_text(request.form.get('model', ''), 80)
        year = request.form.get('year', type=int)
        price = request.form.get('price', type=float)
        status = sanitize_text(request.form.get('status', 'in_stock'), 30)
        if status not in ALLOWED_STATUS:
            status = 'in_stock'
        if not vin or len(vin) < 11:
            flash('Укажите корректный VIN', 'danger')
            return redirect(url_for('warehouse.add_car'))
        if not brand or not model:
            flash('Укажите марку и модель', 'danger')
            return redirect(url_for('warehouse.add_car'))
        if year is None or year < 1990 or year > 2100:
            flash('Некорректный год', 'danger')
            return redirect(url_for('warehouse.add_car'))
        if price is None or price < 0 or price > 1e9:
            flash('Некорректная цена', 'danger')
            return redirect(url_for('warehouse.add_car'))
        if Car.query.filter_by(vin=vin).first():
            flash('Автомобиль с таким VIN уже существует', 'danger')
            return redirect(url_for('warehouse.add_car'))

        car = Car(
            vin=vin, brand=brand, model=model, year=year, price=price,
            body_type=sanitize_text(request.form.get('body_type'), 40),
            transmission=sanitize_text(request.form.get('transmission'), 30),
            drive=sanitize_text(request.form.get('drive'), 30),
            engine=sanitize_text(request.form.get('engine'), 50),
            power_hp=request.form.get('power_hp', type=int),
            color_body=sanitize_text(request.form.get('color_body'), 40),
            color_interior=sanitize_text(request.form.get('color_interior'), 40),
            mileage=request.form.get('mileage', type=int) or 0,
            is_new=request.form.get('is_new') == '1',
            status=status,
            description=sanitize_text(request.form.get('description'), 5000),
            published=request.form.get('published') == '1',
            image_url=_safe_image_url(request.form.get('image_url')),
        )
        db.session.add(car)
        db.session.add(AuditLog(
            user_id=current_user.id, action='add_car',
            details=f'Добавлен VIN {car.vin}', ip_address=client_ip(),
        ))
        db.session.commit()
        flash('Автомобиль добавлен на склад', 'success')
        return redirect(url_for('warehouse.index'))
    return render_template('warehouse/car_form.html', car=None)


@warehouse_bp.route('/car/<int:car_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warehouse')
def edit_car(car_id):
    car = Car.query.get_or_404(car_id)
    if request.method == 'POST':
        car.brand = sanitize_text(request.form.get('brand', ''), 50)
        car.model = sanitize_text(request.form.get('model', ''), 80)
        year = request.form.get('year', type=int)
        price = request.form.get('price', type=float)
        if year is not None and 1990 <= year <= 2100:
            car.year = year
        if price is not None and 0 <= price <= 1e9:
            car.price = price
        car.body_type = sanitize_text(request.form.get('body_type'), 40)
        car.transmission = sanitize_text(request.form.get('transmission'), 30)
        car.drive = sanitize_text(request.form.get('drive'), 30)
        car.engine = sanitize_text(request.form.get('engine'), 50)
        car.power_hp = request.form.get('power_hp', type=int)
        car.color_body = sanitize_text(request.form.get('color_body'), 40)
        car.color_interior = sanitize_text(request.form.get('color_interior'), 40)
        car.mileage = request.form.get('mileage', type=int) or 0
        car.is_new = request.form.get('is_new') == '1'
        status = sanitize_text(request.form.get('status', 'in_stock'), 30)
        car.status = status if status in ALLOWED_STATUS else car.status
        car.description = sanitize_text(request.form.get('description'), 5000)
        car.published = request.form.get('published') == '1'
        car.image_url = _safe_image_url(request.form.get('image_url') or car.image_url)
        car.updated_at = datetime.utcnow()
        if car.status == 'sold':
            car.published = False
        db.session.add(AuditLog(
            user_id=current_user.id, action='edit_car',
            details=f'Изменён VIN {car.vin} status={car.status}',
            ip_address=client_ip(),
        ))
        db.session.commit()
        flash('Данные автомобиля обновлены', 'success')
        return redirect(url_for('warehouse.index'))
    return render_template('warehouse/car_form.html', car=car)
