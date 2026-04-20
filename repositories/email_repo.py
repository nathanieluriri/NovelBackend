from core.database import client
from schemas.email_schema import ClientData


async def create_email_log(client_data: ClientData):
    print(client_data)
    payload = (
        client_data.model_dump()
        if hasattr(client_data, "model_dump")
        else dict(client_data)
    )
    return await client.insert_and_fetch("LoginAttempts", payload)
