import pytest
from app.srs import grade_to_quality

@pytest.mark.parametrize('grade', [None, 4, True, [], {}])
def test_invalid_grade_types_report_validation_error(grade):
    with pytest.raises(ValueError, match='grade'):
        grade_to_quality(grade)
