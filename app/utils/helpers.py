from functools import wraps
from random import randint

CHARS = "abcdefghiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"


def generate_random_string(n: int = 15):
    st = ""
    for i in range(n):
        st += CHARS[randint(0, len(CHARS) - 1)]

    return st


# Black boxed!
def resolve_projection(allowed_fields: dict, default_fields: list):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            raw_fields = kwargs.get("fields", [])

            selected_columns = [
                allowed_fields[f] for f in raw_fields if f in allowed_fields
            ]

            if not selected_columns:
                selected_columns = default_fields

            kwargs["fields"] = selected_columns

            return await func(*args, **kwargs)

        return wrapper

    return decorator
