# MiroFish + Synap Setup Guide
## Mac Mini (16GB RAM) — Zero Error Configuration
## CHAIN -  sui , sol , bnb, btc , eth , avax, hype , xrp, ada , zec
---

## Why Model Choice Matters

Docker on Mac does **not** use the GPU — all inference runs on CPU via RAM.
Rule of thumb: the model must fit in **available Docker RAM** with ~1-2GB headroom.

| Machine | Docker RAM (safe) | Max Model Size |
|---|---|---|
| MacBook Air 8GB | ~3.7 GB | qwen2.5:3b / llama3.2:1b |
| MacBook Air 16GB | ~8 GB | qwen2.5:7b / llama3.1:8b |
| **Mac Mini 16GB** | **~10 GB** | **qwen2.5:14b / llama3.1:8b ✅** |
| Mac Mini 24GB | ~16 GB | qwen2.5:14b / llama3.3:70b-q4 |

---

## Step 1 — Set Docker Memory Limit

Before pulling any models, give Docker enough RAM:

1. Open **Docker Desktop**
2. Go to **Settings → Resources → Memory**
3. Set to **12 GB** (leaves 4GB for macOS)
4. Click **Apply & Restart**

> ⚠️ Without this step, models will fail with "requires more system memory" even on 16GB machines.

---

## Step 2 — Recommended Models for Mac Mini 16GB

### LLM (for ontology + simulation)

`qwen2.5:14b` is the best choice — smarter outputs, still fits comfortably.

```bash
docker exec -it $(docker ps | grep mirofish-ollama | awk '{print $1}') ollama pull qwen2.5:14b
```

Fallback if 14b is too slow for you:
```bash
docker exec -it $(docker ps | grep mirofish-ollama | awk '{print $1}') ollama pull qwen2.5:7b
```

### Embedding Model (required, same on all machines)

```bash
docker exec -it $(docker ps | grep mirofish-ollama | awk '{print $1}') ollama pull nomic-embed-text:latest
```

### Verify both are pulled

```bash
docker exec -it $(docker ps | grep mirofish-ollama | awk '{print $1}') ollama list
```

Expected output:
```
NAME                       SIZE
qwen2.5:14b                9.0 GB
nomic-embed-text:latest    274 MB
```

---

## Step 3 — Update MiroFish .env

Open `mirofish_engine/.env` and set:

```dotenv
LLM_MODEL_NAME=qwen2.5:14b
OPENAI_API_KEY=ollama
OPENAI_API_BASE_URL=http://mirofish-ollama:11434/v1
LLM_BASE_URL=http://mirofish-ollama:11434/v1
LLM_API_KEY=ollama

EMBEDDING_MODEL=nomic-embed-text:latest
EMBEDDING_BASE_URL=http://mirofish-ollama:11434

NEO4J_URI=bolt://mirofish-neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mirofish
```

> Do NOT change service names like `mirofish-ollama` or `mirofish-neo4j` — these are Docker internal hostnames.

---

## Step 4 — Restart MiroFish Backend

After updating `.env`, restart the backend container so it picks up the new model name:

```bash
docker restart $(docker ps | grep mirofish_engine | awk '{print $1}')
```

Or click **Stop → Start** on the `mirofish` container in Docker Desktop.

---

## Step 5 — Test the Full Stack

### Test Ollama is responding inside MiroFish network
```bash
docker exec -it $(docker ps | grep mirofish-ollama | awk '{print $1}') \
  ollama run qwen2.5:14b "Say hello in one sentence"
```

### Test MiroFish backend API
```bash
curl http://localhost:5001/health
```
Should return `{"status": "ok"}` or similar.

### Run your trading script
```bash
python main.py
```

You should now see the full simulation pipeline complete without 500 errors.

---

## Troubleshooting

### "model requires more system memory"
→ Docker RAM limit is too low. Go back to Step 1 and increase to 12GB.

### 500 on `/api/graph/ontology/generate`
→ Model isn't pulled into the `mirofish-ollama` container. Repeat Step 2.
→ Or the model name in `.env` doesn't match what `ollama list` shows exactly.

### Simulation runs but is very slow
→ Normal on CPU. `qwen2.5:7b` is faster if you prefer speed over quality:
```bash
# In .env:
LLM_MODEL_NAME=qwen2.5:7b
```

