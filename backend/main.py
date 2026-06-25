from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import random
from datetime import datetime
from typing import List

UPDATE_INTERVAL_SECONDS = 60

fake_db = {
    "stocks": [
        {"id": 1,  "symbol": "AAPL",  "name": "Apple Inc.",        "price": 178.50, "prev_price": 178.50, "change": 0.0, "change_pct": 0.0, "volume": 52_000_000,  "market_cap": "2.8T"},
        {"id": 2,  "symbol": "GOOGL", "name": "Alphabet Inc.",      "price": 141.80, "prev_price": 141.80, "change": 0.0, "change_pct": 0.0, "volume": 23_000_000,  "market_cap": "1.8T"},
        {"id": 3,  "symbol": "MSFT",  "name": "Microsoft Corp.",    "price": 378.90, "prev_price": 378.90, "change": 0.0, "change_pct": 0.0, "volume": 31_000_000,  "market_cap": "2.8T"},
        {"id": 4,  "symbol": "AMZN",  "name": "Amazon.com Inc.",    "price": 186.20, "prev_price": 186.20, "change": 0.0, "change_pct": 0.0, "volume": 44_000_000,  "market_cap": "1.9T"},
        {"id": 5,  "symbol": "META",  "name": "Meta Platforms",     "price": 481.50, "prev_price": 481.50, "change": 0.0, "change_pct": 0.0, "volume": 18_000_000,  "market_cap": "1.2T"},
        {"id": 6,  "symbol": "TSLA",  "name": "Tesla Inc.",         "price": 245.30, "prev_price": 245.30, "change": 0.0, "change_pct": 0.0, "volume": 89_000_000,  "market_cap": "780B"},
        {"id": 7,  "symbol": "NVDA",  "name": "NVIDIA Corp.",       "price": 875.40, "prev_price": 875.40, "change": 0.0, "change_pct": 0.0, "volume": 67_000_000,  "market_cap": "2.2T"},
        {"id": 8,  "symbol": "NFLX",  "name": "Netflix Inc.",       "price": 628.70, "prev_price": 628.70, "change": 0.0, "change_pct": 0.0, "volume": 12_000_000,  "market_cap": "275B"},
        {"id": 9,  "symbol": "AMD",   "name": "AMD Inc.",           "price": 168.30, "prev_price": 168.30, "change": 0.0, "change_pct": 0.0, "volume": 55_000_000,  "market_cap": "272B"},
        {"id": 10, "symbol": "INTC",  "name": "Intel Corp.",        "price": 38.20,  "prev_price": 38.20,  "change": 0.0, "change_pct": 0.0, "volume": 45_000_000,  "market_cap": "161B"},
    ],
    "last_updated": None,
    "update_count": 0,
}

active_connections: List[WebSocket] = []


async def broadcast(message: dict):
    for conn in list(active_connections):
        try:
            await conn.send_json(message)
        except Exception:
            if conn in active_connections:
                active_connections.remove(conn)


async def update_prices():
    for stock in fake_db["stocks"]:
        stock["prev_price"] = stock["price"]
        delta = random.gauss(0, 0.012)
        delta = max(-0.05, min(0.05, delta))
        new_price = round(stock["price"] * (1 + delta), 2)
        stock["price"] = max(1.0, new_price)
        stock["change"] = round(stock["price"] - stock["prev_price"], 2)
        stock["change_pct"] = round((stock["change"] / stock["prev_price"]) * 100, 2)
        stock["volume"] = random.randint(5_000_000, 120_000_000)

    fake_db["last_updated"] = datetime.now().isoformat()
    fake_db["update_count"] += 1

    await broadcast({
        "type": "update",
        "stocks": fake_db["stocks"],
        "last_updated": fake_db["last_updated"],
        "update_count": fake_db["update_count"],
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    fake_db["last_updated"] = datetime.now().isoformat()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_prices, "interval", seconds=UPDATE_INTERVAL_SECONDS)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="LiveMarket API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/data")
async def get_data():
    return {
        "stocks": fake_db["stocks"],
        "last_updated": fake_db["last_updated"],
        "update_count": fake_db["update_count"],
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await websocket.send_json({
        "type": "initial",
        "stocks": fake_db["stocks"],
        "last_updated": fake_db["last_updated"],
        "update_count": fake_db["update_count"],
    })
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
