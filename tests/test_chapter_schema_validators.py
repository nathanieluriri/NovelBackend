import pytest
from pydantic import ValidationError

from schemas.chapter_schema import ChapterOut


def test_chapter_out_validator_handles_none_input_without_attribute_error():
    with pytest.raises(ValidationError):
        ChapterOut.model_validate(None)
