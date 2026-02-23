import pytest
from main import app
from db import init_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_get_watchlist(client):
    rv = client.get('/api/watchlist/')
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert 'watchlist' in json_data

def test_add_to_watchlist(client):
    rv = client.post('/api/watchlist/', json={'symbol': 'AAPL'})
    # It might be 200 or 409 if already exists
    assert rv.status_code in [200, 409, 201]
