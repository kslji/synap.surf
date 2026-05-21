import { useState, useEffect, useRef } from 'react';

const api = async (url) => { const r = await fetch(url); return r.json(); };

export function useDashboard() {
  const [stats, setStats] = useState({ equity: 0, pnl_pct: 0, win_rate: 0, realized_pnl: 0, total_trades: 0, positions: [], last_updated: '' });
  const [trades, setTrades] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [perps, setPerps] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [intel, setIntel] = useState({ market_view: 'Loading...', fear_greed: null, trending_coins: [], trending_narratives: [] });
  const [topCoins, setTopCoins] = useState([]);

  const fetchStats = async () => {
    try { const d = await api('/api/stats'); setStats(d); } catch(e) {}
  };
  const fetchTrades = async () => {
    try { const d = await api('/api/trades'); setTrades(d); } catch(e) {}
  };
  const fetchDecisions = async () => {
    try { const d = await api('/api/decisions'); setDecisions(d); } catch(e) {}
  };
  const fetchIntel = async () => {
    try { const d = await api('/api/market_intel'); setIntel(d); } catch(e) {}
  };
  const fetchPerps = async () => {
    try {
      const wRes = await fetch('/api/watchlist');
      const wData = await wRes.json();
      const userWatchlist = wData.watchlist || [];
      setWatchlist(userWatchlist);
      const res = await fetch('/api/hl_top_perps?t=' + Date.now());
      const data = await res.json();
      const ctxs = data.ctxs || [];
      const coins = ctxs.map(ctx => {
        const mark = parseFloat(ctx.markPx || 0), prev = parseFloat(ctx.prevDayPx || mark);
        return { name: ctx.name || '?', mark, chg: prev ? ((mark - prev) / prev) * 100 : 0, absChg: Math.abs(prev ? ((mark - prev) / prev) * 100 : 0) };
      });
      const sorted = coins.sort((a, b) => b.absChg - a.absChg);
      setPerps(sorted);
      setTopCoins(sorted.slice(0, 4).map(c => c.name));
    } catch(e) {}
  };

  const fetchAll = () => { fetchStats(); fetchTrades(); fetchDecisions(); fetchIntel(); fetchPerps(); };

  useEffect(() => {
    fetchAll();
    const i1 = setInterval(fetchAll, 15000);
    const i2 = setInterval(fetchPerps, 2 * 60 * 1000);
    return () => { clearInterval(i1); clearInterval(i2); };
  }, []);

  const saveWatchlist = async (list) => {
    await fetch('/api/watchlist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ watchlist: list }) });
    fetchPerps();
  };

  return { stats, trades, decisions, perps, watchlist, intel, topCoins, fetchAll, saveWatchlist };
}
