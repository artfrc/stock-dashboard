<template>
  <div class="app">
    <!-- Ambient background layers -->
    <div class="bg-grid"></div>
    <div class="bg-glow bg-glow--left"></div>
    <div class="bg-glow bg-glow--right"></div>

    <!-- ── Header ── -->
    <header class="header">
      <div class="header-inner">
        <div class="logo">
          <svg class="logo-icon" viewBox="0 0 24 24" fill="none">
            <path d="M3 17l4-8 4 4 4-6 4 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="19" cy="17" r="2" fill="var(--primary)"/>
          </svg>
          <span class="logo-text">LiveMarket</span>
        </div>

        <div class="header-meta">
          <div class="last-update" v-if="lastUpdated">
            <span class="meta-label">Updated</span>
            <span class="meta-value">{{ formatTime(lastUpdated) }}</span>
          </div>

          <!-- Countdown ring -->
          <div class="countdown-wrap">
            <div class="countdown-ring">
              <svg viewBox="0 0 36 36" class="ring-svg">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2.5"/>
                <circle
                  cx="18" cy="18" r="15.9"
                  fill="none"
                  stroke="var(--primary)"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  :stroke-dasharray="`${ringPct} 100`"
                  transform="rotate(-90 18 18)"
                  class="ring-progress"
                />
              </svg>
              <span class="ring-label">{{ countdown }}s</span>
            </div>
            <span class="meta-label">next update</span>
          </div>

          <!-- Connection badge -->
          <div class="conn-badge" :class="`conn-badge--${connectionStatus}`">
            <span class="conn-dot"></span>
            <span>{{ connLabel }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- ── Stats row ── -->
    <section class="stats-row" v-if="stocks.length">
      <div class="stat-card" v-for="s in summaryStats" :key="s.label">
        <div class="stat-icon-wrap">
          <span class="stat-icon">{{ s.icon }}</span>
        </div>
        <div class="stat-body">
          <span class="stat-val" :class="s.cls">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- ── Table card ── -->
    <main class="card table-card">
      <div class="card-header">
        <div class="card-title-wrap">
          <h2 class="card-title">Market Overview</h2>
          <span class="row-count">{{ stocks.length }} assets</span>
        </div>
        <div class="update-pill" v-if="updateCount > 0">
          <span class="pulse"></span>
          {{ updateCount }} refresh{{ updateCount !== 1 ? 'es' : '' }}
        </div>
      </div>

      <div class="table-scroll">
        <table class="market-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Company</th>
              <th class="r">Price</th>
              <th class="r">Change</th>
              <th class="r">Change %</th>
              <th class="r">Volume</th>
              <th class="r">Mkt Cap</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in stocks"
              :key="s.id"
              :class="['mrow', flashMap[s.id] === 'up' && 'mrow--up', flashMap[s.id] === 'down' && 'mrow--down']"
            >
              <td>
                <span class="symbol-tag">{{ s.symbol }}</span>
              </td>
              <td class="company-col">{{ s.name }}</td>
              <td class="r mono">{{ fmt(s.price) }}</td>
              <td class="r">
                <span :class="['delta', s.change >= 0 ? 'pos' : 'neg']">
                  {{ s.change >= 0 ? '+' : '' }}{{ fmt(s.change) }}
                </span>
              </td>
              <td class="r">
                <span :class="['pct-badge', s.change_pct >= 0 ? 'pos' : 'neg']">
                  <svg class="arrow-icon" viewBox="0 0 10 10" :style="s.change_pct < 0 ? 'transform:rotate(180deg)' : ''">
                    <path d="M5 2 L8 7 L2 7 Z" fill="currentColor"/>
                  </svg>
                  {{ Math.abs(s.change_pct).toFixed(2) }}%
                </span>
              </td>
              <td class="r mono muted">{{ fmtVol(s.volume) }}</td>
              <td class="r mono muted">{{ s.market_cap }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <!-- ── Toast ── -->
    <Transition name="toast">
      <div class="toast" v-if="showToast">
        <svg viewBox="0 0 20 20" fill="none" class="toast-icon">
          <path d="M10 3v2M10 15v2M3 10H1M19 10h-2M5.05 5.05 3.636 3.636M16.364 16.364l-1.414-1.414M5.05 14.95l-1.414 1.414M16.364 3.636l-1.414 1.414" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="10" cy="10" r="3" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        <span>Data refreshed</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const stocks        = ref([])
const lastUpdated   = ref(null)
const updateCount   = ref(0)
const connectionStatus = ref('connecting')
const countdown     = ref(60)
const flashMap      = ref({})
const showToast     = ref(false)

let ws              = null
let tickTimer       = null
let toastTimer      = null

// ── Computed ────────────────────────────────────────────────
const connLabel = computed(() => ({ connected: 'Live', connecting: 'Connecting…', disconnected: 'Offline' }[connectionStatus.value]))

const ringPct = computed(() => (countdown.value / 60) * 100)

const summaryStats = computed(() => {
  if (!stocks.value.length) return []
  const list = stocks.value
  const gainers = list.filter(s => s.change_pct > 0).length
  const losers  = list.filter(s => s.change_pct < 0).length
  const best    = list.reduce((a, b) => a.change_pct > b.change_pct ? a : b)
  const worst   = list.reduce((a, b) => a.change_pct < b.change_pct ? a : b)
  return [
    { icon: '▲', label: 'Gainers',    value: gainers, cls: 'pos' },
    { icon: '▼', label: 'Losers',     value: losers,  cls: losers > 0 ? 'neg' : '' },
    { icon: '★', label: 'Top Gainer', value: `${best.symbol}  ${best.change_pct >= 0 ? '+' : ''}${best.change_pct.toFixed(2)}%`, cls: best.change_pct >= 0 ? 'pos' : 'neg' },
    { icon: '●', label: 'Top Loser',  value: `${worst.symbol}  ${worst.change_pct.toFixed(2)}%`, cls: worst.change_pct < 0 ? 'neg' : 'pos' },
  ]
})

// ── Formatters ──────────────────────────────────────────────
const fmt    = v => `$${Math.abs(v).toFixed(2)}`
const fmtVol = v => v >= 1e9 ? `${(v/1e9).toFixed(1)}B` : v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v.toLocaleString()
const formatTime = iso => new Date(iso).toLocaleTimeString()

// ── Flash rows ──────────────────────────────────────────────
function applyFlash(newList) {
  const prev = Object.fromEntries(stocks.value.map(s => [s.id, s.price]))
  const map  = {}
  newList.forEach(s => {
    if (prev[s.id] === undefined) return
    if (s.price > prev[s.id]) map[s.id] = 'up'
    else if (s.price < prev[s.id]) map[s.id] = 'down'
  })
  flashMap.value = map
  setTimeout(() => { flashMap.value = {} }, 1600)
}

// ── Toast ───────────────────────────────────────────────────
function toast() {
  showToast.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { showToast.value = false }, 3200)
}

// ── WebSocket ───────────────────────────────────────────────
function connect() {
  connectionStatus.value = 'connecting'
  ws = new WebSocket('ws://localhost:8000/ws')

  ws.onopen = () => { connectionStatus.value = 'connected' }

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data)
    if (msg.type === 'update') {
      applyFlash(msg.stocks)
      toast()
      countdown.value = 60
    }
    stocks.value     = msg.stocks
    lastUpdated.value = msg.last_updated
    updateCount.value = msg.update_count ?? 0
  }

  ws.onclose = () => {
    connectionStatus.value = 'disconnected'
    setTimeout(connect, 3000)
  }

  ws.onerror = () => { connectionStatus.value = 'disconnected' }
}

