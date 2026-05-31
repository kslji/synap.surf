import { useState, useEffect, useCallback } from 'react';
import { relTime } from '../utils.js';
import { useToast } from './Toast.jsx';

function SignalModal({ item, onClose }) {
  const t = item.data;
  const isLong = t.side?.toUpperCase() === 'LONG';
  const isSkip = t.side?.toUpperCase() === 'SKIP';
  const themeColor = isSkip ? 'var(--t3)' : (isLong ? 'var(--green)' : 'var(--red)');
  const themeBg = isSkip ? 'rgba(255, 255, 255, 0.05)' : (isLong ? 'rgba(24, 184, 122, 0.05)' : 'rgba(233, 69, 96, 0.05)');
  const themeBorder = isSkip ? 'rgba(255, 255, 255, 0.1)' : (isLong ? 'rgba(24, 184, 122, 0.2)' : 'rgba(233, 69, 96, 0.2)');

  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()} style={{ backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
      <div className="modal-content" style={{ maxWidth: 500, width: '90%', background: 'var(--card)', border: `1px solid ${themeBorder}`, borderRadius: '16px', padding: 0, overflow: 'hidden', boxShadow: `0 20px 60px ${themeBg}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 28px', borderBottom: `1px solid ${themeBorder}`, background: `linear-gradient(to right, ${themeBg}, transparent)` }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <h2 style={{ margin: 0, fontSize: 26, fontWeight: 900, color: 'var(--t1)', letterSpacing: 1 }}>{t.coin}</h2>
              <span style={{ fontSize: 11, fontWeight: 800, padding: '4px 10px', borderRadius: '6px', background: isSkip ? 'rgba(255,255,255,0.1)' : (isLong ? 'rgba(24,184,122,0.15)' : 'rgba(233,69,96,0.15)'), color: themeColor, textTransform: 'uppercase', letterSpacing: 1 }}>
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
              <div style={{ background: 'var(--sub-bg)', border: '1px solid var(--border)', padding: '16px', borderRadius: '12px' }}>
                <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>CONVICTION</span>
                <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: 'var(--accent)' }}>{Math.round(t.conviction * 100)}%</span>
              </div>
            )}
            <div style={{ background: 'var(--sub-bg)', border: '1px solid var(--border)', padding: '16px', borderRadius: '12px' }}>
              <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>SIDE</span>
              <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: themeColor }}>{t.side || 'LONG'}</span>
            </div>
            <div style={{ background: 'var(--sub-bg)', border: '1px solid var(--border)', padding: '16px', borderRadius: '12px' }}>
              <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>LEVERAGE</span>
              <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: 'var(--t1)' }}>{t.leverage || '5'}x</span>
            </div>
            <div style={{ background: 'var(--sub-bg)', border: '1px solid var(--border)', padding: '16px', borderRadius: '12px' }}>
              <span style={{ display: 'block', fontSize: 11, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, marginBottom: 4 }}>PRICE</span>
              <span style={{ display: 'block', fontSize: 20, fontWeight: 900, color: 'var(--t1)' }}>{t.exit_price ? `$${t.exit_price}` : (t.entry_price ? `$${t.entry_price}` : (t.price ? `$${t.price}` : 'Market'))}</span>
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

function PositionsModal({ positions, onClose, handleClose, closingCoin }) {
  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()} style={{ backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="modal-content" style={{ maxWidth: 1000, width: '90%', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '16px', padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--t1)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'inline-block', width: 4, height: 16, background: 'var(--accent)', borderRadius: 2 }}></span>
            Active Positions
          </h2>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', fontSize: 24, cursor: 'pointer', padding: 0 }}>×</button>
        </div>
        
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'var(--sub-bg)', color: 'var(--t2)', fontSize: 13, fontWeight: 700 }}>
                <th style={{ padding: '16px 24px', fontWeight: 600 }}>Coin</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Size</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Position Value</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Entry Price</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Mark Price</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>PNL (ROE %)</th>
                <th style={{ padding: '16px', fontWeight: 600 }}>Liq. Price</th>
                <th style={{ padding: '16px 24px', fontWeight: 600 }}>Margin</th>
                <th style={{ padding: '16px 24px', fontWeight: 600 }}>Action</th>
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
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)', position: 'relative', transition: 'background 0.2s', ':hover': { background: 'rgba(255,255,255,0.02)' } }}>
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
                      <td style={{ padding: '16px 24px' }}>
                        <button 
                          onClick={() => handleClose(p.coin)}
                          disabled={closingCoin === p.coin}
                          style={{ background: 'rgba(233, 69, 96, 0.15)', color: 'var(--red)', border: 'none', padding: '6px 12px', borderRadius: '6px', fontSize: 11, fontWeight: 800, cursor: 'pointer', transition: 'background 0.2s' }}
                        >
                          {closingCoin === p.coin ? 'CLOSING...' : 'CLOSE'}
                        </button>
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
  if (t.side === 'SKIP') { type = 'SKIP'; typeCls = 'update'; meta = t.reasoning; }
  else if (t.event === 'TRADE_OPEN' || t.event === 'SIGNAL') { type = t.side === 'LONG' ? 'LONG' : 'SHORT'; typeCls = (t.side || 'LONG').toLowerCase(); meta = t.reasoning || `Entry $${t.entry_price}`; }
  else if (t.event === 'TRADE_CLOSE') { type = 'CLOSE'; typeCls = 'close'; meta = t.reasoning || `Exit $${t.exit_price} · PnL $${t.pnl_usd}`; }
  else if (t.event === 'TRADE_UPDATE') { type = 'UPDATE'; typeCls = 'update'; meta = t.reasoning || (t.action ? t.action.replace('_', ' ') : 'Risk Adjustment'); }
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
  const [marginMode, setMarginMode] = useState('cross');
  const [showTPSL, setShowTPSL] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [panelWidth, setPanelWidth] = useState(380);
  const [isResizing, setIsResizing] = useState(false);
  const showNotificationsComingSoon = () => {
    toast({
      type: 'info',
      title: 'Coming Soon',
      message: 'Trade notifications will be available in a future Synap Pro release.',
      duration: 4500,
    });
  };

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
  const [activeCoins, setActiveCoins] = useState(['BTC', 'ETH', 'SOL', 'HYPE', 'IMX', 'MERL', 'SUI', 'SEI', 'DOGE', 'LINK', 'AVAX', 'ARB']);
  
  useEffect(() => {
    fetch('/api/watchlist')
      .then(r => r.json())
      .then(d => {
        if (d && d.watchlist && d.watchlist.length > 0) {
          setActiveCoins(d.watchlist);
        }
      })
      .catch(() => {});
  }, []);

  const [tradeCoin, setTradeCoin] = useState('HYPE');
  const [coinDropOpen, setCoinDropOpen] = useState(false);
  const [coinSearch, setCoinSearch] = useState('');
  const [tradeSize, setTradeSize] = useState(0);
  const [tradeLev, setTradeLev] = useState(1);
  const [tradeLimitPrice, setTradeLimitPrice] = useState('');
  const [tpPrice, setTpPrice] = useState('');
  const [slPrice, setSlPrice] = useState('');
  const [tradeLoading, setTradeLoading] = useState(false);
  const [closingCoin, setClosingCoin] = useState(null);

  const handleClose = async (coin) => {
    setClosingCoin(coin);
    const w = localStorage.getItem('wallet_address');
    try {
      const res = await fetch('/api/trade/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coin, wallet_address: w })
      });
      if (res.ok) {
        window.dispatchEvent(new Event('wallet_changed'));
      }
    } catch (e) {}
    setClosingCoin(null);
  };

  // Wallet balance
  const [walletBalance, setWalletBalance] = useState(null);
  const [balRefreshing, setBalRefreshing] = useState(false);
  
  const fetchBalance = useCallback(async () => {
    const savedWallet = localStorage.getItem('wallet_address');
    if (!savedWallet || savedWallet === 'null') {
      setWalletBalance(null);
      return;
    }
    try {
      const url = `/api/wallet/balance?wallet=${encodeURIComponent(savedWallet)}`;
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
      if (!e.target.closest('[data-coin-drop]')) { setCoinDropOpen(false); setCoinSearch(''); }
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

  // All-coin leverage map fetched once from Hyperliquid
  const [coinLeverages, setCoinLeverages] = useState({});
  useEffect(() => {
    fetch('/api/coins/leverages')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.leverages) setCoinLeverages(d.leverages); })
      .catch(() => {});
  }, []);

  // Derive max leverage for selected coin; reset lever when coin changes
  const maxLeverage = coinLeverages[tradeCoin] ?? 20;
  useEffect(() => {
    setTradeLev(prev => Math.min(prev, coinLeverages[tradeCoin] ?? 20));
  }, [tradeCoin, coinLeverages]);

  const [botParams, setBotParams] = useState({
    MARGIN: '10',
    LEVERAGE: 'AUTO',
    TARGET_ROE_PCT: 'AUTO',
    STOP_LOSS_PCT: 'AUTO',
    ASSET: 'AUTO'
  });
  
  const [botActive, setBotActive] = useState(false);
  const [hasOpenPosition, setHasOpenPosition] = useState(false);
  const [savingBot, setSavingBot] = useState(false);

  // Fetch bot status on mount or when wallet changes
  useEffect(() => {
    const w = localStorage.getItem('wallet_address');
    if (!w) return;
    fetch(`/api/strategy/status?wallet_address=${encodeURIComponent(w)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) {
          setBotActive(d.is_active);
          setHasOpenPosition(d.has_open_position);
          if (d.params) {
            setBotParams({
              MARGIN: d.params.capital === 'AUTO' || d.params.capital == null ? 'AUTO' : d.params.capital.toString(),
              LEVERAGE: d.params.leverage === 'AUTO' || d.params.leverage == null ? 'AUTO' : d.params.leverage.toString(),
              TARGET_ROE_PCT: d.params.target_pct == null ? 'AUTO' : d.params.target_pct.toString(),
              STOP_LOSS_PCT: d.params.stop_loss_pct == null ? 'AUTO' : d.params.stop_loss_pct.toString(),
              ASSET: d.params.asset_name || 'AUTO'
            });
          }
        }
      })
      .catch(() => {});
  }, [walletBalance?.configured]);

  const handleBotChange = (key, val) => {
    setBotParams(prev => ({ ...prev, [key]: val }));
  };

  const saveBotParameters = async () => {
    const w = localStorage.getItem('wallet_address');
    if (!w) {
      toast({ type: 'error', title: 'Wallet Not Connected', message: 'Please connect wallet first' });
      return;
    }

    // Block execution if balance is under $10
    const balance = walletBalance?.balance ?? 0;
    if (!walletBalance?.configured || balance < 10) {
      toast({ 
        type: 'error', 
        title: 'Insufficient Balance', 
        message: 'cant take trade below 10$', 
        duration: 7000 
      });
      return;
    }
    
    const capital = botParams.MARGIN === 'AUTO' ? 0 : parseFloat(botParams.MARGIN) || 50;
    const lev = botParams.LEVERAGE === 'AUTO' ? 0 : parseInt(botParams.LEVERAGE) || 10;
    
    if (botParams.MARGIN !== 'AUTO' && capital < 10) {
      toast({ 
        type: 'error', 
        title: 'Minimum Margin Required', 
        message: 'A minimum margin of $10 is required to take an AI trade.', 
        duration: 7000 
      });
      return;
    }
    
    try {
      setSavingBot(true);
      const res = await fetch('/api/strategy/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: w,
          strategy_id: 'ALGO AI BOT',
          is_active: true,
          auto_risk: botParams.MARGIN === 'AUTO' || botParams.LEVERAGE === 'AUTO',
          capital: botParams.MARGIN === 'AUTO' ? 'AUTO' : capital,
          leverage: botParams.LEVERAGE === 'AUTO' ? 'AUTO' : lev,
          target_pct: botParams.TARGET_ROE_PCT === 'AUTO' ? null : parseFloat(botParams.TARGET_ROE_PCT),
          stop_loss_pct: botParams.STOP_LOSS_PCT === 'AUTO' ? null : parseFloat(botParams.STOP_LOSS_PCT),
          asset_name: botParams.ASSET,
          ai_engine: aiEngine.toUpperCase()
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to save');
      
      if (data.alert) {
        toast({ type: 'info', title: 'Status Update', message: data.alert, duration: 8000 });
      } else {
        toast({ type: 'success', title: 'Settings Saved', message: 'AI Bot Parameters Saved!', duration: 5000 });
      }
    } catch (e) {
      toast({ type: 'error', title: 'Error', message: e.message, duration: 7000 });
    } finally {
      setSavingBot(false);
      // Fetch fresh status to update the badge
      fetch(`/api/strategy/status?wallet_address=${encodeURIComponent(w)}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          if (d) {
            setBotActive(d.is_active);
            setHasOpenPosition(d.has_open_position);
          }
        }).catch(() => {});
    }
  };

  const stopBotParameters = async () => {
    const w = localStorage.getItem('wallet_address');
    if (!w) return;
    try {
      setSavingBot(true);
      const res = await fetch('/api/strategy/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: w,
          strategy_id: 'ALGO AI BOT',
          is_active: false,
          auto_risk: true,
          capital: "AUTO",
          leverage: "AUTO",
          asset_name: "AUTO",
          ai_engine: "CLAUDE"
        })
      });
      const data = await res.json();
      if (data.alert) {
        toast({ type: 'info', title: 'Status Update', message: data.alert, duration: 8000 });
      } else {
        toast({ type: 'success', title: 'Bot Stopped', message: 'Bot has been deactivated.', duration: 5000 });
      }
    } catch (e) {
      toast({ type: 'error', title: 'Error', message: e.message, duration: 7000 });
    } finally {
      setSavingBot(false);
      fetch(`/api/strategy/status?wallet_address=${encodeURIComponent(w)}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          if (d) {
            setBotActive(d.is_active);
            setHasOpenPosition(d.has_open_position);
          }
        }).catch(() => {});
    }
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
    WIF:  { emoji: '🐕', color: '#9945ff' },
    PEPE: { emoji: '🐸', color: '#00c853' },
    TIA:  { emoji: '☀️', color: '#7b61ff' },
    INJ:  { emoji: '🌀', color: '#00d2d3' },
    JUP:  { emoji: '⚡', color: '#ff9f43' },
    OP:   { emoji: '🔴', color: '#ff0420' },
    MATIC:{ emoji: '🔷', color: '#8247e5' },
    APT:  { emoji: '◆', color: '#00ccbb' },
  };
  const getCoinMeta = (c) => COIN_META[c] ?? { emoji: '●', color: '#8a8a8a' };
  // All tradeable HL perps from the leverage map; fall back to activeCoins while loading
  const allHlCoins = Object.keys(coinLeverages).length > 0
    ? Object.keys(coinLeverages).sort()
    : (activeCoins.length > 0 ? activeCoins : Object.keys(COIN_META));
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
      const w = localStorage.getItem('wallet_address');
      if (!w) {
        toast({ type: 'error', title: 'Wallet Not Connected', message: 'Please connect wallet first' });
        setTradeLoading(false);
        return;
      }

      // Immediate visual feedback — user knows the order is being processed
      const actionLabel = action === 'CLOSE' ? `Closing ${tradeCoin}` : `${action} ${tradeCoin}`;
      toast({ type: 'info', title: 'Placing Order', message: `${actionLabel} — waiting for Hyperliquid confirmation...`, duration: 10000 });

      let endpoint = '/api/trade/open';
      let payload = { coin: tradeCoin, wallet_address: w };
      
      if (action === 'CLOSE') {
        endpoint = '/api/trade/close';
      } else {
        payload = {
          ...payload,
          side: action,
          size_usd: (tradeSize || 0) * (tradeLev || 1),
          leverage: tradeLev || 1,
          is_limit: hlOrderMode === 'limit',
          margin_mode: marginMode,
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
      toast({ type: 'success', title: 'Order Confirmed', message: `${action} ${tradeCoin} filled on Hyperliquid.`, duration: 5000 });
      
      // Reset inputs and slider to default values
      setTradeSize(0);
      setTradeLev(1);
      setTradeLimitPrice('');
      setTpPrice('');
      setSlPrice('');
      setShowTPSL(false);
      
      // Trigger dashboard refresh
      window.dispatchEvent(new Event('wallet_changed'));
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
        {posModal && <PositionsModal positions={positions} onClose={() => setPosModal(false)} handleClose={handleClose} closingCoin={closingCoin} />}
        
        {/* HYPERLIQUID SECTION */}
        <section className="rp-section">
          <div className="rp-hdr"><h3>HYPERLIQUID</h3></div>
          <div className="trade-ticket">
            <div className="tt-tabs">
              <div style={{ display: 'flex', gap: 16 }}>
                <span className="tt-tab active" style={{ cursor: 'default' }}>TRADE</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <label style={{ fontSize: 9, fontWeight: 700, color: 'var(--t3)', display: 'flex', alignItems: 'center', gap: 6 }}>NOTIFS</label>
                <label
                  className="switch mini"
                  style={{ margin: 0, opacity: 0.55, cursor: 'not-allowed' }}
                  title="Coming soon: trade notifications will be available in a future Synap Pro release."
                  onClick={(e) => { e.preventDefault(); showNotificationsComingSoon(); }}
                >
                  <input type="checkbox" checked={false} readOnly disabled />
                  <span className="slider round" />
                </label>
              </div>
            </div>

            {/* Market / Limit + Cross / Isolated row */}
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ display: 'flex', flex: 1, background: 'var(--sub-bg)', borderRadius: 10, padding: 3, border: '1px solid var(--border)' }}>
                {['market', 'limit'].map(m => (
                  <button key={m} onClick={() => setHlOrderMode(m)} style={{ flex: 1, padding: '5px 0', fontSize: 10, fontWeight: 800, border: 'none', borderRadius: 8, cursor: 'pointer', transition: 'all 0.15s', background: hlOrderMode === m ? 'var(--accent)' : 'transparent', color: hlOrderMode === m ? '#fff' : 'var(--t3)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {m}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', flex: 1, background: 'var(--sub-bg)', borderRadius: 10, padding: 3, border: '1px solid var(--border)' }}>
                {['cross', 'isolated'].map(m => (
                  <button key={m} onClick={() => setMarginMode(m)} style={{ flex: 1, padding: '5px 0', fontSize: 10, fontWeight: 800, border: 'none', borderRadius: 8, cursor: 'pointer', transition: 'all 0.15s', background: marginMode === m ? (m === 'isolated' ? 'rgba(255,159,67,0.8)' : 'var(--accent)') : 'transparent', color: marginMode === m ? '#fff' : 'var(--t3)', textTransform: 'capitalize', letterSpacing: '0.3px' }}>
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* Wallet Balance */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'var(--sub-bg)', borderRadius: 12, border: '1px solid var(--border)', marginBottom: 4 }}>
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

            {/* Perps Overview */}
            {walletBalance?.configured && (
              <div style={{ background: 'var(--sub-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: '12px 14px' }}>
                <div style={{ fontSize: 9, fontWeight: 800, color: 'var(--t3)', letterSpacing: '1px', marginBottom: 10 }}>PERPS OVERVIEW</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 12px' }}>
                  {[
                    { label: 'PERPS BALANCE', value: `$${(walletBalance.balance || 0).toFixed(2)}` },
                    { label: 'UNREALIZED PNL', value: `${(walletBalance.unrealized_pnl || 0) >= 0 ? '+' : ''}$${(walletBalance.unrealized_pnl || 0).toFixed(2)}`, color: (walletBalance.unrealized_pnl || 0) >= 0 ? 'var(--green)' : 'var(--red)' },
                    { label: 'MARGIN RATIO', value: `${(walletBalance.cross_margin_ratio || 0).toFixed(1)}%`, color: (walletBalance.cross_margin_ratio || 0) > 80 ? 'var(--red)' : (walletBalance.cross_margin_ratio || 0) > 50 ? '#f5b301' : 'var(--t1)' },
                    { label: 'MAINT. MARGIN', value: `$${(walletBalance.maintenance_margin || 0).toFixed(2)}` },
                    { label: 'ACCOUNT LEV', value: `${(walletBalance.cross_account_leverage || 0).toFixed(2)}x`, color: (walletBalance.cross_account_leverage || 0) > 10 ? 'var(--red)' : (walletBalance.cross_account_leverage || 0) > 5 ? '#f5b301' : 'var(--t1)' },
                    { label: 'AVAILABLE', value: `$${(walletBalance.available || 0).toFixed(2)}`, color: 'var(--green)' },
                  ].map(({ label, value, color }) => (
                    <div key={label}>
                      <div style={{ fontSize: 9, fontWeight: 700, color: 'var(--t3)', marginBottom: 2 }}>{label}</div>
                      <div style={{ fontSize: 13, fontWeight: 800, color: color || 'var(--t1)' }}>{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Custom Coin Picker */}
            <div style={{ position: 'relative' }} data-coin-drop>
              <button
                onClick={() => setCoinDropOpen(o => !o)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                  background: 'var(--sub-bg)', border: '1px solid var(--border)',
                  borderRadius: 12, padding: '10px 14px', cursor: 'pointer', transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', borderRadius: '50%', background: 'var(--border)', border: '1px solid var(--border)', color: 'var(--t1)', fontSize: '12px', fontWeight: '800', flexShrink: 0 }}>
                  {tradeCoin.charAt(0).toUpperCase()}
                </div>
                <span style={{ fontWeight: 800, fontSize: 14, color: 'var(--t1)', flex: 1, textAlign: 'left', letterSpacing: '0.5px' }}>{tradeCoin}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: getCoinMeta(tradeCoin).color, background: `${getCoinMeta(tradeCoin).color}22`, padding: '2px 8px', borderRadius: 6 }}>PERP</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2.5" style={{ transform: coinDropOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}><polyline points="6 9 12 15 18 9"/></svg>
              </button>

              {coinDropOpen && (
                <div style={{
                  position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 999,
                  background: 'var(--card)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
                  border: '1px solid var(--border)', borderRadius: 14,
                  boxShadow: 'var(--shadow)', overflow: 'hidden',
                  animation: 'toastIn 0.18s ease',
                  display: 'flex', flexDirection: 'column',
                }}>
                  {/* Search box */}
                  <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', position: 'sticky', top: 0, background: 'var(--card)', zIndex: 1 }}>
                    <input
                      autoFocus
                      type="text"
                      placeholder="Search coin..."
                      value={coinSearch}
                      onChange={e => setCoinSearch(e.target.value.toUpperCase())}
                      onClick={e => e.stopPropagation()}
                      style={{ width: '100%', background: 'var(--sub-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 10px', color: 'var(--t1)', fontSize: 12, fontWeight: 700, outline: 'none', boxSizing: 'border-box' }}
                    />
                  </div>
                  {/* Coin list */}
                  <div style={{ maxHeight: 280, overflowY: 'auto' }}>
                    {allHlCoins.filter(c => !coinSearch || c.includes(coinSearch)).map(c => {
                      const m = getCoinMeta(c);
                      const active = c === tradeCoin;
                      const lev = coinLeverages[c];
                      return (
                        <button key={c} onClick={() => { setTradeCoin(c); setCoinDropOpen(false); setCoinSearch(''); setTradeLev(1); }} style={{
                          width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                          padding: '9px 14px', background: active ? `${m.color}18` : 'transparent',
                          border: 'none', borderBottom: '1px solid var(--border)',
                          cursor: 'pointer', transition: 'background 0.15s', textAlign: 'left',
                        }}
                        onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--sub-bg)'; }}
                        onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '20px', height: '20px', borderRadius: '50%', background: 'var(--border)', border: '1px solid var(--border)', color: 'var(--t1)', fontSize: '11px', fontWeight: '800', flexShrink: 0 }}>
                            {c.charAt(0).toUpperCase()}
                          </div>
                          <span style={{ flex: 1, fontWeight: 800, fontSize: 13, color: active ? m.color : 'var(--t1)', letterSpacing: '0.3px' }}>{c}</span>
                          {lev && <span style={{ fontSize: 9, fontWeight: 700, color: lev <= 5 ? '#ff9f43' : 'var(--t3)' }}>{lev}x</span>}
                          {active && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={m.color} strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Margin Slider */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <label style={{ fontSize: 9, fontWeight: 800, color: 'var(--t3)', letterSpacing: '0.5px' }}>MARGIN <span style={{ color: 'var(--t3)', fontWeight: 500, fontSize: 8 }}>(Min $10 total size)</span></label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    display: 'flex', alignItems: 'center',
                    background: 'var(--sub-bg)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '4px 8px',
                    transition: 'all 0.2s'
                  }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--t3)' }}>$</span>
                    <input
                      type="number"
                      className="no-spin"
                      value={tradeSize}
                      onChange={e => setTradeSize(e.target.value === '' ? '' : Number(e.target.value))}
                      style={{ fontSize: 16, fontWeight: 800, color: 'var(--t1)', background: 'transparent', border: 'none', width: '50px', outline: 'none', textAlign: 'right', paddingLeft: '4px' }}
                    />
                  </div>
                  {maxSize > 0 && <span style={{ fontSize: 10, color: 'var(--t3)', fontWeight: 600, minWidth: '35px' }}>({sizePercent}%)</span>}
                </div>
              </div>
              <div style={{ position: 'relative', height: 36, display: 'flex', alignItems: 'center' }}>
                <input
                  type="range" min={0} max={maxSize > 0 ? maxSize : 100} step={maxSize > 100 ? Math.max(1, Math.floor(maxSize / 200)) : 0.1}
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
                    style={{ fontSize: 10, fontWeight: 800, background: maxSize > 0 && sizePercent === pct ? 'var(--accent)' : 'var(--sub-bg)', color: maxSize > 0 && sizePercent === pct ? '#fff' : 'var(--t3)', border: '1px solid var(--border)', borderRadius: 8, padding: '4px 10px', cursor: maxSize > 0 ? 'pointer' : 'not-allowed', transition: 'all 0.15s', opacity: maxSize === 0 ? 0.4 : 1 }}>
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
                    style={{ fontSize: 10, fontWeight: 800, flex: 1, background: tradeLev === lv ? (lv >= maxLeverage * 0.8 ? 'var(--red)' : 'var(--accent)') : 'var(--sub-bg)', color: tradeLev === lv ? '#fff' : 'var(--t3)', border: '1px solid var(--border)', borderRadius: 8, padding: '4px 4px', cursor: 'pointer', transition: 'all 0.15s' }}>
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
              <button className="tt-btn close" style={{ background: '#6b7280', color: '#fff', gridColumn: 'span 2' }} onClick={() => handleTrade('CLOSE')} disabled={tradeLoading}>{tradeLoading ? '...' : 'CLOSE'}</button>
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

                    <button 
                      onClick={(e) => { e.stopPropagation(); handleClose(p.coin); }}
                      disabled={closingCoin === p.coin}
                      style={{ 
                        marginTop: 8, 
                        width: '100%',
                        background: 'rgba(233, 69, 96, 0.15)', 
                        color: 'var(--red)', 
                        border: 'none', 
                        padding: '8px 12px', 
                        borderRadius: '8px', 
                        fontSize: 11, 
                        fontWeight: 800, 
                        cursor: 'pointer', 
                        transition: 'background 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6
                      }}
                    >
                      {closingCoin === p.coin ? 'CLOSING...' : 'CLOSE POSITION'}
                    </button>
                  </div>
                  );
                })}
          </div>
        </section>

        {/* ALGO AI BOT SECTION */}
        <section className="rp-section">
          <div className="rp-hdr" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px 12px' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, margin: 0, whiteSpace: 'nowrap' }}>
              Synap.surf AI 
              <span className="limit-tooltip" data-tooltip="In the beta phase, users will be able to place one AI-powered order.." style={{ fontSize: 9, color: '#ff9f43', background: 'rgba(255, 159, 67, 0.1)', padding: '2px 6px', borderRadius: 4, fontWeight: 800, letterSpacing: '0.5px', textTransform: 'none', cursor: 'help', whiteSpace: 'nowrap' }}>ⓘ Limit</span>
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap' }}>
              {hasOpenPosition ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(24, 184, 122, 0.15)', padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(24, 184, 122, 0.3)' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 8px var(--green)', animation: 'pulse 2s infinite', flexShrink: 0 }} />
                  <span style={{ fontSize: 9, fontWeight: 900, color: 'var(--green)', letterSpacing: 0.5, whiteSpace: 'nowrap' }}>POSITION ACTIVE</span>
                </div>
              ) : botActive ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(0, 210, 211, 0.15)', padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(0, 210, 211, 0.3)' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 8px var(--accent)', flexShrink: 0 }} />
                  <span style={{ fontSize: 9, fontWeight: 900, color: 'var(--accent)', letterSpacing: 0.5, whiteSpace: 'nowrap' }}>SEARCHING TRADES</span>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(255, 255, 255, 0.05)', padding: '4px 10px', borderRadius: 6 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--t3)', flexShrink: 0 }} />
                  <span style={{ fontSize: 9, fontWeight: 900, color: 'var(--t3)', letterSpacing: 0.5, whiteSpace: 'nowrap' }}>INACTIVE</span>
                </div>
              )}
            </div>
          </div>
          <div className="bot-config">
            {Object.entries(botParams).map(([key, val]) => {
              const isAutoCapable = key === 'LEVERAGE' || key === 'TARGET_ROE_PCT' || key === 'STOP_LOSS_PCT' || key === 'ASSET';
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
                          onChange={(e) => handleBotChange(key, e.target.checked ? 'AUTO' : (key === 'ASSET' ? 'BTC' : (key === 'MARGIN' ? '10' : '10')))}
                        />
                        AI AUTO
                      </label>
                    )}
                  </div>
                  {key === 'ASSET' && !isAuto ? (
                    <div style={{ position: 'relative' }} data-bot-asset-drop>
                      <button 
                        onClick={() => setBotAssetDropOpen(o => !o)}
                        style={{ background: 'var(--sub-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 10px', color: 'var(--t1)', fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}
                      >
                        {val}
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2.5" style={{ transform: botAssetDropOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}><polyline points="6 9 12 15 18 9"/></svg>
                      </button>
                      {botAssetDropOpen && (
                        <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 4, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, zIndex: 100, boxShadow: 'var(--shadow)', width: 160 }}>
                          {activeCoins.map(c => (
                            <button key={c} onClick={() => { handleBotChange(key, c); setBotAssetDropOpen(false); }}
                              style={{ background: val === c ? 'rgba(0, 210, 211, 0.1)' : 'transparent', color: val === c ? 'var(--accent)' : 'var(--t2)', border: 'none', borderRadius: 6, padding: '6px 8px', fontSize: 11, fontWeight: 700, cursor: 'pointer', textAlign: 'left', transition: 'all 0.1s' }}
                              onMouseEnter={e => { if (val !== c) e.currentTarget.style.background = 'var(--sub-bg)'; }}
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
              <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>NOTIFS</label>
              <label
                className="switch mini"
                style={{ opacity: 0.55, cursor: 'not-allowed' }}
                title="Coming soon: trade notifications will be available in a future Synap Pro release."
                onClick={(e) => { e.preventDefault(); showNotificationsComingSoon(); }}
              >
                <input type="checkbox" checked={false} readOnly disabled />
                <span className="slider round" />
              </label>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              {botActive && (
                <button 
                  onClick={stopBotParameters} 
                  disabled={savingBot} 
                  style={{ 
                    flex: 1, 
                    background: 'rgba(233, 69, 96, 0.15)', 
                    color: 'var(--red)', 
                    border: '1px solid rgba(233, 69, 96, 0.3)', 
                    borderRadius: 8, 
                    fontSize: 13, 
                    fontWeight: 800, 
                    cursor: 'pointer', 
                    padding: '12px 0' 
                  }}
                >
                  STOP BOT
                </button>
              )}
              <button 
                className="bc-save-btn" 
                onClick={saveBotParameters} 
                disabled={savingBot}
                style={{ flex: botActive ? 2 : 1 }}
              >
                {savingBot ? 'SAVING...' : (botActive ? 'UPDATE PARAMS' : 'EXECUTE')}
              </button>
            </div>
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
      {posModal && <PositionsModal positions={positions} onClose={() => setPosModal(false)} handleClose={handleClose} closingCoin={closingCoin} />}
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
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleClose(p.coin); }}
                    disabled={closingCoin === p.coin}
                    style={{ 
                      marginTop: 8, 
                      width: '100%',
                      background: 'rgba(233, 69, 96, 0.15)', 
                      color: 'var(--red)', 
                      border: 'none', 
                      padding: '8px 12px', 
                      borderRadius: '8px', 
                      fontSize: 11, 
                      fontWeight: 800, 
                      cursor: 'pointer', 
                      transition: 'background 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6
                    }}
                  >
                    {closingCoin === p.coin ? 'CLOSING...' : 'CLOSE POSITION'}
                  </button>
                </div>
                );
              })}
        </div>
      </section>

      <section className="rp-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="rp-hdr"><h3>AI SIGNALS</h3></div>
        <div className="signals-list">
          {(!decisions || !Array.isArray(decisions) || decisions.length === 0) ? (
            <div className="pos-empty" style={{ flex: 1, minHeight: 200, margin: 0 }}>
              <div className="empty-icon">🤖</div>
              <span>NO AI SIGNALS YET</span>
              <p>AI trading signals will appear here automatically.</p>
            </div>
          ) : (
            decisions
              .filter(d => {
                const reasoning = d?.data?.reasoning || d?.reasoning || '';
                return !reasoning.includes('Manual UI');
              })
              .slice(0, 10).map((d, i) => (
              <SignalCard key={i} item={d} onClick={() => setModal(d)} />
            ))
          )}
        </div>
      </section>
    </aside>
    </div>
  );
}
