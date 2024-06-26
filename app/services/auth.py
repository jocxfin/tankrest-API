import requests
from fastapi import HTTPException
from app.core.config import settings
from loguru import logger

class AuthService:
    BASE_URL = "https://api.tankille.fi"

    @staticmethod
    def login():
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
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"Login failed with status code {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail="Login failed")
        logger.info("Login successful")
        return response.json()

    @staticmethod
    def refresh(token: str):
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
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"Token refresh failed with status code {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail="Token refresh failed")
        logger.info("Token refresh successful")
        return response.json()