// ── Lifecycle ────────────────────────────────────────────────
onMounted(() => {
  connect()
  tickTimer = setInterval(() => {
    countdown.value = Math.max(0, countdown.value - 1)
  }, 1000)
})

onUnmounted(() => {
  ws?.close()
  clearInterval(tickTimer)
  clearTimeout(toastTimer)
})
</script>

<style scoped>
/* ── Layout ──────────────────────────────────────── */
.app {
  min-height: 100vh;
  padding: 0 24px 48px;
  position: relative;
  overflow-x: hidden;
}

/* ── Background decorations ──────────────────────── */
.bg-grid {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(99,102,241,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,102,241,0.04) 1px, transparent 1px);
  background-size: 40px 40px;
}

.bg-glow {
  position: fixed; z-index: 0; pointer-events: none;
  width: 600px; height: 600px; border-radius: 50%;
  filter: blur(120px); opacity: 0.18;
}
.bg-glow--left  { top: -100px; left: -150px; background: var(--primary); }
.bg-glow--right { bottom: -100px; right: -150px; background: #06b6d4; }

/* ── Header ──────────────────────────────────────── */
.header {
  position: sticky; top: 0; z-index: 50;
  padding: 16px 0;
  background: rgba(6, 11, 20, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  margin: 0 -24px;
  padding-left: 24px; padding-right: 24px;
}
.header-inner {
  max-width: 1300px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between; gap: 24px;
}

.logo { display: flex; align-items: center; gap: 10px; }
.logo-icon { width: 28px; height: 28px; color: var(--primary); }
.logo-text  { font-size: 1.1rem; font-weight: 700; letter-spacing: -0.02em; }

.header-meta { display: flex; align-items: center; gap: 20px; }

.last-update { display: flex; flex-direction: column; align-items: flex-end; }
.meta-label  { font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.meta-value  { font-size: 0.82rem; color: var(--text-secondary); font-family: var(--mono); }

/* Countdown ring */
.countdown-wrap { display: flex; flex-direction: column; align-items: center; gap: 3px; }
.countdown-ring { position: relative; width: 44px; height: 44px; }
.ring-svg       { width: 100%; height: 100%; }
.ring-progress  { transition: stroke-dasharray 0.9s linear; }
.ring-label {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.62rem; font-family: var(--mono); color: var(--primary); font-weight: 500;
}

/* Connection badge */
.conn-badge {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 999px;
  font-size: 0.75rem; font-weight: 500;
  border: 1px solid transparent;
  transition: all 0.3s;
}
.conn-badge--connected    { border-color: var(--success); color: var(--success); background: var(--success-bg); }
.conn-badge--connecting   { border-color: rgba(251,191,36,0.4); color: #fbbf24; background: rgba(251,191,36,0.08); }
.conn-badge--disconnected { border-color: rgba(244,63,94,0.4); color: var(--danger); background: var(--danger-bg); }

.conn-dot {
  width: 7px; height: 7px; border-radius: 50%; background: currentColor;
  animation: pulse-dot 2s ease-in-out infinite;
}
.conn-badge--disconnected .conn-dot { animation: none; }

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}

/* ── Stats cards ──────────────────────────────────── */
.stats-row {
  max-width: 1300px; margin: 28px auto 0;
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
  position: relative; z-index: 1;
}

.stat-card {
  display: flex; align-items: center; gap: 14px;
  padding: 18px 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  backdrop-filter: blur(12px);
  transition: border-color 0.2s, transform 0.2s;
}
.stat-card:hover { border-color: var(--border-hover); transform: translateY(-1px); }

.stat-icon-wrap {
  width: 38px; height: 38px; border-radius: 10px;
  background: var(--primary-glow);
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; flex-shrink: 0;
}
.stat-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.stat-val   { font-size: 0.92rem; font-weight: 600; white-space: nowrap; }
.stat-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Table card ──────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  backdrop-filter: blur(12px);
  position: relative; z-index: 1;
}

.table-card { max-width: 1300px; margin: 20px auto 0; overflow: hidden; }

.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border);
}
.card-title-wrap { display: flex; align-items: baseline; gap: 10px; }
.card-title { font-size: 1rem; font-weight: 600; }
.row-count  { font-size: 0.72rem; color: var(--text-muted); }

