# Боты, API, каталог
def test_gptbot_blocked(client):
    r = client.get('/', headers={'User-Agent': 'GPTBot/1.0'})
    assert r.status_code == 403


def test_claude_blocked(client):
    r = client.get('/', headers={'User-Agent': 'Mozilla/5.0 ClaudeBot'})
    assert r.status_code == 403


def test_credit_calculator(client, browser_headers):
    r = client.post(
        '/api/credit-calculator',
        json={'price': 1000000, 'down_payment': 100000, 'term_months': 12, 'rate': 12},
        headers={**browser_headers, 'Content-Type': 'application/json'},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert 'monthly_payment' in data
    assert data['loan_amount'] == 900000


def test_credit_calculator_bad_input(client, browser_headers):
    r = client.post(
        '/api/credit-calculator',
        json={'price': -1, 'down_payment': 0, 'term_months': 12, 'rate': 12},
        headers={**browser_headers, 'Content-Type': 'application/json'},
    )
    assert r.status_code == 400


def test_robots_disallow_ai(client, browser_headers):
    r = client.get('/robots.txt', headers=browser_headers)
    assert r.status_code == 200
    body = r.data.decode('utf-8')
    assert 'GPTBot' in body
    assert 'Disallow: /crm/' in body
