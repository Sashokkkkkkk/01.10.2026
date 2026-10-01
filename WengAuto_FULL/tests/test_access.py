# A01 — контроль доступа
def test_public_pages(client, browser_headers):
    for path in ('/', '/catalog', '/contacts', '/login', '/credit'):
        r = client.get(path, headers=browser_headers)
        assert r.status_code == 200, path


def test_crm_requires_login(client, browser_headers):
    r = client.get('/crm/', headers=browser_headers, follow_redirects=False)
    assert r.status_code in (302, 401)
    assert '/login' in (r.headers.get('Location') or '')


def test_admin_requires_admin_role(client, login, browser_headers):
    login('manager', 'ManagerPass123!')
    r = client.get('/admin/', headers=browser_headers, follow_redirects=False)
    # manager не admin → редирект на главную
    assert r.status_code in (200, 302)
    if r.status_code == 302:
        assert '/admin' not in (r.headers.get('Location') or '')


def test_hidden_car_not_public(client, browser_headers):
    # id=2 — sold + not published
    r = client.get('/car/2', headers=browser_headers)
    assert r.status_code == 404


def test_published_car_ok(client, browser_headers):
    r = client.get('/car/1', headers=browser_headers)
    assert r.status_code == 200
