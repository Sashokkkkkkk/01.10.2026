# modules/security.py — защита от ботов, AI-скраперов, злоупотреблений
"""
Легальный hardening:
- Rate limiting (Flask-Limiter)
- Расширенная блокировка AI/scraper User-Agents
- Honeypot-поля
- Form tokens (HMAC)
- Secure HTTP headers + CSP
- Brute-force защита логина
- Эвристики «не похож на браузер»
"""
from __future__ import annotations

import hashlib
import hmac
import re
import time
from collections import defaultdict
from threading import Lock

from flask import request, abort, current_app
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

_login_failures: dict[str, list[float]] = defaultdict(list)
_lock = Lock()
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SEC = 900
LOGIN_BLOCK_SEC = 1800


def client_ip() -> str:
    """Публичное имя (без «_» — чтобы не ругался линтер)."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()[:45]
    return (request.remote_addr or '0.0.0.0')[:45]


# Обратная совместимость
_client_ip = client_ip


def is_blocked_user_agent(ua: str) -> bool:
    if not ua or len(ua) < 10:
        return True
    low = ua.lower()
    allowed = current_app.config.get('ALLOWED_BOT_UA', [])
    if any(a in low for a in allowed):
        return False
    blocked = current_app.config.get('BLOCKED_UA_SUBSTRINGS', [])
    return any(b in low for b in blocked)


def looks_like_scraper() -> bool:
    """Эвристика: запрос не похож на обычный браузер."""
    ua = request.headers.get('User-Agent', '')
    if is_blocked_user_agent(ua):
        return True

    # Пустые ключевые заголовки у скриптов
    if not ua:
        return True

    accept = request.headers.get('Accept', '')
    # Многие AI-боты/curl не шлют Accept HTML
    if request.method == 'GET' and request.path not in ('/robots.txt', '/sitemap.xml'):
        if not accept:
            return True
        # Явный API-клиент без HTML
        if 'text/html' not in accept and '*/*' not in accept and 'application/json' in accept:
            if not request.path.startswith('/api/'):
                return True

    # Нет Accept-Language — частый признак автоматизации
    if request.method == 'GET' and not request.path.startswith('/api/'):
        if not request.headers.get('Accept-Language') and 'mozilla' not in ua.lower():
            return True

    return False


def register_login_failure(ip: str) -> None:
    now = time.time()
    with _lock:
        fails = _login_failures[ip]
        fails.append(now)
        _login_failures[ip] = [t for t in fails if now - t < LOGIN_WINDOW_SEC]


def clear_login_failures(ip: str) -> None:
    with _lock:
        _login_failures.pop(ip, None)


def is_login_blocked(ip: str) -> bool:
    now = time.time()
    with _lock:
        fails = [t for t in _login_failures.get(ip, []) if now - t < LOGIN_WINDOW_SEC]
        _login_failures[ip] = fails
        if len(fails) >= LOGIN_MAX_ATTEMPTS:
            last = max(fails) if fails else 0
            if now - last < LOGIN_BLOCK_SEC:
                return True
    return False


def sanitize_text(value: str | None, max_len: int = 500) -> str:
    if not value:
        return ''
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(value))
    cleaned = cleaned.strip()
    return cleaned[:max_len]


def sanitize_phone(value: str | None) -> str:
    if not value:
        return ''
    cleaned = re.sub(r'[^\d+\s\-()]', '', str(value))
    return cleaned[:20]


_PHONE_RE = re.compile(r'^[\d+\s\-()]{6,20}$')
_EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def validate_phone(phone: str) -> bool:
    return bool(_PHONE_RE.match(phone or ''))


def validate_email(email: str) -> bool:
    if not email:
        return True
    return bool(_EMAIL_RE.match(email)) and len(email) <= 120


def honeypot_filled() -> bool:
    for name in ('website', 'url', 'company_url', 'fax', 'hp_field'):
        if request.form.get(name, '').strip():
            return True
    return False


def make_form_token() -> str:
    ts = str(int(time.time()))
    secret = current_app.config['SECRET_KEY'].encode()
    sig = hmac.new(secret, ts.encode(), hashlib.sha256).hexdigest()[:16]
    return f'{ts}.{sig}'


def verify_form_token(token: str | None, max_age: int = 3600) -> bool:
    if not token or '.' not in token:
        return False
    ts_str, sig = token.split('.', 1)
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if abs(time.time() - ts) > max_age:
        return False
    secret = current_app.config['SECRET_KEY'].encode()
    expected = hmac.new(secret, ts_str.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(sig, expected)


def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['X-XSS-Protection'] = '0'
    # img-src только self — внешние картинки не нужны
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'"
    )
    response.headers['Content-Security-Policy'] = csp
    if current_app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Server'] = 'WengAuto'
    # Не кэшировать личный кабинет
    if request.path.startswith(('/crm', '/admin', '/warehouse', '/login')):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
    return response


def anti_bot_middleware():
    if request.path.startswith('/static/'):
        return None
    # В тестах не режем «браузер» без лишних заголовков
    if current_app.config.get('TESTING'):
        ua = request.headers.get('User-Agent', '')
        if is_blocked_user_agent(ua):
            abort(403)
        return None
    if looks_like_scraper():
        abort(403)
    return None
