import pytest
from fastapi import HTTPException
from app.main import ReviewIn

def test_matching_review_inputs_are_accepted():
    assert ReviewIn(card_id=1, grade=" Good ", quality=4).resolve_quality() == 4

@pytest.mark.parametrize("grade", ["again", "unknown"])
def test_conflicting_or_invalid_grade_is_not_silently_ignored(grade):
    with pytest.raises(HTTPException) as error:
        ReviewIn(card_id=1, grade=grade, quality=4).resolve_quality()
    assert error.value.status_code == 400