.update-pill {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 12px; border-radius: 999px;
  font-size: 0.72rem; font-weight: 500; color: var(--primary);
  background: var(--primary-glow); border: 1px solid rgba(99,102,241,0.25);
}
.pulse {
  width: 7px; height: 7px; border-radius: 50%; background: var(--primary);
  animation: pulse-dot 1.6s ease-in-out infinite;
}

/* ── Table ───────────────────────────────────────── */
.table-scroll { overflow-x: auto; }

.market-table {
  width: 100%; border-collapse: collapse;
}
.market-table thead th {
  padding: 10px 16px;
  font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--text-muted);
  background: rgba(0,0,0,0.15);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.market-table thead th:first-child { padding-left: 24px; }
.market-table thead th:last-child  { padding-right: 24px; }

.mrow td {
  padding: 14px 16px;
  font-size: 0.875rem;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  transition: background 0.15s;
  vertical-align: middle;
}
.mrow:last-child td { border-bottom: none; }
.mrow td:first-child { padding-left: 24px; }
.mrow td:last-child  { padding-right: 24px; }

.mrow:hover td { background: rgba(99,102,241,0.04); }

/* Flash animations */
@keyframes flash-up {
  0%   { background-color: transparent; }
  25%  { background-color: rgba(16, 185, 129, 0.18); }
  100% { background-color: transparent; }
}
@keyframes flash-down {
  0%   { background-color: transparent; }
  25%  { background-color: rgba(244, 63, 94, 0.18); }
  100% { background-color: transparent; }
}

