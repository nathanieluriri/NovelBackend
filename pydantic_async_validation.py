from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class ValidationInfo:
    field_names: tuple[str, ...]


def async_field_validator(*field_names: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        setattr(func, "__async_field_validator_fields__", tuple(field_names))
        return func

    return decorator


class AsyncValidationModelMixin:
    async def model_async_validate(self) -> "AsyncValidationModelMixin":
        executed_validators: set[int] = set()

        for cls in type(self).mro():
            for attribute_name, attribute_value in cls.__dict__.items():
                field_names = getattr(attribute_value, "__async_field_validator_fields__", None)
                if field_names is None:
                    continue

                validator = getattr(self, attribute_name, None)
                if validator is None:
                    continue

                validator_id = id(attribute_value)
                if validator_id in executed_validators:
                    continue
                executed_validators.add(validator_id)

                await validator(ValidationInfo(field_names=tuple(field_names)))

        return self
