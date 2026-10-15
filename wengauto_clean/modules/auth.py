# modules/auth.py — аутентификация + защита от brute-force
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, AuditLog
from modules.security import (
    is_login_blocked, register_login_failure, clear_login_failures,
    _client_ip, sanitize_text
)
from functools import wraps
from flask import current_app

auth_bp = Blueprint('auth', __name__)


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles and current_user.role != 'admin':
                flash('Недостаточно прав доступа', 'danger')
                return redirect(url_for('website.index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('crm.dashboard'))

    ip = _client_ip()
    if is_login_blocked(ip):
        flash('Слишком много неудачных попыток. Попробуйте через 30 минут.', 'danger')
        current_app.logger.warning('Login blocked for IP %s', ip)
        return render_template('login.html'), 429

    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''), 80)
        password = request.form.get('password', '') or ''

        # Минимальная задержка против timing-атак (упрощённо)
        user = User.query.filter_by(username=username).first()
        ok = user and user.is_active and user.check_password(password)

        if ok:
            clear_login_failures(ip)
            login_user(user, remember=False)
            log = AuditLog(
                user_id=user.id, action='login',
                details=f'Вход {username}', ip_address=ip
            )
            db.session.add(log)
            db.session.commit()
            flash(f'Добро пожаловать, {user.full_name or user.username}!', 'success')
            next_page = request.args.get('next')
            # Только относительные URL
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('crm.dashboard'))

        register_login_failure(ip)
        flash('Неверный логин или пароль', 'danger')
        current_app.logger.info('Failed login for %s from %s', username, ip)

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log = AuditLog(
        user_id=current_user.id, action='logout',
        details='Выход', ip_address=_client_ip()
    )
    db.session.add(log)
    db.session.commit()
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('website.index'))
