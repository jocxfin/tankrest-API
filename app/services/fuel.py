import requests
from fastapi import HTTPException
from app.core.config import settings
from loguru import logger

class FuelService:
    BASE_URL = "https://api.tankille.fi"

    @staticmethod
    def get_stations(token: str):
        url = f"{FuelService.BASE_URL}/stations"
        headers = {
            "x-access-token": token,
            "accept": "*/*",
            "user-agent": settings.USER_AGENT,
            "accept-language": "en",
            "accept-encoding": "gzip;q=1.0, compress;q=0.5"
        }
        logger.info(f"Sending get stations request to {url}")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get stations with status code {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail="Failed to get stations")
        logger.info("Get stations request successful")
        return response.json()

    @staticmethod
    def get_station_prices(station_id: str, token: str, since: str):
        url = f"{FuelService.BASE_URL}/stations/{station_id}/prices"
        params = {"since": since}
        headers = {
            "x-access-token": token,
            "accept": "*/*",
            "user-agent": settings.USER_AGENT,
            "accept-language": "en",
            "accept-encoding": "gzip;q=1.0, compress;q=0.5"
        }
        logger.info(f"Sending get station prices request to {url}")
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            logger.error(f"Failed to get station prices with status code {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail="Failed to get station prices")
        logger.info("Get station prices request successful")
        return response.json()
