# modules/crm.py — модуль CRM (п. 4.2.2)
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db, Lead, Client, Deal, Car, AuditLog
from modules.auth import role_required
from modules.security import sanitize_text, client_ip
from datetime import datetime

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')

ALLOWED_LEAD_STATUS = frozenset({'new', 'in_progress', 'done', 'rejected', 'converted'})
ALLOWED_DEAL_STAGE = frozenset({'new', 'negotiation', 'contract', 'sold', 'lost'})


@crm_bp.route('/')
@login_required
@role_required('admin', 'manager', 'marketing')
def dashboard():
    new_leads = Lead.query.filter_by(status='new').order_by(Lead.created_at.desc()).limit(10).all()
    deals_count = Deal.query.count()
    clients_count = Client.query.count()
    leads_count = Lead.query.count()
    stages = db.session.query(Deal.stage, db.func.count(Deal.id)).group_by(Deal.stage).all()
    return render_template(
        'crm/dashboard.html',
        new_leads=new_leads,
        deals_count=deals_count,
        clients_count=clients_count,
        leads_count=leads_count,
        stages=stages,
    )


@crm_bp.route('/leads')
@login_required
@role_required('admin', 'manager', 'marketing')
def leads():
    status = sanitize_text(request.args.get('status', ''), 30)
    query = Lead.query
    if status in ALLOWED_LEAD_STATUS:
        query = query.filter_by(status=status)
    elif status:
        status = ''
    items = query.order_by(Lead.created_at.desc()).limit(500).all()
    return render_template('crm/leads.html', leads=items, current_status=status)


@crm_bp.route('/leads/<int:lead_id>/update', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def update_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    new_status = sanitize_text(request.form.get('status', ''), 30)
    if new_status in ALLOWED_LEAD_STATUS:
        lead.status = new_status
        lead.manager_id = current_user.id
        db.session.add(AuditLog(
            user_id=current_user.id, action='update_lead',
            details=f'lead#{lead_id} -> {new_status}', ip_address=client_ip(),
        ))
        db.session.commit()
        flash('Статус заявки обновлён', 'success')
    else:
        flash('Недопустимый статус', 'danger')
    return redirect(url_for('crm.leads'))


@crm_bp.route('/clients')
@login_required
@role_required('admin', 'manager', 'marketing')
def clients():
    items = Client.query.order_by(Client.created_at.desc()).limit(500).all()
    return render_template('crm/clients.html', clients=items)


@crm_bp.route('/deals')
@login_required
@role_required('admin', 'manager')
def deals():
    items = Deal.query.order_by(Deal.updated_at.desc()).limit(500).all()
    return render_template('crm/deals.html', deals=items)


@crm_bp.route('/deals/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def create_deal():
    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        car_id = request.form.get('car_id', type=int)
        stage = sanitize_text(request.form.get('stage', 'new'), 30)
        if stage not in ALLOWED_DEAL_STAGE:
            stage = 'new'
        amount = request.form.get('amount', type=float)
        notes = sanitize_text(request.form.get('notes', ''), 2000)

        if not client_id or not Client.query.get(client_id):
            flash('Выберите существующего клиента', 'danger')
            return redirect(url_for('crm.create_deal'))
        if amount is not None and (amount < 0 or amount > 1e9):
            flash('Некорректная сумма', 'danger')
            return redirect(url_for('crm.create_deal'))
        if car_id and not Car.query.get(car_id):
            car_id = None

        deal = Deal(
            client_id=client_id,
            car_id=car_id,
            stage=stage,
            amount=amount,
            manager_id=current_user.id,
            notes=notes,
        )
        db.session.add(deal)
        if car_id and stage in ('contract', 'sold'):
            car = Car.query.get(car_id)
            if car:
                car.status = 'sold' if stage == 'sold' else 'reserved'
                car.published = stage != 'sold'
        db.session.add(AuditLog(
            user_id=current_user.id, action='create_deal',
            details=f'client={client_id} car={car_id} stage={stage}',
            ip_address=client_ip(),
        ))
        db.session.commit()
        flash('Сделка создана', 'success')
        return redirect(url_for('crm.deals'))

    clients_list = Client.query.order_by(Client.full_name).limit(500).all()
    cars = Car.query.filter(Car.status.in_(['in_stock', 'reserved'])).limit(500).all()
    return render_template('crm/deal_form.html', clients=clients_list, cars=cars)


@crm_bp.route('/deals/<int:deal_id>/stage', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def update_deal_stage(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    new_stage = sanitize_text(request.form.get('stage', ''), 30)
    if new_stage not in ALLOWED_DEAL_STAGE:
        flash('Недопустимый этап сделки', 'danger')
        return redirect(url_for('crm.deals'))

    deal.stage = new_stage
    deal.updated_at = datetime.utcnow()
    if deal.car_id and new_stage == 'sold':
        car = Car.query.get(deal.car_id)
        if car:
            car.status = 'sold'
            car.published = False
    db.session.add(AuditLog(
        user_id=current_user.id, action='update_deal_stage',
        details=f'deal#{deal_id} -> {new_stage}', ip_address=client_ip(),
    ))
    db.session.commit()
    flash('Этап сделки обновлён', 'success')
    return redirect(url_for('crm.deals'))
