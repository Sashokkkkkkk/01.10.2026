# modules/admin.py — администрирование (п. 4.2.6)
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Promo, AuditLog, ServiceBooking
from modules.auth import role_required
from modules.security import sanitize_text, validate_email, client_ip

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_ROLES = frozenset({'admin', 'manager', 'warehouse', 'service', 'marketing'})


@admin_bp.route('/')
@login_required
@role_required('admin')
def index():
    users = User.query.all()
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()
    bookings = ServiceBooking.query.order_by(ServiceBooking.created_at.desc()).limit(20).all()
    return render_template('admin/index.html', users=users, logs=logs, bookings=bookings)


@admin_bp.route('/users/add', methods=['POST'])
@login_required
@role_required('admin')
def add_user():
    username = sanitize_text(request.form.get('username', ''), 80)
    email = sanitize_text(request.form.get('email', ''), 120)
    password = request.form.get('password', '') or ''
    full_name = sanitize_text(request.form.get('full_name', ''), 150)
    role = sanitize_text(request.form.get('role', 'manager'), 30)

    if not username or len(username) < 3:
        flash('Логин не менее 3 символов', 'danger')
        return redirect(url_for('admin.index'))
    if not validate_email(email) or not email:
        flash('Укажите корректный email', 'danger')
        return redirect(url_for('admin.index'))
    if len(password) < 10:
        flash('Пароль не менее 10 символов', 'danger')
        return redirect(url_for('admin.index'))
    if role not in ALLOWED_ROLES:
        flash('Недопустимая роль', 'danger')
        return redirect(url_for('admin.index'))
    if User.query.filter_by(username=username).first():
        flash('Пользователь с таким логином уже существует', 'danger')
        return redirect(url_for('admin.index'))
    if User.query.filter_by(email=email).first():
        flash('Email уже занят', 'danger')
        return redirect(url_for('admin.index'))

    user = User(username=username, email=email, full_name=full_name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.add(AuditLog(
        user_id=current_user.id, action='add_user',
        details=f'Создан пользователь {username} роль={role}',
        ip_address=client_ip(),
    ))
    db.session.commit()
    flash('Пользователь создан', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/promos')
@login_required
@role_required('admin', 'marketing')
def promos():
    items = Promo.query.order_by(Promo.created_at.desc()).all()
    return render_template('admin/promos.html', promos=items)


@admin_bp.route('/promos/add', methods=['POST'])
@login_required
@role_required('admin', 'marketing')
def add_promo():
    title = sanitize_text(request.form.get('title', ''), 200)
    description = sanitize_text(request.form.get('description', ''), 2000)
    discount = request.form.get('discount_percent', type=int) or 0
    if not title:
        flash('Укажите название акции', 'danger')
        return redirect(url_for('admin.promos'))
    if discount < 0 or discount > 90:
        flash('Скидка 0–90%', 'danger')
        return redirect(url_for('admin.promos'))
    promo = Promo(title=title, description=description, discount_percent=discount, active=True)
    db.session.add(promo)
    db.session.commit()
    flash('Акция добавлена', 'success')
    return redirect(url_for('admin.promos'))


@admin_bp.route('/analytics')
@login_required
@role_required('admin', 'manager')
def analytics():
    from models import Lead, Deal, Car, Client
    from sqlalchemy import func
    sales_by_brand = db.session.query(Car.brand, func.count(Car.id)).filter(Car.status == 'sold').group_by(Car.brand).all()
    leads_by_type = db.session.query(Lead.type, func.count(Lead.id)).group_by(Lead.type).all()
    deals_by_stage = db.session.query(Deal.stage, func.count(Deal.id)).group_by(Deal.stage).all()
    total_revenue = db.session.query(func.sum(Deal.amount)).filter(Deal.stage == 'sold').scalar() or 0
    return render_template(
        'admin/analytics.html',
        sales_by_brand=sales_by_brand,
        leads_by_type=leads_by_type,
        deals_by_stage=deals_by_stage,
        total_revenue=total_revenue,
        clients_count=Client.query.count(),
        cars_in_stock=Car.query.filter_by(status='in_stock').count(),
    )
