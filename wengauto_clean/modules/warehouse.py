# modules/warehouse.py — модуль «Склад/автопарк» (п. 4.2.3)
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Car, AuditLog
from modules.auth import role_required
from datetime import datetime

warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/warehouse')

@warehouse_bp.route('/')
@login_required
@role_required('admin', 'warehouse', 'manager')
def index():
    status = request.args.get('status', '')
    query = Car.query
    if status:
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
        car = Car(
            vin=request.form.get('vin', '').strip().upper(),
            brand=request.form.get('brand', '').strip(),
            model=request.form.get('model', '').strip(),
            year=request.form.get('year', type=int),
            price=request.form.get('price', type=float),
            body_type=request.form.get('body_type'),
            transmission=request.form.get('transmission'),
            drive=request.form.get('drive'),
            engine=request.form.get('engine'),
            power_hp=request.form.get('power_hp', type=int),
            color_body=request.form.get('color_body'),
            color_interior=request.form.get('color_interior'),
            mileage=request.form.get('mileage', type=int) or 0,
            is_new=request.form.get('is_new') == '1',
            status=request.form.get('status', 'in_stock'),
            description=request.form.get('description'),
            published=request.form.get('published') == '1',
            image_url=request.form.get('image_url') or '/static/img/car-placeholder.jpg'
        )
        if Car.query.filter_by(vin=car.vin).first():
            flash('Автомобиль с таким VIN уже существует', 'danger')
            return redirect(url_for('warehouse.add_car'))
        db.session.add(car)
        log = AuditLog(user_id=current_user.id, action='add_car', details=f'Добавлен VIN {car.vin}')
        db.session.add(log)
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
        car.brand = request.form.get('brand', '').strip()
        car.model = request.form.get('model', '').strip()
        car.year = request.form.get('year', type=int)
        car.price = request.form.get('price', type=float)
        car.body_type = request.form.get('body_type')
        car.transmission = request.form.get('transmission')
        car.drive = request.form.get('drive')
        car.engine = request.form.get('engine')
        car.power_hp = request.form.get('power_hp', type=int)
        car.color_body = request.form.get('color_body')
        car.color_interior = request.form.get('color_interior')
        car.mileage = request.form.get('mileage', type=int) or 0
        car.is_new = request.form.get('is_new') == '1'
        car.status = request.form.get('status', 'in_stock')
        car.description = request.form.get('description')
        car.published = request.form.get('published') == '1'
        car.image_url = request.form.get('image_url') or car.image_url
        car.updated_at = datetime.utcnow()
        # Синхронизация с каталогом сайта: при продаже снимаем с публикации
        if car.status == 'sold':
            car.published = False
        db.session.commit()
        flash('Данные автомобиля обновлены', 'success')
        return redirect(url_for('warehouse.index'))
    return render_template('warehouse/car_form.html', car=car)