### Claude Brain 401 error
→ Unrelated to models. Your `ANTHROPIC_API_KEY` in the main `.env` has whitespace or isn't loading.
Add `.strip()` to wherever it's read in `synap/config.py`:
```python
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
```

### Wrong Ollama container targeted
The MiroFish stack has its **own** Ollama container (`mirofish-ollama`), separate from any other Ollama you may have installed. Always target it explicitly:
```bash
docker exec -it $(docker ps | grep mirofish-ollama | awk '{print $1}') ollama list
```

---

## Model Reference Card

| Model | Size | RAM Needed | Quality | Speed |
|---|---|---|---|---|
| llama3.2:1b | 1.3 GB | 2.5 GB | ⭐⭐ | ⚡⚡⚡⚡ |
| qwen2.5:3b | 1.9 GB | 3.2 GB | ⭐⭐⭐ | ⚡⚡⚡⚡ |
| qwen2.5:7b | 4.7 GB | 6.5 GB | ⭐⭐⭐⭐ | ⚡⚡⚡ |
| **qwen2.5:14b** | **9.0 GB** | **11 GB** | **⭐⭐⭐⭐⭐** | **⚡⚡** |
| llama3.1:8b | 4.9 GB | 6.5 GB | ⭐⭐⭐⭐ | ⚡⚡⚡ |

**Recommended for Mac Mini 16GB → `qwen2.5:14b`**


# BTC AI Grid Bot — Hyperliquid + Claude Sonnet

Single-coin BTC perpetual futures bot with Claude AI decisions.

## How It Works

```
every 60s
  └── fetch 50×4H candles from Hyperliquid
      └── write → candles/BTC_4h.csv
          └── NEW candle detected?
              ├── YES → ask Claude → LONG / SHORT / NO_TRADE
              │         ├── LONG  → place GTC limit entry (maker, below mid)
              │         │           + reduce-only GTC limit exit
              │         ├── SHORT → place GTC limit entry (maker, above mid)
              │         │           + reduce-only GTC limit exit
              │         └── NO_TRADE → HOLD (do nothing)
              └── NO  → sleep, wait
```

## Quick Start

```bash
# 1. Install deps
pip install hyperliquid-python-sdk anthropic eth-account

# 2. Set keys (never hardcode in production)
export ANTHROPIC_API_KEY="sk-ant-..."
export HL_PRIVATE_KEY="0x..."
export HL_WALLET="0x..."

# 3. Run (TESTNET first!)
#    Set USE_TESTNET = True in bot.py before going live
python bot.py
```

## Key Settings (bot.py)

| Variable | Default | Description |
|---|---|---|
| `USE_TESTNET` | `False` | ⚠️ Set `True` for paper trading |
| `NOTIONAL_PER_TRADE` | `$50` | USD size per trade |
| `DEFAULT_LEVERAGE` | `5` | Cross leverage |
| `CHECK_INTERVAL_SEC` | `60` | Poll frequency |
| `NUM_CANDLES` | `50` | Candles fetched from HL |
| `CANDLES_FOR_CLAUDE` | `20` | Candles sent to Claude |

## NO_TRADE Policy: HOLD

When Claude returns `NO_TRADE`, the bot does **nothing** — existing positions
and exit orders are left untouched. Claude may return `NO_TRADE` multiple
candles in a row while the existing trade plays out toward its exit target.

## Order Types

| Stage | Type | Details |
|---|---|---|
| Entry | GTC Limit (maker) | LONG: entry < mid · SHORT: entry > mid |
| Exit | Reduce-only GTC Limit | At Claude's `exit_price` |
| Emergency | Market close | Only on side-flip (LONG→SHORT or vice versa) |

## Files

```
candles/BTC_4h.csv          ← updated every 4H candle close
logs/bot.log                ← runtime log
logs/decisions_YYYYMMDD.jsonl   ← Claude's decisions (JSON lines)
logs/orders_YYYYMMDD.jsonl      ← placed orders
bot_state.json              ← last known state (survives restarts)
dashboard.html              ← browser monitoring UI
```

## Security

⚠️ Private keys must be in environment variables, not in the script.
⚠️ Always test on TESTNET (`USE_TESTNET = True`) before mainnet.