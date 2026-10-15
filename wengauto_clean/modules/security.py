# modules/security.py — защита от ботов, нейросетей-скраперов, злоупотреблений
"""
Меры (легальная hardening веб-приложения):
- Rate limiting по IP
- Блокировка известных AI/scraper User-Agents
- Honeypot-поля в формах (невидимы людям)
- Простая JS-проверка (timestamp + token)
- Secure HTTP headers
- Валидация и нормализация ввода
- Защита логина от brute-force
"""
from __future__ import annotations

import hashlib
import hmac
import re
import time
from functools import wraps
from collections import defaultdict
from threading import Lock

from flask import request, abort, g, current_app, session
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

# --- In-memory fail2ban-like для логина (без Redis) ---
_login_failures: dict[str, list[float]] = defaultdict(list)
_lock = Lock()
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SEC = 900  # 15 мин
LOGIN_BLOCK_SEC = 1800  # 30 мин блок


def _client_ip() -> str:
    # За прокси (nginx) смотрим X-Forwarded-For, иначе remote_addr
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()[:45]
    return (request.remote_addr or '0.0.0.0')[:45]


def is_blocked_user_agent(ua: str) -> bool:
    if not ua:
        return True
    low = ua.lower()
    allowed = current_app.config.get('ALLOWED_BOT_UA', [])
    if any(a in low for a in allowed):
        return False
    blocked = current_app.config.get('BLOCKED_UA_SUBSTRINGS', [])
    return any(b in low for b in blocked)


def check_bot_headers() -> bool:
    """Грубая эвристика: отсутствие типичных браузерных заголовков."""
    ua = request.headers.get('User-Agent', '')
    if is_blocked_user_agent(ua):
        return True
    # Пустой Accept у многих скриптов
    accept = request.headers.get('Accept', '')
    if request.method == 'GET' and not accept and not ua:
        return True
    return False


def register_login_failure(ip: str) -> None:
    now = time.time()
    with _lock:
        fails = _login_failures[ip]
        fails.append(now)
        # чистим старые
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
    # Убираем управляющие символы, обрезаем
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(value))
    cleaned = cleaned.strip()
    return cleaned[:max_len]


def sanitize_phone(value: str | None) -> str:
    if not value:
        return ''
    # Только цифры, +, пробелы, скобки, дефис
    cleaned = re.sub(r'[^\d+\s\-()]', '', str(value))
    return cleaned[:20]


_PHONE_RE = re.compile(r'^[\d+\s\-()]{6,20}$')
_EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def validate_phone(phone: str) -> bool:
    return bool(_PHONE_RE.match(phone or ''))


def validate_email(email: str) -> bool:
    if not email:
        return True  # необязательное
    return bool(_EMAIL_RE.match(email)) and len(email) <= 120


def honeypot_filled() -> bool:
    """Если бот заполнил скрытое поле — отклоняем."""
    # Поля, которых нет в видимой форме
    for name in ('website', 'url', 'company_url', 'fax', 'hp_field'):
        val = request.form.get(name, '').strip()
        if val:
            return True
    return False


def make_form_token() -> str:
    """Одноразовый токен формы: timestamp + HMAC."""
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
    """Заголовки безопасности (OWASP-рекомендации)."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['X-XSS-Protection'] = '0'  # устаревший; полагаемся на CSP
    # CSP: без inline-скриптов где возможно; для калькулятора оставляем 'unsafe-inline' минимум
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp
    if current_app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Не светим стек
    response.headers['Server'] = 'WengAuto'
    return response


def anti_bot_middleware():
    """Вызывается before_request: блокирует явных ботов/скраперов."""
    # Статика и favicon — пропускаем
    if request.path.startswith('/static/'):
        return None
    if check_bot_headers():
        abort(403)
    return None
