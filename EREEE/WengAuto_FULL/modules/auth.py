# modules/auth.py — аутентификация + защита от brute-force
import time
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from models import db, User, AuditLog
from modules.security import (
    is_login_blocked, register_login_failure, clear_login_failures,
    client_ip, sanitize_text,
)

auth_bp = Blueprint('auth', __name__)

# Фиктивный хеш для выравнивания времени, если пользователь не найден (anti timing)
_DUMMY_HASH = (
    'scrypt:32768:8:1$dummy$0000000000000000000000000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000'
)

# Разрешённые внутренние next= после логина
_ALLOWED_NEXT_PREFIXES = ('/crm', '/admin', '/warehouse', '/login')


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.path))
            if not current_user.is_active:
                logout_user()
                flash('Учётная запись отключена', 'danger')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles and current_user.role != 'admin':
                current_app.logger.warning(
                    'Access denied user=%s role=%s path=%s',
                    current_user.username, current_user.role, request.path,
                )
                flash('Недостаточно прав доступа', 'danger')
                return redirect(url_for('website.index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def _safe_next(next_page: str | None) -> str | None:
    if not next_page:
        return None
    if not next_page.startswith('/') or next_page.startswith('//') or '\\' in next_page:
        return None
    if any(next_page == p or next_page.startswith(p + '/') for p in _ALLOWED_NEXT_PREFIXES):
        return next_page
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('crm.dashboard'))

    ip = client_ip()
    if is_login_blocked(ip):
        flash('Слишком много неудачных попыток. Попробуйте через 30 минут.', 'danger')
        current_app.logger.warning('Login blocked for IP %s', ip)
        return render_template('login.html'), 429

    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''), 80)
        password = request.form.get('password', '') or ''
        if len(password) > 256:
            password = password[:256]

        user = User.query.filter_by(username=username).first()
        # Постоянное время проверки пароля (и для несуществующего логина)
        if user and user.is_active:
            ok = user.check_password(password)
        else:
            check_password_hash(_DUMMY_HASH, password or 'x')
            ok = False

        if ok:
            clear_login_failures(ip)
            session.clear()  # смена session id после логина
            login_user(user, remember=False)
            session.permanent = True
            db.session.add(AuditLog(
                user_id=user.id, action='login',
                details=f'Вход {username}', ip_address=ip,
            ))
            db.session.commit()
            flash(f'Добро пожаловать, {user.full_name or user.username}!', 'success')
            nxt = _safe_next(request.args.get('next'))
            if nxt:
                return redirect(nxt)
            return redirect(url_for('crm.dashboard'))

        register_login_failure(ip)
        time.sleep(0.45)
        flash('Неверный логин или пароль', 'danger')
        current_app.logger.info('Failed login for %s from %s', username, ip)

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    db.session.add(AuditLog(
        user_id=current_user.id, action='logout',
        details='Выход', ip_address=client_ip(),
    ))
    db.session.commit()
    logout_user()
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('website.index'))
