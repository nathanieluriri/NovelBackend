# schemas/response_schema.py

from typing import Generic, TypeVar, Optional, Union
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    status_code: int
    data: Optional[T]
    detail: Union[str, list[str], dict, None]
