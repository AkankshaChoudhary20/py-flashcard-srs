from functools import partial
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
from fastapi.testclient import TestClient
from app import db
from app.main import app
import app.main as main


def test_concurrent_reviews_preserve_both_repetition_updates(tmp_path,monkeypatch):
    database=tmp_path/'cards.db'
    monkeypatch.setattr(db,'init_db',partial(db.init_db,db_path=database))
    monkeypatch.setattr(db,'connect',partial(db.connect,db_path=database))
    original=main.review;started=Event()
    def delayed_review(*args,**kwargs):
        started.set();time.sleep(.15)
        return original(*args,**kwargs)
    monkeypatch.setattr(main,'review',delayed_review)
    with TestClient(app) as client:
        deck=client.post('/api/decks',json={'name':'Study'}).json()
        card=client.post(f"/api/decks/{deck['id']}/cards",json={'front':'Q','back':'A'}).json()
        payload={'card_id':card['id'],'quality':4}
        with ThreadPoolExecutor(max_workers=2) as executor:
            first=executor.submit(client.post,'/api/reviews',json=payload)
            assert started.wait(2)
            second=executor.submit(client.post,'/api/reviews',json=payload)
            assert first.result().status_code==200
            assert second.result().status_code==200
        updated=client.get(f"/api/decks/{deck['id']}/cards").json()[0]
        assert updated['repetitions']==2
        assert updated['interval_days']==6
