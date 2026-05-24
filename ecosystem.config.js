module.exports = {
  apps: [
    {
      name: "fastapi-server",
      script: "python3",
      args: "-m uvicorn backend.server:app --host 127.0.0.1 --port 8000",
      interpreter: "none",
      watch: false
    },
    {
      name: "ai-runner",
      script: "python3",
      args: "-m synap.runner",
      interpreter: "none",
      watch: false
    },
    {
      name: "ai-maintainer",
      script: "python3",
      args: "-m synap.maintainer",
      interpreter: "none",
      watch: false
    },
    {
      name: "trade-worker",
      script: "python3",
      args: "-m synap.worker",
      interpreter: "none",
      watch: false
    },
    {
      name: "volatility-ticker",
      script: "python3",
      args: "-m synap.ticker_poller",
      interpreter: "none",
      watch: false
    },
    {
      name: "telegram-bot",
      script: "python3",
      args: "-m synap.telegram_bot",
      interpreter: "none",
      watch: false
    },
    {
      name: "nansen-updater",
      script: "python3",
      args: "-m synap.nansen_updater",
      interpreter: "none",
    },
    {
      name: "websocket-service",
      script: "python3",
      args: "-m uvicorn backend.websocket_service:app --host 127.0.0.1 --port 8001",
      interpreter: "none",
      watch: false
    }
  ]
};
