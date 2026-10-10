from functools import partial

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    database = tmp_path / "flashcards.db"
    monkeypatch.setattr(db, "init_db", partial(db.init_db, db_path=database))
    monkeypatch.setattr(db, "connect", partial(db.connect, db_path=database))
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("name", ["", "   ", "\t\n", "\u2003"])
def test_blank_deck_names_are_rejected(client, name):
    assert client.post("/api/decks", json={"name": name}).status_code == 422
    assert client.get("/api/decks").json() == []


@pytest.mark.parametrize("field", ["front", "back"])
def test_blank_card_text_is_rejected(client, field):
    deck = client.post("/api/decks", json={"name": "Study"}).json()
    payload = {"front": "Question", "back": "Answer", field: " \t\n "}
    url = f"/api/decks/{deck['id']}/cards"
    assert client.post(url, json=payload).status_code == 422
    assert client.get(url).json() == []


def test_valid_text_is_trimmed_and_stored(client):
    deck = client.post("/api/decks", json={"name": "  Study  "}).json()
    assert deck["name"] == "Study"
    url = f"/api/decks/{deck['id']}/cards"
    response = client.post(url, json={"front": "  First\nSecond  ", "back": " Answer\t"})
    assert response.status_code == 200
    assert response.json()["front"] == "First\nSecond"
    assert response.json()["back"] == "Answer"
    assert client.get(url).json()[0]["front"] == "First\nSecond"


@pytest.mark.parametrize("quality", [True, False, "4", 3.5, 4.0])
def test_review_rejects_non_integer_quality_without_changing_card(client, quality):
    deck = client.post("/api/decks", json={"name": "Study"}).json()
    url = f"/api/decks/{deck['id']}/cards"
    card = client.post(url, json={"front": "Q", "back": "A"}).json()
    response = client.post("/api/reviews", json={"card_id": card["id"], "quality": quality})
    assert response.status_code == 422
    assert client.get(url).json() == [card]


@pytest.mark.parametrize("quality", range(6))
def test_review_accepts_integer_quality(client, quality):
    deck = client.post("/api/decks", json={"name": "Study"}).json()
    card = client.post(f"/api/decks/{deck['id']}/cards", json={"front": "Q", "back": "A"}).json()
    assert client.post("/api/reviews", json={"card_id": card["id"], "quality": quality}).status_code == 200
