import aiohttp
from fastapi import HTTPException
from app.core.config import settings
from loguru import logger

class AuthService:
    BASE_URL = "https://api.tankille.fi"

    @staticmethod
    async def login():
        url = f"{AuthService.BASE_URL}/auth/login"
        payload = {
            "email": settings.EMAIL,
            "password": settings.PASSWORD,
            "device": settings.DEVICE
        }
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "accept-encoding": "gzip;q=1.0, compress;q=0.5",
            "user-agent": settings.USER_AGENT,
            "accept-language": "en"
        }
        logger.info(f"Sending login request to {url}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Login failed with status code {response.status}")
                    raise HTTPException(status_code=response.status, detail="Login failed")
                logger.info("Login successful")
                return await response.json()

    @staticmethod
    async def refresh(token: str):
        url = f"{AuthService.BASE_URL}/auth/refresh"
        payload = {"token": token}
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "accept-encoding": "gzip;q=1.0, compress;q=0.5",
            "user-agent": settings.USER_AGENT,
            "accept-language": "en"
        }
        logger.info(f"Sending refresh request to {url}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Token refresh failed with status code {response.status}")
                    raise HTTPException(status_code=response.status, detail="Token refresh failed")
                logger.info("Token refresh successful")
                return await response.json()
