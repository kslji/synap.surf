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
    try { 
      const wallet = localStorage.getItem('wallet_address');
      if (!wallet || wallet === 'null') {
        setStats({ equity: 0, pnl_pct: 0, win_rate: 0, realized_pnl: 0, total_trades: 0, positions: [], last_updated: '' });
        return;
      }
      const d = await api(`/api/stats?wallet=${wallet}`); 
      if (localStorage.getItem('wallet_address') === wallet) setStats(d); 
    } catch(e) {}
  };
  const fetchTrades = async () => {
    try { 
      const wallet = localStorage.getItem('wallet_address');
      if (!wallet || wallet === 'null') {
        setTrades([]);
        return;
      }
      const d = await api(`/api/trades?wallet=${wallet}`); 
      if (localStorage.getItem('wallet_address') === wallet) setTrades(d); 
    } catch(e) {}
  };
  const fetchDecisions = async () => {
    try { 
      const wallet = localStorage.getItem('wallet_address');
      if (!wallet || wallet === 'null') {
        setDecisions([]);
        return;
      }
      const d = await api(`/api/decisions?wallet=${wallet}`); 
      if (localStorage.getItem('wallet_address') === wallet) setDecisions(d); 
    } catch(e) {}
  };
  const fetchIntel = async () => {
    try { 
      const d = await api('/api/market_intel'); 
      setIntel(d); 
    } catch(e) {}
  };
  const fetchPerps = async () => {
    try {
      const wRes = await fetch('/api/watchlist');
      const wData = await wRes.json();
      const userWatchlist = wData.watchlist || [];
      setWatchlist(userWatchlist);
      const res = await fetch('/api/volatility_ticker?t=' + Date.now());
      const data = await res.json();
      const coins = (Array.isArray(data) ? data : []).map(c => {
        return { 
          name: c.coin || '?', 
          mark: parseFloat(c.price || 0), 
          chg: (parseFloat(c.change_pct || 0)) * 100, 
          absChg: Math.abs(parseFloat(c.change_pct || 0)) * 100 
        };
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
    window.addEventListener('wallet_changed', fetchAll);
    return () => { 
      clearInterval(i1); 
      clearInterval(i2); 
      window.removeEventListener('wallet_changed', fetchAll); 
    };
  }, []);

  const saveWatchlist = async (list) => {
    await fetch('/api/watchlist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ watchlist: list }) });
    fetchPerps();
  };

  return { stats, trades, decisions, perps, watchlist, intel, topCoins, fetchAll, saveWatchlist };
}
