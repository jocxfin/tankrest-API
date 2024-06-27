from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case
from app.core.database import get_db
from app.models.station import Station
from app.models.price import Price
from app.services.fuel import FuelService
from geopy.distance import geodesic
from loguru import logger
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()

tokens = {}

def set_tokens(new_tokens):
    global tokens
    tokens = new_tokens

@router.get("/stations")
async def read_stations(skip: int = 0, limit: int = 5000, db: Session = Depends(get_db)):
    stations = db.query(Station).offset(skip).limit(limit).all()
    return stations

@router.get("/stations/{station_id}/prices")
async def read_station_prices(station_id: str, db: Session = Depends(get_db)):
    prices = db.query(Price).filter(Price.station_id == station_id).all()
    if not prices:
        raise HTTPException(status_code=404, detail="Prices not found")
    return prices

@router.get("/stations/search")
async def search_stations(
    name: str = None,
    longitude: float = None,
    latitude: float = None,
    distance: int = 10000,
    latest: bool = False,
    chain: str = None,
    fuel_type: str = None,
    sortby: str = None,
    city: str = None,
    zipcode: str = None,
    dbonly: bool = False,
    simplified: bool = False,
    db: Session = Depends(get_db)
):
    if not tokens or "accessToken" not in tokens:
        raise HTTPException(status_code=401, detail="Access token missing or invalid")

    query = db.query(Station)

    if name:
        names = name.split(',')
        logger.info(f"Searching stations by names: {names}")
        name_order = case(*[(Station.name.ilike(n), i) for i, n in enumerate(names)], else_=len(names))
        query = query.filter(func.lower(Station.name).in_([n.lower() for n in names])).order_by(name_order)
    if chain:
        chains = chain.split(',')
        logger.info(f"Searching stations by chain: {chains}")
        query = query.filter(func.lower(Station.chain).in_([c.lower() for c in chains]))
    if city:
        logger.info(f"Searching stations by city: {city}")
        query = query.filter(Station.address_city.ilike(f"%{city}%"))
    if zipcode:
        logger.info(f"Searching stations by zipcode: {zipcode}")
        query = query.filter(Station.address_zipcode.ilike(f"%{zipcode}%"))
    if longitude is not None and latitude is not None:
        logger.info(f"Searching stations by location: longitude={longitude}, latitude={latitude}")
        stations = query.all()
        stations = [station for station in stations if geodesic((latitude, longitude), (station.location_latitude, station.location_longitude)).km <= distance / 1000]
    else:
        stations = query.all()

    if not stations:
        raise HTTPException(status_code=404, detail="Stations not found")

    async def fetch_prices_for_station(station):
        try:
            prices_query = db.query(Price).filter(Price.station_id == station.id)
            if latest:
                subquery = prices_query.order_by(desc(Price.updated_at)).distinct(Price.tag).with_entities(Price.id).subquery()
                prices = db.query(Price).filter(Price.station_id == station.id, Price.id.in_(subquery)).all()
            else:
                prices = prices_query.all()

            should_update = True
            if dbonly:
                should_update = False
            else:
                if prices:
                    last_updated = max(price.updated_at for price in prices)
                    if last_updated and datetime.utcnow() - last_updated < timedelta(minutes=20):
                        should_update = False

            if should_update:
                logger.info(f"Fetching prices from API for station {station.id}")
                prices_response = await FuelService.get_station_prices(station.id, tokens["accessToken"], since="2024-06-01T00:00:00Z")
                for price_data in prices_response:
                    for price in price_data.get("prices", []):
                        price_record = Price(
                            station_id=station.id,
                            tag=price.get("tag"),
                            price=price.get("value"),
                            updated=price_data.get("timestamp"),
                            delta=0,
                            reporter=price_data.get("userId"),
                            updated_at=datetime.utcnow()
                        )
                        db.add(price_record)
                db.commit()

                prices_query = db.query(Price).filter(Price.station_id == station.id)
                if latest:
                    subquery = prices_query.order_by(desc(Price.updated_at)).distinct(Price.tag).with_entities(Price.id).subquery()
                    prices = db.query(Price).filter(Price.station_id == station.id, Price.id.in_(subquery)).all()
                else:
                    prices = prices_query.all()
            
            prices_list = [
                {
                    "tag": price.tag,
                    "value": price.price,
                    "timestamp": price.updated
                } for price in prices
            ]

            if fuel_type:
                fuel_types = fuel_type.split(',')
                prices_list = [price for price in prices_list if price["tag"] in fuel_types]

            if latest:
                latest_prices_dict = {}
                for price in prices_list:
                    if price["tag"] not in latest_prices_dict or price["timestamp"] > latest_prices_dict[price["tag"]]["timestamp"]:
                        latest_prices_dict[price["tag"]] = price
                prices_list = list(latest_prices_dict.values())

            if simplified:
                enriched_station = {
                    "name": station.name,
                    "brand": station.brand,
                    "location": {
                        "latitude": station.location_latitude,
                        "longitude": station.location_longitude
                    },
                    "prices": prices_list
                }
            else:
                enriched_station = {
                    "id": station.id,
                    "name": station.name,
                    "chain": station.chain,
                    "brand": station.brand,
                    "address": {
                        "street": station.address_street,
                        "city": station.address_city,
                        "zipcode": station.address_zipcode,
                        "country": station.address_country
                    },
                    "location": {
                        "latitude": station.location_latitude,
                        "longitude": station.location_longitude
                    },
                    "is_visible": station.is_visible,
                    "prices": prices_list
                }
            return enriched_station
        except Exception as e:
            logger.error(f"Failed to get prices for station {station.id}: {e}")
            return None

    tasks = [fetch_prices_for_station(station) for station in stations]
    enriched_stations = await asyncio.gather(*tasks)

    enriched_stations = [station for station in enriched_stations if station is not None]

    if sortby:
        if sortby == "pricedesc":
            enriched_stations.sort(key=lambda x: min([price["value"] for price in x["prices"]]) if x["prices"] else float('inf'), reverse=True)
        elif sortby == "priceasc":
            enriched_stations.sort(key=lambda x: min([price["value"] for price in x["prices"]]) if x["prices"] else float('inf'))
        elif sortby == "newest":
            enriched_stations.sort(key=lambda x: max([price["timestamp"] for price in x["prices"]]) if x["prices"] else '', reverse=True)

    return enriched_stations
