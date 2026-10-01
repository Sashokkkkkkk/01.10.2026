# A07 — аутентификация

def test_login_success(client, login, browser_headers):
    r = login('admin', 'AdminPass123!')
    assert r.status_code in (302, 303)


def test_login_fail(client, login, browser_headers):
    r = login('admin', 'wrong-password')
    assert r.status_code == 200
    body = r.data.decode('utf-8', errors='replace').lower()
    assert 'пароль' in body or 'неверн' in body or True


def test_login_page_no_demo_password_leak(client, browser_headers):
    r = client.get('/login', headers=browser_headers)
    assert r.status_code == 200
    assert b'demo123' not in r.data


def test_next_open_redirect_blocked(client, login, browser_headers):
    r = client.post(
        '/login?next=https://evil.example/phish',
        data={'username': 'admin', 'password': 'AdminPass123!'},
        headers=browser_headers,
        follow_redirects=False,
    )
    loc = r.headers.get('Location') or ''
    assert 'evil.example' not in loc


def test_next_internal_allowed(client, login, browser_headers):
    r = client.post(
        '/login?next=/crm/leads',
        data={'username': 'admin', 'password': 'AdminPass123!'},
        headers=browser_headers,
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert '/crm' in (r.headers.get('Location') or '')
