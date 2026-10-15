# app.py — точка входа АИС «WengAuto» (production-ready hardening)
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request, jsonify
from flask_wtf.csrf import CSRFError
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from models import db, User
from modules.security import (
    csrf, security_headers, anti_bot_middleware, _client_ip
)
from modules.website import website_bp
from modules.auth import auth_bp
from modules.crm import crm_bp
from modules.warehouse import warehouse_bp
from modules.admin import admin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Логирование (всегда, для аудита A09) ---
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'logs'), exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(app.config['BASE_DIR'], 'logs', 'wengauto.log'),
        maxBytes=2_000_000, backupCount=5, encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    handler.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    db.init_app(app)
    csrf.init_app(app)

    # Rate limiter — защита от массовых запросов / ботов
    limiter = Limiter(
        key_func=lambda: _client_ip() or get_remote_address(),
        app=app,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '200 per hour')],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URI', 'memory://'),
        headers_enabled=True,
    )
    app.extensions['limiter'] = limiter

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для доступа необходимо войти в систему'
    login_manager.session_protection = 'strong'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    # Middleware
    @app.before_request
    def _security_before():
        return anti_bot_middleware()

    @app.after_request
    def _security_after(response):
        return security_headers(response)

    # Blueprints
    app.register_blueprint(website_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(admin_bp)

    # --- Обработчики ошибок (не отдаём стек наружу) ---

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        app.logger.warning('CSRF failed path=%s', request.path)
        if request.path.startswith('/api/'):
            return jsonify(error='Сессия устарела. Обновите страницу.'), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Некорректный запрос'), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Доступ запрещён'), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Не найдено'), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        if request.path.startswith('/api/'):
            return jsonify(error='Слишком много запросов. Подождите.'), 429
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception('Internal error')
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify(error='Внутренняя ошибка сервера'), 500
        return render_template('errors/500.html'), 500

    @app.route('/robots.txt')
    def robots_txt():
        ai_bots = [
            'GPTBot', 'ChatGPT-User', 'OAI-SearchBot', 'Google-Extended',
            'CCBot', 'anthropic-ai', 'ClaudeBot', 'Claude-Web', 'Claude-SearchBot',
            'Bytespider', 'Amazonbot', 'PerplexityBot', 'YouBot', 'cohere-ai',
            'Diffbot', 'ImagesiftBot', 'meta-externalagent', 'Applebot-Extended',
        ]
        lines = [
            'User-agent: *',
            'Allow: /',
            'Disallow: /crm/',
            'Disallow: /admin/',
            'Disallow: /warehouse/',
            'Disallow: /login',
            'Disallow: /api/',
            '',
        ]
        for bot in ai_bots:
            lines += [f'User-agent: {bot}', 'Disallow: /', '']
        lines.append('Sitemap: /sitemap.xml')
        return '\n'.join(lines), 200, {'Content-Type': 'text/plain; charset=utf-8'}

    @app.route('/sitemap.xml')
    def sitemap():
        from flask import url_for
        pages = ['website.index', 'website.catalog', 'website.promos',
                 'website.trade_in', 'website.credit', 'website.service',
                 'website.about', 'website.contacts']
        xml = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for ep in pages:
            xml.append(f'  <url><loc>{url_for(ep, _external=True)}</loc></url>')
        xml.append('</urlset>')
        return '\n'.join(xml), 200, {'Content-Type': 'application/xml; charset=utf-8'}


    # Жёсткие лимиты на чувствительные маршруты
    with app.app_context():
        pass
    try:
        limiter.limit('8 per minute;40 per hour')(app.view_functions['auth.login'])
        limiter.limit('15 per minute;100 per hour')(app.view_functions['website.create_lead'])
        limiter.limit('10 per minute;50 per hour')(app.view_functions['website.book_service'])
        limiter.limit('30 per minute')(app.view_functions['website.credit_calculator'])
    except Exception as ex:
        app.logger.warning('Rate limit attach: %s', ex)

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    from seed_data import seed
    seed()
    print('=' * 50)
    print('АИС «WengAuto» (hardened) запущена')
    print('Сайт: http://127.0.0.1:5000')
    print('CRM:  http://127.0.0.1:5000/crm')
    print('=' * 50)
    # debug=False — не светим стек ошибок наружу
    app.run(host='127.0.0.1', port=5003, debug=False)
