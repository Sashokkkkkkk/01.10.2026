# config.py — конфигурация АИС «WengAuto»
import os
import secrets


def _load_or_create_secret(base_dir: str) -> str:
    """SECRET_KEY из env или файла .secret_key (не светим в репозиторий)."""
    env = os.environ.get('SECRET_KEY')
    if env and len(env) >= 16:
        return env
    path = os.path.join(base_dir, '.secret_key')
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                val = f.read().strip()
            if len(val) >= 16:
                return val
        except OSError:
            pass
    val = secrets.token_hex(32)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(val)
    except OSError:
        pass
    return val


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = _load_or_create_secret(BASE_DIR)

    _db = os.environ.get('SQLITE_PATH') or os.path.join(BASE_DIR, 'wengauto.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or ('sqlite:///' + _db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 300}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('HTTPS', '0') == '1'
    PERMANENT_SESSION_LIFETIME = 3600 * 8
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False

    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_DEFAULT = '180 per hour;50 per minute'
    RATELIMIT_HEADERS_ENABLED = True

    BLOCKED_UA_SUBSTRINGS = [
        'gptbot', 'chatgpt', 'chatgpt-user', 'oai-searchbot',
        'ccbot', 'anthropic', 'claude-web', 'claudebot', 'claude-searchbot',
        'google-extended', 'google-cloudvertexbot',
        'bytespider', 'petalbot', 'amazonbot',
        'perplexitybot', 'perplexity-user',
        'youbot', 'cohere-ai', 'ai2bot', 'diffbot',
        'meta-externalagent', 'facebookexternalhit',
        'imagesiftbot', 'omgili', 'webzio-extended',
        'scrapy', 'httpclient', 'python-requests', 'python-urllib',
        'aiohttp', 'httpx', 'curl/', 'wget/', 'libwww', 'java/',
        'go-http', 'okhttp', 'postman', 'insomnia',
        'headlesschrome', 'phantomjs', 'selenium', 'puppeteer',
        'playwright', 'splash', 'htmlunit',
        'dataforseo', 'semrush', 'ahrefs', 'mj12bot', 'dotbot',
        'blexbot', 'seekport', 'nuclei', 'sqlmap', 'nikto', 'nmap',
        'masscan', 'zgrab', 'spider', 'crawler', 'scraper',
    ]
    ALLOWED_BOT_UA = ['googlebot', 'bingbot', 'yandexbot', 'duckduckbot', 'applebot']

    MAX_NAME_LEN = 150
    MAX_PHONE_LEN = 20
    MAX_MESSAGE_LEN = 2000
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB — защита от огромных POST