.mrow--up   td { animation: flash-up   1.6s ease-out; }
.mrow--down td { animation: flash-down 1.6s ease-out; }

/* Symbol tag */
.symbol-tag {
  display: inline-block;
  padding: 3px 8px; border-radius: 6px;
  font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em;
  font-family: var(--mono);
  background: rgba(99,102,241,0.12);
  color: #a5b4fc;
  border: 1px solid rgba(99,102,241,0.2);
}

.company-col { color: var(--text-secondary); white-space: nowrap; }
.mono  { font-family: var(--mono); font-size: 0.82rem; }
.muted { color: var(--text-secondary); }
.r     { text-align: right; }

/* Change delta */
.delta { font-family: var(--mono); font-size: 0.82rem; }

/* Percent badge */
.pct-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 6px;
  font-size: 0.77rem; font-weight: 600; font-family: var(--mono);
}
.arrow-icon { width: 8px; height: 8px; flex-shrink: 0; }

/* Colors */
.pos { color: var(--success); }
.neg { color: var(--danger); }
.pct-badge.pos { background: var(--success-bg); }
.pct-badge.neg { background: var(--danger-bg); }

/* ── Toast ───────────────────────────────────────── */
.toast {
  position: fixed; bottom: 28px; right: 28px; z-index: 100;
  display: flex; align-items: center; gap: 10px;
  padding: 12px 20px; border-radius: 12px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  backdrop-filter: blur(20px);
  color: var(--success);
  font-size: 0.85rem; font-weight: 500;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(16,185,129,0.1);
}
.toast-icon { width: 16px; height: 16px; flex-shrink: 0; }

.toast-enter-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.toast-leave-active { transition: all 0.25s ease-in; }
.toast-enter-from   { opacity: 0; transform: translateY(12px) scale(0.92); }
.toast-leave-to     { opacity: 0; transform: translateY(8px); }

/* ── Responsive ──────────────────────────────────── */
@media (max-width: 800px) {
  .stats-row { grid-template-columns: 1fr 1fr; }
  .app { padding: 0 12px 40px; }
  .header { padding-left: 12px; padding-right: 12px; margin: 0 -12px; }
  .header-meta { gap: 12px; }
  .countdown-wrap .meta-label { display: none; }
  .last-update { display: none; }
}
@media (max-width: 500px) {
  .stats-row { grid-template-columns: 1fr; }
}
</style>
