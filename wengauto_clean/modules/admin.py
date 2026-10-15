# modules/admin.py — администрирование (п. 4.2.6)
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Promo, AuditLog, ServiceBooking
from modules.auth import role_required
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

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
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '')
    role = request.form.get('role', 'manager')
    if User.query.filter_by(username=username).first():
        flash('Пользователь с таким логином уже существует', 'danger')
        return redirect(url_for('admin.index'))
    user = User(username=username, email=email, full_name=full_name, role=role)
    user.set_password(password)
    db.session.add(user)
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
    promo = Promo(
        title=request.form.get('title', '').strip(),
        description=request.form.get('description', ''),
        discount_percent=request.form.get('discount_percent', type=int) or 0,
        active=True
    )
    db.session.add(promo)
    db.session.commit()
    flash('Акция добавлена', 'success')
    return redirect(url_for('admin.promos'))

@admin_bp.route('/analytics')
@login_required
@role_required('admin', 'manager')
def analytics():
    """Подсистема «Аналитика и отчётность» (п. 4.2.5)"""
    from models import Lead, Deal, Car, Client
    from sqlalchemy import func
    sales_by_brand = db.session.query(Car.brand, func.count(Car.id)).filter(Car.status == 'sold').group_by(Car.brand).all()
    leads_by_type = db.session.query(Lead.type, func.count(Lead.id)).group_by(Lead.type).all()
    deals_by_stage = db.session.query(Deal.stage, func.count(Deal.id)).group_by(Deal.stage).all()
    total_revenue = db.session.query(func.sum(Deal.amount)).filter(Deal.stage == 'sold').scalar() or 0
    return render_template('admin/analytics.html',
                           sales_by_brand=sales_by_brand,
                           leads_by_type=leads_by_type,
                           deals_by_stage=deals_by_stage,
                           total_revenue=total_revenue,
                           clients_count=Client.query.count(),
                           cars_in_stock=Car.query.filter_by(status='in_stock').count())
