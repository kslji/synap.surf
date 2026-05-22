import { useState, useEffect, useCallback } from 'react';
import { relTime } from '../utils.js';
import { useToast } from './Toast.jsx';

function SignalModal({ item, onClose }) {
  const t = item.data;
  const isLong = t.side?.toUpperCase() !== 'SHORT';
  const themeColor = isLong ? 'var(--green)' : 'var(--red)';
  const themeBg = isLong ? 'rgba(24, 184, 122, 0.05)' : 'rgba(233, 69, 96, 0.05)';
  const themeBorder = isLong ? 'rgba(24, 184, 122, 0.2)' : 'rgba(233, 69, 96, 0.2)';

  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()} style={{ backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
      <div className="modal-content" style={{ maxWidth: 500, width: '90%', background: '#13171a', border: `1px solid ${themeBorder}`, borderRadius: '16px', padding: 0, overflow: 'hidden', boxShadow: `0 20px 60px ${themeBg}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 28px', borderBottom: `1px solid ${themeBorder}`, background: `linear-gradient(to right, ${themeBg}, transparent)` }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <h2 style={{ margin: 0, fontSize: 26, fontWeight: 900, color: '#fff', letterSpacing: 1 }}>{t.coin}</h2>
              <span style={{ fontSize: 11, fontWeight: 800, padding: '4px 10px', borderRadius: '6px', background: isLong ? 'rgba(24,184,122,0.15)' : 'rgba(233,69,96,0.15)', color: themeColor, textTransform: 'uppercase', letterSpacing: 1 }}>
                {t.event?.replace('TRADE_', '') || 'SIGNAL'}
              </span>
            </div>
            <div style={{ color: 'var(--t3)', fontSize: 12, fontWeight: 600 }}>{relTime(item.timestamp)}</div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', fontSize: 24, cursor: 'pointer', padding: 0, transition: 'color 0.2s' }}>×</button>
        </div>
        
        <div className="modal-body" style={{ padding: '32px 28px' }}>
          <div style={{ marginBottom: 32 }}>
            <h4 style={{ margin: '0 0 12px 0', fontSize: 13, fontWeight: 800, color: 'var(--accent)', letterSpacing: 1.5, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 10px var(--accent)' }}></span>
              AI REASONING
            </h4>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.7, color: 'var(--t1)', fontWeight: 500 }}>
              {t.reasoning || t.details || t.reason}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
            {t.conviction && !isNaN(t.conviction) && (
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px' }}>
                <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>CONVICTION</span>
                <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: 'var(--accent)' }}>{Math.round(t.conviction * 100)}%</span>
              </div>
            )}
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px' }}>
              <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>SIDE</span>
              <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: themeColor }}>{t.side || 'LONG'}</span>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px' }}>
              <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>LEVERAGE</span>
              <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: '#fff' }}>{t.leverage || '5'}x</span>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px' }}>
              <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>PRICE</span>
              <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: '#fff' }}>{t.entry_price ? `$${t.entry_price}` : (t.price ? `$${t.price}` : 'Market')}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TelegramModal({ onClose }) {
  const [tgToken, setTgToken] = useState('');
  const [tgChatId, setTgChatId] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch('/api/settings/keys').then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.telegram_bot_token) setTgToken(d.telegram_bot_token);
        if (d?.telegram_chat_id) setTgChatId(d.telegram_chat_id);
      }).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    await fetch('/api/settings/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ telegram_bot_token: tgToken, telegram_chat_id: tgChatId }),
    }).catch(() => {});
    setSaving(false);
    onClose();
  };

  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-content" style={{ maxWidth: 400 }}>
        <span className="modal-close" onClick={onClose}>×</span>
        <div className="modal-header" style={{ marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 900, color: 'var(--t1)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2.5"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
            Telegram Notifications
          </h2>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--t3)', lineHeight: 1.5 }}>
            Get instant alerts when the bot opens a trade, hits a take-profit, or hits a stop-loss.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--t2)' }}>BOT TOKEN</label>
            <input type="text" value={tgToken} onChange={e => setTgToken(e.target.value)} placeholder="123456789:ABCdefGHIjklMNOpqr..." style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', color: 'var(--t1)', fontSize: 13 }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--t2)' }}>CHAT ID</label>
            <input type="text" value={tgChatId} onChange={e => setTgChatId(e.target.value)} placeholder="e.g. -100123456789" style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', color: 'var(--t1)', fontSize: 13 }} />
          </div>
          <button onClick={handleSave} disabled={saving} style={{ background: 'var(--accent)', color: '#fff', border: 'none', padding: 12, borderRadius: 8, fontSize: 13, fontWeight: 800, cursor: 'pointer', marginTop: 8 }}>
            {saving ? 'SAVING...' : 'SAVE CONFIGURATION'}
          </button>
        </div>
      </div>
    </div>
  );
}

function PositionsModal({ positions, onClose }) {
  const [closingCoin, setClosingCoin] = useState(null);

  const handleClose = async (coin) => {
    setClosingCoin(coin);
    try {
      await fetch('/api/trade/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coin })
      });
    } catch (e) {}
    setClosingCoin(null);
  };

  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()} style={{ backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="modal-content" style={{ maxWidth: 1000, width: '90%', background: '#13171a', border: '1px solid var(--border)', borderRadius: '16px', padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--t1)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'inline-block', width: 4, height: 16, background: 'var(--accent)', borderRadius: 2 }}></span>
            Active Positions
          </h2>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', fontSize: 24, cursor: 'pointer', padding: 0 }}>×</button>
        </div>
        
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)', color: 'var(--t2)', fontSize: 13, fontWeight: 700 }}>
                <th style={{ padding: '16px 24px', fontWeight: 600 }}>Coin</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Size</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Position Value</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Entry Price</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Mark Price</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>PNL (ROE %)</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Liq. Price</th>
                <th style={{ padding: '16px 24px', fontWeight: 600 }}>Margin</th>
              </tr>
            </thead>
            <tbody>
              {!positions || positions.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: 'var(--t3)' }}>No active positions.</td>
                </tr>
              ) : (
                positions.map((p, i) => {
                  const isLong = p.side?.toUpperCase() === 'LONG';
                  const pnlUsd = p.pnl_usd !== undefined ? p.pnl_usd : (p.unrealized_pnl || 0);
                  const pnlPct = p.pnl_pct !== undefined ? p.pnl_pct : (p.unrealized_pnl_pct || 0);
                  const isPos = pnlUsd >= 0;
                  
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', position: 'relative', transition: 'background 0.2s', ':hover': { background: 'rgba(255,255,255,0.02)' } }}>
                      <td style={{ padding: '16px 24px' }}>
                        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: isLong ? 'var(--green)' : 'var(--red)' }}></div>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                          <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--t1)' }}>{p.coin}</span>
                          <span style={{ fontSize: 12, color: 'var(--t3)' }}>{p.leverage}x</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px', fontSize: 13, color: isLong ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                        {p.size} {p.coin}
                      </td>
                      <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>
                        {Number(p.size_usd || 0).toFixed(2)} USDC
                      </td>
                      <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>
                        {Number(p.entry_price || 0).toFixed(4)}
                      </td>
                      <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>
                        {Number(p.mark_price || p.entry_price || 0).toFixed(4)}
                      </td>
                      <td style={{ padding: '16px', fontSize: 13, color: isPos ? 'var(--green)' : 'var(--red)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                        {isPos ? '+' : '-'}${Math.abs(pnlUsd).toFixed(2)} ({isPos ? '+' : ''}{Number(pnlPct).toFixed(1)}%)
                        <a href={`https://app.hyperliquid.xyz/trade/${p.coin}`} target="_blank" rel="noreferrer" style={{ background: 'transparent', border: 'none', color: 'var(--t3)', cursor: 'pointer', padding: 0, display: 'flex', opacity: 0.7, textDecoration: 'none' }} title={`Trade ${p.coin} on Hyperliquid`}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        </a>
                      </td>
                      <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>
                        {Number(p.liquidation_price || 0).toFixed(4)}
                      </td>
                      <td style={{ padding: '16px 24px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>
                        ${Number(p.margin_used || 0).toFixed(2)} <span style={{ color: 'var(--t3)', fontWeight: 400 }}>({(p.leverage_type || 'cross').charAt(0).toUpperCase() + (p.leverage_type || 'cross').slice(1)})</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SignalCard({ item, onClick }) {
  const t = item.data;
  const time = relTime(item.timestamp);
  let type = 'SIGNAL', typeCls = 'signal', meta = t.reasoning || t.details || 'Analyzing opportunities...';
  if (t.event === 'TRADE_OPEN') { type = 'OPEN'; typeCls = (t.side || 'LONG').toLowerCase(); meta = t.reasoning || `Entry $${t.entry_price} · SL $${t.stop_loss}`; }
  else if (t.event === 'TRADE_CLOSE') { type = 'CLOSE'; typeCls = 'close'; meta = t.reasoning || `Exit $${t.exit_price} · PnL $${t.pnl_usd}`; }
  else if (t.event === 'TRADE_UPDATE') { type = 'UPDATE'; typeCls = 'update'; meta = t.reasoning || (t.action ? t.action.replace('_', ' ') : 'Risk Adjustment'); }
  else if (t.event === 'FILL') { type = 'FILL'; typeCls = 'update'; meta = t.details || `Manual fill at $${t.entry_price}`; }
  const conv = t.conviction ? Math.round(t.conviction * 100) : null;
  return (
    <div className="signal-card" onClick={onClick}>
      <div className="sc-top"><span className="sc-coin">{t.coin}</span><span className="sc-time">{time}</span></div>
      <div style={{ marginBottom: 6 }}><span className={`sc-type ${typeCls}`}>{type}</span></div>
      <div className="sc-desc">{meta}</div>
      {conv && <span className="conviction-chip">{conv}% conviction</span>}
    </div>
  );
}

export default function RightPanel({ view, stats, decisions, tradingMode, setTradingMode }) {
  const toast = useToast();
  const [modal, setModal] = useState(null);
  const [tgModal, setTgModal] = useState(false);
  const [posModal, setPosModal] = useState(false);
  const [aiEngine, setAiEngine] = useState('claude');
  const [hlOrderMode, setHlOrderMode] = useState('market');
  const [astOrderMode, setAstOrderMode] = useState('market');
  const [showTPSL, setShowTPSL] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [panelWidth, setPanelWidth] = useState(380);
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e) => {
      let newWidth = window.innerWidth - e.clientX;
      if (newWidth < 320) newWidth = 320;
      if (newWidth > 800) newWidth = 800;
      setPanelWidth(newWidth);
    };
    const handleMouseUp = () => setIsResizing(false);
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'none';
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  // New trade state
  const [tradeCoin, setTradeCoin] = useState('HYPE');
  const [coinDropOpen, setCoinDropOpen] = useState(false);
  const [tradeSize, setTradeSize] = useState(0);
  const [tradeLev, setTradeLev] = useState(1);
  const [tradeLimitPrice, setTradeLimitPrice] = useState('');
  const [tpPrice, setTpPrice] = useState('');
  const [slPrice, setSlPrice] = useState('');
  const [tradeLoading, setTradeLoading] = useState(false);

  // Wallet balance
  const [walletBalance, setWalletBalance] = useState(null);
  const [balRefreshing, setBalRefreshing] = useState(false);
  
  const fetchBalance = useCallback(async () => {
    try {
      const savedWallet = localStorage.getItem('hl_wallet');
      const url = savedWallet
        ? `/api/wallet/balance?wallet=${encodeURIComponent(savedWallet)}`
        : '/api/wallet/balance';
      const res = await fetch(url);
      if (res.ok) setWalletBalance(await res.json());
    } catch (_) {}
  }, []);
  useEffect(() => { fetchBalance(); }, [fetchBalance]);

  const handleFetchBalance = async () => {
    if (balRefreshing) return;
    setBalRefreshing(true);
    await fetchBalance();
    setTimeout(() => setBalRefreshing(false), 500);
  };

  // Close coin dropdown on outside click
  useEffect(() => {
    if (!coinDropOpen) return;
    const handler = (e) => {
      if (!e.target.closest('[data-coin-drop]')) setCoinDropOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [coinDropOpen]);

  // Close bot asset dropdown on outside click
  const [botAssetDropOpen, setBotAssetDropOpen] = useState(false);
  useEffect(() => {
    if (!botAssetDropOpen) return;
    const handler = (e) => {
      if (!e.target.closest('[data-bot-asset-drop]')) setBotAssetDropOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [botAssetDropOpen]);

  // Per-coin max leverage from Hyperliquid
  const [maxLeverage, setMaxLeverage] = useState(20);
  useEffect(() => {
    fetch(`/api/coin/leverage/${tradeCoin}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.max_leverage) { setMaxLeverage(d.max_leverage); setTradeLev(1); } })
      .catch(() => {});
  }, [tradeCoin]);

  const [botParams, setBotParams] = useState({
    MARGIN: '50',
    LEVERAGE: '10',
    MAX_HOLD_HOURS: '24',
    TARGET_ROE_PCT: 'AUTO',
    STOP_LOSS_PCT: 'AUTO',
    ASSET: 'AUTO'
  });

  const handleBotChange = (key, val) => {
    setBotParams(prev => ({ ...prev, [key]: val }));
  };

  const COIN_META = {
    BTC:  { emoji: '₿', color: '#f7931a' },
    ETH:  { emoji: 'Ξ', color: '#627eea' },
    SOL:  { emoji: '◎', color: '#9945ff' },
    HYPE: { emoji: '⚡', color: '#00d2d3' },
    IMX:  { emoji: '◈', color: '#17b2e8' },
    MERL: { emoji: '✦', color: '#e5643a' },
    SUI:  { emoji: '💧', color: '#4da2ff' },
    SEI:  { emoji: '🔴', color: '#ff4757' },
    DOGE: { emoji: '🐕', color: '#c3a634' },
    LINK: { emoji: '⬡', color: '#375bd2' },
    AVAX: { emoji: '🔺', color: '#e84142' },
    ARB:  { emoji: '◉', color: '#12aaff' },
  };
  const coins = Object.keys(COIN_META);
  const positions = (stats && Array.isArray(stats.positions)) ? stats.positions : [];
  const rpnl = Number(stats?.realized_pnl) || 0;
  const unpnl = stats?.unrealized_pnl !== undefined ? Number(stats.unrealized_pnl) : positions.reduce((acc, p) => acc + (Number(p?.pnl_usd !== undefined ? p.pnl_usd : p?.unrealized_pnl) || 0), 0);

  const handleTrade = async (action) => {
    if (tradeLoading) return;
    setTradeLoading(true);
    
    // Hyperliquid requires a minimum nominal size of $10
    if ((action === 'LONG' || action === 'SHORT') && (tradeSize * tradeLev < 10)) {
      toast({ 
        type: 'error', 
        title: 'Order Too Small', 
        message: 'Hyperliquid requires a minimum nominal order size of $10. Please increase your margin or leverage.', 
        duration: 7000 
      });
      setTradeLoading(false);
      return;
    }
    
    try {
      // Auto-sync wallet from localStorage to backend if available
      const savedWallet = localStorage.getItem('hl_wallet');
      if (savedWallet) {
        await fetch('/api/settings/keys', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hl_wallet: savedWallet }),
        }).catch(() => {});
      }

      let endpoint = '/api/trade/open';
      let payload = { coin: tradeCoin };
      
      if (action === 'CLOSE') {
        endpoint = '/api/trade/close';
      } else if (action === 'REVERSE') {
        endpoint = '/api/trade/reverse';
      } else {
        payload = {
          ...payload,
          side: action,
          size_usd: tradeSize || 0,
          leverage: tradeLev || 1,

          is_limit: hlOrderMode === 'limit',
        };
        if (hlOrderMode === 'limit' && tradeLimitPrice) payload.limit_price = parseFloat(tradeLimitPrice);
        if (showTPSL && tpPrice) payload.tp_price = parseFloat(tpPrice);
        if (showTPSL && slPrice) payload.sl_price = parseFloat(slPrice);
      }
      
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const text = await res.text();
      let data = {};
      try { data = JSON.parse(text); } catch (_) { /* non-JSON body */ }

      if (!res.ok) {
        const detail = data.detail || text || `HTTP ${res.status}`;
        throw new Error(detail);
      }
      toast({ type: 'success', title: 'Trade Submitted', message: `${action} on ${tradeCoin} executed successfully.`, duration: 5000 });
    } catch (err) {
      if (err.message.includes('Failed to fetch') || err.message.includes('ECONNREFUSED')) {
        toast({ type: 'error', title: 'Backend Offline', message: 'Server is not running. Start the backend and try again.', duration: 7000 });
      } else {
        toast({ type: 'error', title: 'Trade Failed', message: err.message, duration: 7000 });
      }
    } finally {
      setTradeLoading(false);
    }
  };

  if (view === 'charts') {
    const bal = walletBalance?.balance ?? 0;
    const avail = walletBalance?.available ?? 0;
    // Use actual available balance as slider max; only fall back to 1000 if wallet not yet configured
    const maxSize = walletBalance?.configured ? (avail > 0 ? avail : bal > 0 ? bal : 0) : 0;
    const sizePercent = maxSize > 0 ? Math.round((tradeSize / maxSize) * 100) : 0;

    // Quick leverage presets capped to the coin's real max
    const levPresets = [1, 5, 10, 20, 50].filter(l => l <= maxLeverage);
    if (!levPresets.includes(maxLeverage)) levPresets.push(maxLeverage);

    return (
      <div className={`rp-container ${isPanelOpen ? 'open' : 'closed'} ${isResizing ? 'resizing' : ''}`}>
        <div className="rp-resizer" onMouseDown={() => { setIsPanelOpen(true); setIsResizing(true); }} />
        <button className="rp-toggle-btn" onClick={() => setIsPanelOpen(!isPanelOpen)} title={isPanelOpen ? 'Collapse Panel' : 'Expand Panel'}>
          {isPanelOpen ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          )}
        </button>
        <aside className="right-panel" style={isPanelOpen ? { width: panelWidth } : {}}>
        {modal && <SignalModal item={modal} onClose={() => setModal(null)} />}
        {tgModal && <TelegramModal onClose={() => setTgModal(false)} />}
        {posModal && <PositionsModal positions={positions} onClose={() => setPosModal(false)} />}
        
        {/* HYPERLIQUID SECTION */}
        <section className="rp-section">
          <div className="rp-hdr"><h3>HYPERLIQUID</h3></div>
          <div className="trade-ticket">
            <div className="tt-tabs">
              <div style={{ display: 'flex', gap: 16 }}>
                <span className={`tt-tab ${hlOrderMode === 'market' ? 'active' : ''}`} onClick={() => setHlOrderMode('market')}>MARKET</span>
                <span className={`tt-tab ${hlOrderMode === 'limit' ? 'active' : ''}`} onClick={() => setHlOrderMode('limit')}>LIMIT</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <label style={{ fontSize: 9, fontWeight: 700, color: 'var(--t3)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  NOTIFS
                </label>
                <label className="switch mini" style={{ margin: 0 }}>
                  <input type="checkbox" defaultChecked />
                  <span className="slider round" />
                </label>
              </div>
            </div>
            
            {/* Wallet Balance */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 4 }}>
              <div>
                <div style={{ fontSize: 9, fontWeight: 800, color: 'var(--t3)', letterSpacing: '0.5px', marginBottom: 3 }}>ACCOUNT VALUE</div>
                 <div style={{ fontSize: 20, fontWeight: 900, color: 'var(--t1)', letterSpacing: '-0.5px' }}>
                   {walletBalance?.configured
                     ? `$${bal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                     : '$0.00'}
                 </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 9, fontWeight: 800, color: 'var(--t3)', letterSpacing: '0.5px', marginBottom: 3 }}>AVAILABLE</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--green)' }}>
                  {walletBalance?.configured ? `$${avail.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                </div>
              </div>
              <button onClick={handleFetchBalance} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', cursor: 'pointer', padding: 4, borderRadius: 8, transition: 'color 0.2s', display: 'flex', alignItems: 'center' }} title="Refresh balance">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ animation: balRefreshing ? 'spin 1s linear infinite' : 'none' }}>
                  <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
                  <path d="M21 3v5h-5" />
                </svg>
              </button>
            </div>

            {/* Custom Coin Picker */}
            <div style={{ position: 'relative' }} data-coin-drop>
              <button
                onClick={() => setCoinDropOpen(o => !o)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 12, padding: '10px 14px', cursor: 'pointer', transition: 'all 0.2s',
                }}
              >
                <span style={{ fontSize: 18, lineHeight: 1 }}>{COIN_META[tradeCoin]?.emoji}</span>
                <span style={{ fontWeight: 800, fontSize: 14, color: 'var(--t1)', flex: 1, textAlign: 'left', letterSpacing: '0.5px' }}>{tradeCoin}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: COIN_META[tradeCoin]?.color, background: `${COIN_META[tradeCoin]?.color}22`, padding: '2px 8px', borderRadius: 6 }}>PERP</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2.5" style={{ transform: coinDropOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}><polyline points="6 9 12 15 18 9"/></svg>
              </button>

              {coinDropOpen && (
                <div style={{
                  position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 999,
                  background: 'rgba(14,18,26,0.98)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
                  border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14,
                  boxShadow: '0 16px 48px rgba(0,0,0,0.6)', overflow: 'hidden',
                  animation: 'toastIn 0.18s ease',
                }}>
                  {coins.map(c => {
                    const m = COIN_META[c];
                    const active = c === tradeCoin;
                    return (
                      <button key={c} onClick={() => { setTradeCoin(c); setCoinDropOpen(false); }} style={{
                        width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                        padding: '10px 14px', background: active ? `${m.color}18` : 'transparent',
                        border: 'none', borderBottom: '1px solid rgba(255,255,255,0.04)',
                        cursor: 'pointer', transition: 'background 0.15s', textAlign: 'left',
                      }}
                      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                      onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                      >
                        <span style={{ fontSize: 16, width: 22, textAlign: 'center', lineHeight: 1 }}>{m.emoji}</span>
                        <span style={{ flex: 1, fontWeight: 800, fontSize: 13, color: active ? m.color : 'var(--t1)', letterSpacing: '0.3px' }}>{c}</span>
                        {active && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={m.color} strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Margin Slider */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <label style={{ fontSize: 9, fontWeight: 800, color: 'var(--t3)', letterSpacing: '0.5px' }}>MARGIN</label>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                  <span style={{ fontSize: 18, fontWeight: 900, color: 'var(--t1)' }}>${tradeSize.toLocaleString()}</span>
                  {maxSize > 0 && <span style={{ fontSize: 10, color: 'var(--t3)', fontWeight: 600 }}>({sizePercent}%)</span>}
                </div>
              </div>
              <div style={{ position: 'relative', height: 36, display: 'flex', alignItems: 'center' }}>
                <input
                  type="range" min={0} max={maxSize > 0 ? maxSize : 100} step={maxSize > 100 ? Math.max(1, Math.floor(maxSize / 200)) : 1}
                  value={tradeSize}
                  onChange={e => setTradeSize(Number(e.target.value))}
                  disabled={maxSize === 0}
                  style={{ width: '100%', accentColor: 'var(--accent)', cursor: maxSize > 0 ? 'pointer' : 'not-allowed', height: 4, opacity: maxSize === 0 ? 0.4 : 1 }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                {[25, 50, 75, 100].map(pct => (
                  <button key={pct}
                    onClick={() => maxSize > 0 && setTradeSize(Math.floor(maxSize * pct / 100))}
                    style={{ fontSize: 10, fontWeight: 800, background: maxSize > 0 && sizePercent === pct ? 'var(--accent)' : 'rgba(255,255,255,0.06)', color: maxSize > 0 && sizePercent === pct ? '#fff' : 'var(--t3)', border: 'none', borderRadius: 8, padding: '4px 10px', cursor: maxSize > 0 ? 'pointer' : 'not-allowed', transition: 'all 0.15s', opacity: maxSize === 0 ? 0.4 : 1 }}>
                    {pct}%
                  </button>
                ))}
              </div>
              {maxSize === 0 && <p style={{ fontSize: 10, color: 'var(--t3)', margin: 0, textAlign: 'center' }}>Connect wallet in Settings to set margin</p>}
            </div>

            {/* Leverage Slider */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <label style={{ fontSize: 9, fontWeight: 800, color: 'var(--t3)', letterSpacing: '0.5px' }}>LEVERAGE <span style={{ color: 'var(--t3)', fontWeight: 500, fontSize: 8 }}>(max {maxLeverage}× for {tradeCoin})</span></label>
                <span style={{ fontSize: 18, fontWeight: 900, color: tradeLev >= maxLeverage * 0.8 ? 'var(--red)' : tradeLev >= maxLeverage * 0.4 ? '#f5b301' : 'var(--t1)' }}>{tradeLev}×</span>
              </div>
              <input
                type="range" min={1} max={maxLeverage} step={1}
                value={tradeLev}
                onChange={e => setTradeLev(Number(e.target.value))}
                style={{ width: '100%', accentColor: tradeLev >= maxLeverage * 0.8 ? 'var(--red)' : tradeLev >= maxLeverage * 0.4 ? '#f5b301' : 'var(--accent)', cursor: 'pointer', height: 4 }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 4 }}>
                {levPresets.map(lv => (
                  <button key={lv} onClick={() => setTradeLev(lv)}
                    style={{ fontSize: 10, fontWeight: 800, flex: 1, background: tradeLev === lv ? (lv >= maxLeverage * 0.8 ? 'var(--red)' : 'var(--accent)') : 'rgba(255,255,255,0.06)', color: tradeLev === lv ? '#fff' : 'var(--t3)', border: 'none', borderRadius: 8, padding: '4px 4px', cursor: 'pointer', transition: 'all 0.15s' }}>
                    {lv}×
                  </button>
                ))}
              </div>
            </div>

            {hlOrderMode === 'limit' && (
              <div className="tt-row">
                <div className="tt-lev-input" style={{ width: '100%' }}>
                  <span style={{ fontSize: 9, color: 'var(--t3)', marginRight: 6 }}>LIMIT PRICE</span>
                  <input type="number" placeholder="0.00" style={{ textAlign: 'left' }} value={tradeLimitPrice} onChange={e => setTradeLimitPrice(e.target.value)} />
                </div>
              </div>
            )}

            <div className="tg-config-row">
              <div className="bc-field" style={{ width: '100%' }}>
                <label style={{ fontSize: 9 }}>TP / SL</label>
                <label className="switch mini">
                  <input type="checkbox" checked={showTPSL} onChange={() => setShowTPSL(!showTPSL)} />
                  <span className="slider round" />
                </label>
              </div>
            </div>

            {showTPSL && (
              <div className="tpsl-grid">
                <div className="tt-lev-input">
                  <span style={{ fontSize: 8, color: 'var(--t3)', marginRight: 4 }}>TP</span>
                  <input type="number" placeholder="Price" value={tpPrice} onChange={e => setTpPrice(e.target.value)} />
                </div>
                <div className="tt-lev-input">
                  <span style={{ fontSize: 8, color: 'var(--t3)', marginRight: 4 }}>SL</span>
                  <input type="number" placeholder="Price" value={slPrice} onChange={e => setSlPrice(e.target.value)} />
                </div>
              </div>
            )}

            <div className="tt-btns">
              <button className="tt-btn buy" onClick={() => handleTrade('LONG')} disabled={tradeLoading}>{tradeLoading ? '...' : 'LONG'}</button>
              <button className="tt-btn sell" onClick={() => handleTrade('SHORT')} disabled={tradeLoading}>{tradeLoading ? '...' : 'SHORT'}</button>
              <button className="tt-btn reverse" style={{ background: '#6c5ce7', color: '#fff' }} onClick={() => handleTrade('REVERSE')} disabled={tradeLoading}>{tradeLoading ? '...' : 'REVERSE'}</button>
              <button className="tt-btn close" style={{ background: 'var(--t3)', color: '#fff' }} onClick={() => handleTrade('CLOSE')} disabled={tradeLoading}>{tradeLoading ? '...' : 'CLOSE'}</button>
            </div>
          </div>
        </section>


        {/* ALGO AI BOT SECTION */}
        <section className="rp-section">
          <div className="rp-hdr">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              ALGO AI BOT 
              <span style={{ fontSize: 9, color: '#ff9f43', background: 'rgba(255, 159, 67, 0.1)', padding: '2px 6px', borderRadius: 4, fontWeight: 800, letterSpacing: '0.5px', textTransform: 'none' }}>(Max 2 positions)</span>
            </h3>
          </div>
          <div className="bot-config">
            {Object.entries(botParams).map(([key, val]) => {
              const isAutoCapable = key === 'TARGET_ROE_PCT' || key === 'STOP_LOSS_PCT' || key === 'ASSET';
              const isAuto = val === 'AUTO';
              return (
                <div key={key} className="bc-field" style={{ alignItems: isAutoCapable ? 'flex-start' : 'center' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <label>{key === 'TARGET_ROE_PCT' ? 'TARGET %' : key === 'STOP_LOSS_PCT' ? 'STOP LOSS %' : key.replace(/_/g, ' ')}</label>
                    {isAutoCapable && (
                      <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', fontSize: 9, color: 'var(--t3)', textTransform: 'none' }}>
                        <input 
                          type="checkbox" 
                          checked={isAuto} 
                          onChange={(e) => handleBotChange(key, e.target.checked ? 'AUTO' : (key === 'ASSET' ? 'BTC' : '10'))}
                        />
                        AI AUTO
                      </label>
                    )}
                  </div>
                  {key === 'ASSET' && !isAuto ? (
                    <div style={{ position: 'relative' }} data-bot-asset-drop>
                      <button 
                        onClick={() => setBotAssetDropOpen(o => !o)}
                        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '6px 10px', color: 'var(--t1)', fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}
                      >
                        {val}
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2.5" style={{ transform: botAssetDropOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}><polyline points="6 9 12 15 18 9"/></svg>
                      </button>
                      {botAssetDropOpen && (
                        <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 4, background: '#1e1e24', border: '1px solid var(--border)', borderRadius: 12, padding: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, zIndex: 100, boxShadow: '0 8px 24px rgba(0,0,0,0.6)', width: 160 }}>
                          {coins.map(c => (
                            <button key={c} onClick={() => { handleBotChange(key, c); setBotAssetDropOpen(false); }}
                              style={{ background: val === c ? 'rgba(0, 210, 211, 0.1)' : 'transparent', color: val === c ? 'var(--accent)' : 'var(--t2)', border: 'none', borderRadius: 6, padding: '6px 8px', fontSize: 11, fontWeight: 700, cursor: 'pointer', textAlign: 'left', transition: 'all 0.1s' }}
                              onMouseEnter={e => { if (val !== c) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                              onMouseLeave={e => { if (val !== c) e.currentTarget.style.background = 'transparent'; }}
                            >
                              {c}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <input 
                      type={(isAuto || key === 'ASSET') ? "text" : "number"} 
                      value={isAuto ? "AUTO" : val} 
                      disabled={isAuto}
                      onChange={e => handleBotChange(key, key === 'ASSET' ? e.target.value.toUpperCase() : e.target.value)} 
                      style={isAuto ? { opacity: 0.5, cursor: 'not-allowed', textAlign: 'center' } : {}}
                    />
                  )}
                </div>
              );
            })}
            <div className="bc-field" style={{ marginTop: 8 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>TELEGRAM NOTIFS</label>
              <label className="switch mini">
                <input type="checkbox" defaultChecked />
                <span className="slider round" />
              </label>
            </div>
            <div className="bc-field" style={{ marginTop: 16, marginBottom: 8 }}>
              <label style={{ fontSize: 9 }}>AI ENGINE</label>
              <div className="mini-toggle" style={{ background: 'var(--bg)', border: '1px solid var(--border)', width: 'fit-content' }}>
                <span className={`m-tgl${aiEngine === 'claude' ? ' active' : ''}`} onClick={() => setAiEngine('claude')} style={{ fontSize: 8, padding: '4px 10px' }}>CLAUDE</span>
                <span className="m-tgl grok-tooltip" data-tooltip="Right now Grok is unavailable" style={{ fontSize: 8, padding: '4px 10px', opacity: 0.5, cursor: 'not-allowed' }}>GROK</span>
              </div>
            </div>
            <button className="bc-save-btn">SAVE PARAMETERS</button>
            <button className="bc-save-btn" onClick={() => setPosModal(true)} style={{ marginTop: 8, background: 'rgba(255,255,255,0.05)', color: 'var(--t1)' }}>VIEW OPEN POSITIONS</button>
          </div>
        </section>
      </aside>
      </div>
    );
  }

  return (
    <div className={`rp-container ${isPanelOpen ? 'open' : 'closed'} ${isResizing ? 'resizing' : ''}`}>
      <div className="rp-resizer" onMouseDown={() => { setIsPanelOpen(true); setIsResizing(true); }} />
      <button className="rp-toggle-btn" onClick={() => setIsPanelOpen(!isPanelOpen)} title={isPanelOpen ? 'Collapse Panel' : 'Expand Panel'}>
        {isPanelOpen ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        )}
      </button>
      <aside className="right-panel" style={isPanelOpen ? { width: panelWidth } : {}}>
      {modal && <SignalModal item={modal} onClose={() => setModal(null)} />}
      {posModal && <PositionsModal positions={positions} onClose={() => setPosModal(false)} />}
      <section className="rp-section">
        <div className="rp-hdr">
          <h3>
            PERFORMANCE
            {stats?.is_last_20 && (
              <span style={{ fontSize: '10px', color: '#ff9f43', textTransform: 'none', marginLeft: '12px', fontWeight: '800', background: 'rgba(255, 159, 67, 0.1)', padding: '2px 8px', borderRadius: '6px', letterSpacing: '0' }}>
                (based on last 20 trades)
              </span>
            )}
          </h3>
        </div>
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="stat-card">
            <span className="stat-label">REALIZED</span>
            <span className={`stat-val ${rpnl >= 0 ? 'pos' : 'neg'}`}>{rpnl >= 0 ? '+' : '-'}${Math.abs(rpnl).toFixed(2)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">UNREALIZED</span>
            <span className={`stat-val ${unpnl >= 0 ? 'pos' : 'neg'}`}>{unpnl >= 0 ? '+' : '-'}${Math.abs(unpnl).toFixed(2)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">WIN RATE</span>
            <span className="stat-val highlight">{typeof stats.win_rate === 'number' ? stats.win_rate.toFixed(0) : '0'}%</span>
          </div>
        </div>
      </section>

      <section className="rp-section">
        <div className="rp-hdr"><h3>OPEN POSITIONS ({positions.length})</h3></div>
        <div className="positions-list">
          {!positions.length 
            ? <div className="pos-empty">
                <div className="empty-icon">📁</div>
                <span>NO ACTIVE POSITIONS</span>
                <p>Open trades will appear here automatically.</p>
              </div>
            : positions.map((p, i) => {
                const pnlUsd = p.pnl_usd !== undefined ? p.pnl_usd : (p.unrealized_pnl || 0);
                const pnlPct = p.pnl_pct !== undefined ? p.pnl_pct : (p.unrealized_pnl_pct || 0);
                return (
                <div key={i} className="pos-item" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '16px', padding: '16px', marginBottom: '12px', display: 'flex', flexDirection: 'column', gap: '12px', boxShadow: 'var(--shadow)', transition: 'all 0.2s ease', cursor: 'pointer' }}
                  onClick={() => setPosModal(true)}
                  onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.borderColor = p.side?.toUpperCase() === 'LONG' ? 'var(--green)' : 'var(--red)'; }}
                  onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.borderColor = 'var(--border)'; }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: p.side?.toUpperCase() === 'LONG' ? 'rgba(24, 184, 122, 0.1)' : 'rgba(233, 69, 96, 0.1)', color: p.side?.toUpperCase() === 'LONG' ? 'var(--green)' : 'var(--red)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', fontWeight: '900' }}>
                        {p.coin?.slice(0, 2)}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: '16px', fontWeight: '900', color: 'var(--t1)', lineHeight: '1.2' }}>{p.coin}</span>
                        <span style={{ fontSize: '11px', fontWeight: '800', color: p.side?.toUpperCase() === 'LONG' ? 'var(--green)' : 'var(--red)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          {p.side?.toUpperCase() === 'LONG' ? <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg> : <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/></svg>}
                          {p.side?.toUpperCase()} {p.leverage}x
                        </span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                      <span style={{ fontSize: '16px', fontWeight: '900', color: pnlUsd >= 0 ? 'var(--green)' : 'var(--red)', letterSpacing: '-0.5px' }}>
                        {pnlUsd >= 0 ? '+' : '-'}${Math.abs(pnlUsd).toFixed(2)}
                      </span>
                      <span style={{ fontSize: '11px', fontWeight: '800', color: pnlUsd >= 0 ? 'var(--green)' : 'var(--red)', background: pnlUsd >= 0 ? 'rgba(24, 184, 122, 0.1)' : 'rgba(233, 69, 96, 0.1)', padding: '2px 8px', borderRadius: '6px', marginTop: '4px' }}>
                        {pnlUsd >= 0 ? '+' : ''}{(Number(pnlPct) || 0).toFixed(2)}%
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed var(--border)', paddingTop: '12px', marginTop: '2px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '10px', fontWeight: '800', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Margin</span>
                      <span style={{ fontSize: '13px', fontWeight: '800', color: 'var(--t1)' }}>${(Number(p.size_usd) || 0).toFixed(2)}</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                      <span style={{ fontSize: '10px', fontWeight: '800', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Entry</span>
                      <span style={{ fontSize: '13px', fontWeight: '800', color: 'var(--t1)' }}>${Number(p.entry_price || 0).toFixed(4)}</span>
                    </div>
                  </div>
                </div>
                );
              })}
        </div>
      </section>

      <section className="rp-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="rp-hdr"><h3>AI SIGNALS</h3></div>
        <div className="signals-list">
          {(Array.isArray(decisions) ? decisions : []).slice(0, 10).map((d, i) => (
            <SignalCard key={i} item={d} onClick={() => setModal(d)} />
          ))}
        </div>
      </section>
    </aside>
    </div>
  );
}
