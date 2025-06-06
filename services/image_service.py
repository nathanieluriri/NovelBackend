import httpx
import asyncio
from fastapi import UploadFile, File
import base64


async def upload_base64_image(base64_string: str) -> dict:
    url = "https://image-hosting-api-v2.vercel.app/upload"
    payload = {"base64_image": base64_string}
    headers = {"accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['url']
    
    


async def get_base64_from_upload(file: UploadFile) -> str:
    content = await file.read()  # Read file contents as bytes
    return base64.b64encode(content).decode('utf-8') 