import requests
from fastapi import HTTPException
from app.core.config import settings
from loguru import logger
from datetime import datetime, timedelta
import threading

class AuthService:
    BASE_URL = "https://api.tankille.fi"
    refresh_token = None
    access_token = None
    token_expiry = datetime.utcnow() - timedelta(hours=1)

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
        tokens = response.json()
        AuthService.refresh_token = tokens.get("refreshToken")
        AuthService.access_token = tokens.get("accessToken")
        AuthService.token_expiry = datetime.utcnow() + timedelta(hours=1)
        return tokens

    @staticmethod
    def refresh():
        url = f"{AuthService.BASE_URL}/auth/refresh"
        payload = {"token": AuthService.refresh_token}
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
        tokens = response.json()
        AuthService.access_token = tokens.get("accessToken")
        AuthService.token_expiry = datetime.utcnow() + timedelta(hours=1)
        return tokens

    @staticmethod
    def schedule_token_refresh():
        def refresh_tokens():
            while True:
                now = datetime.utcnow()
                if AuthService.token_expiry < now + timedelta(minutes=5):
                    AuthService.refresh()
                threading.Event().wait(60)  # wait for 1 minute

        thread = threading.Thread(target=refresh_tokens, daemon=True)
        thread.start()
