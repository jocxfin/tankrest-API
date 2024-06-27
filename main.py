from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.api import endpoints
from app.core.database import Base, engine, get_async_db
from app.services.auth import AuthService
from app.services.fuel import FuelService
from app.models.station import Station
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
import asyncio

app = FastAPI()

# Create the database tables
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

tokens = None
tokens_lock = asyncio.Lock()

class FileLockContextManager:
    """Create a file on enter and remove that file on exit."""

    def __init__(self, filename) -> None:
        self.filename = filename
        self.lock_file = Path(self.filename)

    async def __aenter__(self) -> None:
        # Might raise FileExistsError
        async with aiofiles.open(self.lock_file, mode='x'):
            pass

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.warning("Deleting lock file")
        await aiofiles.os.remove(self.lock_file)

async def initialize_tokens():
    global tokens
    try:
        login_response = await AuthService.login()
        logger.info("Successfully logged in and obtained tokens.")
        logger.info(f"Login response: {login_response}")
        refresh_token = login_response.get("refreshToken")
        tokens = await AuthService.refresh(refresh_token)
        logger.info("Successfully refreshed token.")
        logger.info(f"Tokens received: {tokens}")
        endpoints.set_tokens(tokens)
    except Exception as e:
        logger.error(f"Failed to login or refresh token: {e}")
        tokens = None

async def refresh_tokens_periodically():
    global tokens
    while True:
        await asyncio.sleep(3600)  # Refresh every hour
        try:
            async with FileLockContextManager("/tmp/token_refresh.lock"):
                async with tokens_lock:
                    refresh_token = tokens.get("refreshToken")
                    tokens = await AuthService.refresh(refresh_token)
                    logger.info("Token refresh successful")
                    endpoints.set_tokens(tokens)
        except FileExistsError:
            logger.info("Token refresh already in progress by another worker.")
        except Exception as e:
            logger.error(f"Failed to refresh tokens: {e}")

# Initialize tokens on startup
@app.on_event("startup")
async def on_startup():
    await initialize_tokens()
    asyncio.create_task(refresh_tokens_periodically())

async def update_stations(db: AsyncSession, token: str):
    stations_data = await FuelService.get_stations(token)
    for station in stations_data:
        db_station = await db.execute(
            Station.__table__.select().where(Station.id == station["_id"])
        ).first()
        if not db_station:
            try:
                is_visible = station.get("isVisible", False)
                if isinstance(is_visible, int):
                    is_visible = bool(is_visible)

                location_latitude = float(station["location"]["coordinates"][1])
                location_longitude = float(station["location"]["coordinates"][0])
                
                logger.info(f"Adding station: id={station['_id']}, name={station['name']}")
                
                db_station = Station(
                    id=station["_id"],
                    name=station["name"],
                    chain=station["chain"],
                    brand=station["brand"],
                    address_street=station["address"]["street"],
                    address_city=station["address"]["city"],
                    address_zipcode=station["address"]["zipcode"],
                    address_country=station["address"]["country"],
                    location_latitude=location_latitude,
                    location_longitude=location_longitude,
                    is_visible=is_visible
                )
                db.add(db_station)
            except Exception as e:
                logger.error(f"Error adding station {station['_id']}: {e}")
    await db.commit()

@app.on_event("startup")
async def initial_update_stations():
    async with tokens_lock:
        if tokens and "accessToken" in tokens:
            async with get_async_db() as db:
                await update_stations(db, tokens["accessToken"])
        else:
            logger.error("No accessToken found in tokens.")

app.include_router(endpoints.router)

app.mount("/static", StaticFiles(directory="app/templates"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    async with aiofiles.open("app/templates/index.html") as f:
        html_content = await f.read()
    return HTMLResponse(content=html_content)
