# modules/website.py — публичный веб-сайт + антибот на формах
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, current_app
)
from models import db, Car, Lead, Client, Promo, ServiceBooking
from modules.security import (
    sanitize_text, sanitize_phone, validate_phone, validate_email,
    honeypot_filled, make_form_token, verify_form_token, _client_ip, csrf
)
from datetime import datetime

website_bp = Blueprint('website', __name__)

def _safe_back(fallback_endpoint='website.index'):
    """Редирект только на свой сайт (anti open-redirect)."""
    ref = request.referrer
    if ref and ref.startswith(request.host_url):
        return redirect(ref)
    return redirect(url_for(fallback_endpoint))



def _like_escape(s: str) -> str:
    """Экранирование % и _ для безопасного LIKE."""
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')



def _form_security_ok() -> bool:
    """Общая проверка форм: honeypot + токен времени."""
    if honeypot_filled():
        current_app.logger.warning('Honeypot hit from %s', _client_ip())
        return False
    token = request.form.get('form_token', '')
    if not verify_form_token(token):
        current_app.logger.warning('Bad form token from %s', _client_ip())
        return False
    return True


@website_bp.route('/')
def index():
    cars = Car.query.filter_by(published=True, status='in_stock').limit(6).all()
    promos = Promo.query.filter_by(active=True).limit(3).all()
    return render_template('index.html', cars=cars, promos=promos, form_token=make_form_token())


@website_bp.route('/catalog')
def catalog():
    brand = sanitize_text(request.args.get('brand', ''), 50)
    model = sanitize_text(request.args.get('model', ''), 80)
    body_type = sanitize_text(request.args.get('body_type', ''), 40)
    transmission = sanitize_text(request.args.get('transmission', ''), 30)
    is_new = request.args.get('is_new', '')
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    year_min = request.args.get('year_min', type=int)

    query = Car.query.filter_by(published=True).filter(Car.status.in_(['in_stock', 'reserved']))

    if brand:
        query = query.filter(Car.brand.ilike(f'%{_like_escape(brand)}%', escape='\\'))
    if model:
        query = query.filter(Car.model.ilike(f'%{_like_escape(model)}%', escape='\\'))
    if body_type:
        query = query.filter(Car.body_type == body_type)
    if transmission:
        query = query.filter(Car.transmission == transmission)
    if is_new == '1':
        query = query.filter(Car.is_new.is_(True))
    elif is_new == '0':
        query = query.filter(Car.is_new.is_(False))
    if price_min is not None and 0 <= price_min < 1e9:
        query = query.filter(Car.price >= price_min)
    if price_max is not None and 0 <= price_max < 1e9:
        query = query.filter(Car.price <= price_max)
    if year_min is not None and 1990 <= year_min <= 2100:
        query = query.filter(Car.year >= year_min)

    cars = query.order_by(Car.created_at.desc()).limit(200).all()
    brands = db.session.query(Car.brand).distinct().all()
    body_types = db.session.query(Car.body_type).distinct().all()
    return render_template(
        'catalog.html', cars=cars, brands=brands, body_types=body_types,
        filters=request.args
    )


@website_bp.route('/car/<int:car_id>')
def car_detail(car_id):
    from flask import abort
    car = Car.query.get_or_404(car_id)
    # Публике — только опубликованные и не проданные
    if not car.published or car.status == 'sold':
        abort(404)
    return render_template('car_detail.html', car=car, form_token=make_form_token())


@website_bp.route('/promos')
def promos():
    items = Promo.query.filter_by(active=True).all()
    return render_template('promos.html', promos=items)


@website_bp.route('/trade-in')
def trade_in():
    return render_template('trade_in.html', form_token=make_form_token())


@website_bp.route('/credit')
def credit():
    return render_template('credit.html', form_token=make_form_token())


@website_bp.route('/service')
def service():
    return render_template('service.html', form_token=make_form_token())


@website_bp.route('/about')
def about():
    return render_template('about.html')


@website_bp.route('/contacts')
def contacts():
    return render_template('contacts.html', form_token=make_form_token())


