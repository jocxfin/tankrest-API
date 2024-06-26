from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from loguru import logger
from app.api import endpoints
from app.core.database import Base, engine, get_db
from app.services.auth import AuthService
from app.services.fuel import FuelService
from app.models.station import Station
from datetime import datetime

app = FastAPI()

# Create the database tables
Base.metadata.create_all(bind=engine)

# Perform initial login to get tokens
try:
    login_response = AuthService.login()
    logger.info("Successfully logged in and obtained tokens.")
    logger.info(f"Login response: {login_response}")
    
    refresh_token = login_response.get("refreshToken")
    tokens = AuthService.refresh(refresh_token)
    logger.info("Successfully refreshed token.")
    logger.info(f"Tokens received: {tokens}")
    endpoints.set_tokens(tokens)
except Exception as e:
    logger.error(f"Failed to login or refresh token: {e}")
    tokens = None

# Fetch all stations and update the database
def update_stations(db: Session, token: str):
    stations_data = FuelService.get_stations(token)
    for station in stations_data:
        db_station = db.query(Station).filter(Station.id == station["_id"]).first()
        if not db_station:
            try:
                is_visible = station.get("isVisible", False)
                if isinstance(is_visible, int):
                    is_visible = bool(is_visible)

                location_latitude = float(station["location"]["coordinates"][1])
                location_longitude = float(station["location"]["coordinates"][0])
                
                logger.info(f"Adding station: id={station['_id']}, name={station['name']}, chain={station['chain']}, brand={station['brand']}, address_street={station['address']['street']}, address_city={station['address']['city']}, address_zipcode={station['address']['zipcode']}, address_country={station['address']['country']}, location_latitude={location_latitude}, location_longitude={location_longitude}, is_visible={is_visible}")
                
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
    db.commit()

if tokens and "accessToken" in tokens:
    with next(get_db()) as db:
        update_stations(db, tokens["accessToken"])
else:
    logger.error("No accessToken found in tokens.")

app.include_router(endpoints.router)

app.mount("/static", StaticFiles(directory="app/templates"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("app/templates/index.html") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
