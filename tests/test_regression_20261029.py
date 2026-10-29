import pytest
from functools import partial
from fastapi.testclient import TestClient
from app import db
from app.main import app

@pytest.mark.parametrize("card_id", [2**63, -(2**63)-1, 0, -1, True, "1", 1.0])
def test_invalid_review_ids_return_validation_error(card_id, tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'init_db', partial(db.init_db, db_path=tmp_path / 'cards.db'))
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post('/api/reviews', json={'card_id': card_id, 'quality': 4})
    assert response.status_code == 422
    assert response.json()['detail'][0]['loc'] == ['body', 'card_id']