@website_bp.route('/api/credit-calculator', methods=['POST'])
@csrf.exempt
def credit_calculator():
    data = request.get_json(silent=True) or {}
    try:
        price = float(data.get('price', 0))
        down_payment = float(data.get('down_payment', 0))
        term_months = int(data.get('term_months', 36))
        rate_annual = float(data.get('rate', 12.0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректные данные'}), 400

    if not (0 < price < 1e9) or down_payment < 0 or down_payment >= price:
        return jsonify({'error': 'Некорректная цена / взнос'}), 400
    if term_months < 1 or term_months > 120:
        return jsonify({'error': 'Срок 1–120 месяцев'}), 400
    if rate_annual < 0 or rate_annual > 100:
        return jsonify({'error': 'Некорректная ставка'}), 400

    rate = rate_annual / 100 / 12
    loan = price - down_payment
    if rate > 0:
        monthly = loan * (rate * (1 + rate) ** term_months) / ((1 + rate) ** term_months - 1)
    else:
        monthly = loan / term_months
    total = monthly * term_months
    return jsonify({
        'monthly_payment': round(monthly, 2),
        'total_payment': round(total, 2),
        'overpay': round(total - loan, 2),
        'loan_amount': round(loan, 2),
    })


@website_bp.route('/lead', methods=['POST'])
def create_lead():
    if not _form_security_ok():
        flash('Запрос отклонён. Обновите страницу и попробуйте снова.', 'danger')
        return _safe_back('website.index')

    lead_type = sanitize_text(request.form.get('type', 'callback'), 40)
    if lead_type not in ('callback', 'test_drive', 'credit', 'trade_in', 'service'):
        lead_type = 'callback'
    name = sanitize_text(request.form.get('name'), current_app.config.get('MAX_NAME_LEN', 150))
    phone = sanitize_phone(request.form.get('phone'))
    email = sanitize_text(request.form.get('email'), 120)
    message = sanitize_text(request.form.get('message'), current_app.config.get('MAX_MESSAGE_LEN', 2000))
    car_id = request.form.get('car_id', type=int)

    if not name or not validate_phone(phone):
        flash('Укажите корректные имя и телефон', 'danger')
        return _safe_back('website.index')
    if not validate_email(email):
        flash('Некорректный email', 'danger')
        return _safe_back('website.index')

    client = Client.query.filter_by(phone=phone).first()
    if not client:
        client = Client(full_name=name, phone=phone, email=email or None, source='site')
        db.session.add(client)
        db.session.flush()
    else:
        if name and client.full_name != name:
            client.full_name = name
        if email:
            client.email = email

    if car_id:
        car = db.session.get(Car, car_id)
        if not car:
            car_id = None

    lead = Lead(
        client_id=client.id,
        type=lead_type,
        message=message,
        car_id=car_id,
        status='new',
    )
    db.session.add(lead)
    db.session.commit()
    flash('Заявка успешно отправлена! Менеджер свяжется с вами в ближайшее время.', 'success')
    return _safe_back('website.index')


@website_bp.route('/service/book', methods=['POST'])
def book_service():
    if not _form_security_ok():
        flash('Запрос отклонён. Обновите страницу и попробуйте снова.', 'danger')
        return redirect(url_for('website.service'))

    name = sanitize_text(request.form.get('name'), 150)
    phone = sanitize_phone(request.form.get('phone'))
    car_info = sanitize_text(request.form.get('car_info'), 100)
    service_type = sanitize_text(request.form.get('service_type'), 80)
    notes = sanitize_text(request.form.get('notes'), 1000)
    preferred_date = request.form.get('preferred_date')

    if not name or not validate_phone(phone):
        flash('Укажите корректные имя и телефон', 'danger')
        return redirect(url_for('website.service'))

    pref = None
    if preferred_date:
        try:
            pref = datetime.fromisoformat(preferred_date)
        except ValueError:
            pref = None

    booking = ServiceBooking(
        client_name=name,
        phone=phone,
        car_info=car_info,
        service_type=service_type,
        preferred_date=pref,
        notes=notes,
    )
    db.session.add(booking)
    db.session.commit()
    flash('Запись на сервис принята! Мы подтвердим время звонком.', 'success')
    return redirect(url_for('website.service'))
