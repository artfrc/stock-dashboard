# LiveMarket — Real-Time Stock Dashboard

A full-stack real-time dashboard that simulates a live stock market feed. The Python backend runs a scheduler that updates prices every 60 seconds and pushes changes to the frontend via WebSocket, producing instant visual feedback without any page refresh.

![Stack](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![Stack](https://img.shields.io/badge/Frontend-Vue.js_3-42b883?style=flat-square&logo=vue.js)
![Stack](https://img.shields.io/badge/Realtime-WebSocket-6366f1?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

---

## Features

- **Live price updates** — APScheduler triggers a price recalculation every 60 seconds; the result is broadcast to every connected client through a WebSocket
- **Row flash animations** — table rows flash green or red to indicate whether each price went up or down
- **Countdown ring** — SVG ring in the header counts down the seconds to the next scheduled update
- **Connection status badge** — shows Live / Connecting / Offline and auto-reconnects if the WebSocket drops
- **Summary stat cards** — dynamically computed gainers count, losers count, top gainer and top loser
- **Toast notification** — a non-intrusive notification appears on every data refresh
- **Fake in-memory database** — no external database required; 10 tech stocks with realistic Gaussian price variation (±1.2%, capped at ±5%)
- **REST endpoint** — `GET /api/data` also available for one-shot queries
- **Modern dark UI** — glassmorphism cards, ambient glows, JetBrains Mono for numbers, fully responsive

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+ · FastAPI · Uvicorn |
| Scheduler | APScheduler (AsyncIOScheduler) |
| Realtime | WebSocket (native FastAPI) |
| Frontend | Vue 3 (Composition API) · Vite |
| Styling | Custom CSS — dark theme, glassmorphism, CSS animations |
| Fonts | Inter · JetBrains Mono (Google Fonts) |

---

## Project Structure

```
stock-dashboard/
├── backend/
│   ├── main.py            # FastAPI app, scheduler, WebSocket, fake DB
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.vue        # Main component — table, animations, WS logic
    │   ├── main.js        # Vue app entry point
    │   └── style.css      # Global resets and CSS variables
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

> Both servers must be running at the same time.

---

## API Reference

### `GET /api/data`

Returns the current state of all stocks in the fake database.

**Response**

```json
{
  "stocks": [
    {
      "id": 1,
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "price": 181.34,
      "prev_price": 178.50,
      "change": 2.84,
      "change_pct": 1.59,
      "volume": 67000000,
      "market_cap": "2.8T"
    }
  ],
  "last_updated": "2026-06-25T20:12:11.327417",
  "update_count": 3
}
```

### `WS /ws`

WebSocket endpoint. On connection, sends an `initial` message with the full dataset. Every 60 seconds, sends an `update` message with the refreshed data.

**Message types**

| type | When sent | Payload |
|---|---|---|
| `initial` | On connection | `{ type, stocks, last_updated, update_count }` |
| `update` | Every 60 s | `{ type, stocks, last_updated, update_count }` |

---

## How the Scheduler Works

```
App startup
    └── AsyncIOScheduler starts
            └── update_prices() runs every 60 seconds
                    ├── Applies Gaussian noise (σ=1.2%) to each stock price
                    ├── Clamps delta to [-5%, +5%]
                    ├── Recalculates change and change_pct
                    ├── Randomises volume
                    └── Broadcasts updated payload to all WebSocket clients
```

The price variation uses `random.gauss(0, 0.012)` — a normal distribution centred at 0, which produces natural-looking market fluctuation rather than uniform random noise.

---

## Frontend Architecture

The entire UI lives in a single `App.vue` file using Vue 3's Composition API.

```
App.vue
 ├── WebSocket connection (auto-reconnect on close)
 ├── 1-second interval → countdown ref (feeds the SVG ring)
 ├── On WS message:
 │    ├── applyFlash()  → compares new vs old prices, sets flashMap
 │    ├── toast()       → shows the refresh notification for 3.2 s
 │    └── resets countdown to 60
 └── Template
      ├── Header        → logo, last-update time, countdown ring, conn badge
      ├── Stats row     → gainers, losers, top gainer, top loser (computed)
      ├── Table         → 10 rows with flash-up / flash-down CSS animations
      └── Toast         → <Transition> animated notification
```

---

## Customisation

| What | Where | How |
|---|---|---|
| Update interval | `backend/main.py` | Change `UPDATE_INTERVAL_SECONDS` |
| Stock list | `backend/main.py` | Edit the `fake_db["stocks"]` list |
| Price volatility | `backend/main.py` | Adjust `random.gauss(0, 0.012)` — increase σ for wilder swings |
| Flash duration | `frontend/src/App.vue` | Change `1600` ms in `applyFlash()` and the matching CSS `animation` duration |
| Color theme | `frontend/src/style.css` | Edit the CSS variables in `:root` |

---

## License

MIT
