from app import db
from datetime import date

def test_deck_due_cards_use_compound_index(tmp_path):
    path = tmp_path / 'cards.db'
    db.init_db(path)
    with db.connect(path) as conn:
        deck = db.create_deck(conn, 'Deck')
        card = db.create_card(conn, deck['id'], 'Front', 'Back')
        plan = conn.execute('EXPLAIN QUERY PLAN SELECT * FROM card WHERE deck_id = ? AND due_date <= ? ORDER BY due_date', (deck['id'], date.today().isoformat())).fetchall()
        assert any('idx_card_deck_due_date' in row[3] for row in plan)
        assert not any('TEMP B-TREE' in row[3] for row in plan)
        assert [r['id'] for r in db.get_due_cards(conn, deck['id'])] == [card['id']]
