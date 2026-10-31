import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import db
from app.main import app

class DeckIdBoundsTests(unittest.TestCase):
    def test_invalid_deck_ids_never_reach_sqlite(self):
        client = TestClient(app)
        with patch.object(db, 'connect') as connect:
            for value in ('0', '-1', str(2**63), str(10**100)):
                urls = ['/api/decks/' + value + '/cards', '/api/cards/due?deck_id=' + value]
                for url in urls:
                    with self.subTest(url=url):
                        self.assertEqual(client.get(url).status_code, 422)
                self.assertEqual(client.post(urls[0], json={'front': 'Q', 'back': 'A'}).status_code, 422)
            connect.assert_not_called()
