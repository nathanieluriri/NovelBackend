# schemas/response_schema.py

from typing import Generic, TypeVar, Optional, Union, Any
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class APIResponse(GenericModel, Generic[T]):
    status_code: int
    data: Optional[T]
    detail: Union[str, list[str], dict, None]
