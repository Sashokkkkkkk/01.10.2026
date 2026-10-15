# config.py — конфигурация АИС «WengAuto» (усиленная безопасность)
import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # В проде/локально — рядом с проектом; в sandbox можно SQLITE_PATH
    _db = os.environ.get('SQLITE_PATH') or os.path.join(BASE_DIR, 'wengauto.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or ('sqlite:///' + _db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('HTTPS', '0') == '1'
    PERMANENT_SESSION_LIFETIME = 3600 * 8
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600 * 24 * 7

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False

    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_DEFAULT = '200 per hour;60 per minute'
    RATELIMIT_HEADERS_ENABLED = True

    MAX_INTERNAL_USERS = 30
    MAX_SITE_VISITORS = 1000
    MAX_CATALOG_ITEMS = 5000

    BLOCKED_UA_SUBSTRINGS = [
        'gptbot', 'chatgpt', 'ccbot', 'anthropic', 'claude-web', 'claudebot',
        'google-extended', 'bytespider', 'petalbot', 'scrapy', 'httpclient',
        'python-requests', 'python-urllib', 'aiohttp', 'httpx', 'curl/',
        'wget/', 'libwww', 'java/', 'go-http', 'okhttp', 'postman',
        'headlesschrome', 'phantomjs', 'selenium', 'puppeteer', 'playwright',
        'dataforseo', 'semrush', 'ahrefs', 'mj12bot', 'dotbot',
    ]
    ALLOWED_BOT_UA = ['googlebot', 'bingbot', 'yandexbot', 'duckduckbot']

    MAX_NAME_LEN = 150
    MAX_PHONE_LEN = 20
    MAX_MESSAGE_LEN = 2000
