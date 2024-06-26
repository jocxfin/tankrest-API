import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "TankRest"
    PROJECT_VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/fuel_prices.db")
    EMAIL: str = os.getenv("EMAIL")
    PASSWORD: str = os.getenv("PASSWORD")
    DEVICE: str = os.getenv("DEVICE")
    USER_AGENT: str = os.getenv("USER_AGENT")

settings = Settings()
