import { useState, useEffect, useCallback } from 'react';
import { relTime } from '../utils.js';
import { useToast } from './Toast.jsx';

function SignalModal({ item, onClose }) {
  const t = item.data;
  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-content">
        <span className="modal-close" onClick={onClose}>×</span>
        <div className="modal-header" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <h2 style={{ margin: 0, fontSize: 24, fontWeight: 900 }}>{t.coin}</h2>
                <span className={`sc-type ${t.event?.toLowerCase().includes('open') ? 'long' : 'close'}`} style={{ fontSize: 10, padding: '4px 8px' }}>
                  {t.event?.replace('TRADE_', '')}
                </span>
              </div>
              <div style={{ color: 'var(--t3)', fontSize: 11, fontWeight: 700 }}>{relTime(item.timestamp)}</div>
            </div>
          </div>
        </div>
        
        <div className="modal-body">
          <div className="modal-reasoning-section" style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 16 }}>
            <h4 className="section-label" style={{ color: 'var(--accent)', marginBottom: 8 }}>AI REASONING</h4>
            <p className="reasoning-text" style={{ fontSize: 13, lineHeight: 1.6, opacity: 0.9 }}>
              {t.reasoning || t.details || t.reason}
            </p>
          </div>

          <div className="modal-stats-grid">
            {t.conviction && !isNaN(t.conviction) && (
              <div className="m-stat">
                <span className="m-label">CONVICTION</span>
                <span className="m-val highlight">{Math.round(t.conviction * 100)}%</span>
              </div>
            )}
            <div className="m-stat">
              <span className="m-label">SIDE</span>
              <span className={`m-val ${t.side?.toLowerCase() || 'long'}`}>{t.side || 'LONG'}</span>
            </div>
            <div className="m-stat">
              <span className="m-label">LEVERAGE</span>
              <span className="m-val">{t.leverage || '5'}x</span>
            </div>
            <div className="m-stat">
              <span className="m-label">AMOUNT</span>
              <span className="m-val">${t.position_size_usd || '100'}</span>
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
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-content" style={{ maxWidth: 500 }}>
        <span className="modal-close" onClick={onClose}>×</span>
        <div className="modal-header" style={{ marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 900, color: 'var(--t1)' }}>OPEN POSITIONS</h2>
        </div>
        <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          {!positions || positions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--t3)' }}>
              No active positions.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {positions.map((p, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <span style={{ fontSize: 16, fontWeight: 800, color: 'var(--t1)' }}>{p.coin}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: p.side === 'LONG' ? 'var(--accent)' : 'var(--red)' }}>{p.side} {p.leverage}x</span>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: p.pnl_usd >= 0 ? 'var(--accent)' : 'var(--red)' }}>
                        {p.pnl_usd >= 0 ? '+' : '-'}${Math.abs(p.pnl_usd).toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <button 
                    onClick={() => handleClose(p.coin)}
                    disabled={closingCoin === p.coin}
                    style={{ background: 'var(--t3)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: 11, fontWeight: 800, cursor: 'pointer' }}
                  >
                    {closingCoin === p.coin ? 'CLOSING...' : 'CLOSE'}
                  </button>
                </div>
              ))}
            </div>
          )}
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
  const positions = stats.positions || [];
  const rpnl = stats.realized_pnl || 0;
  const unpnl = positions.reduce((acc, p) => acc + (p.pnl_usd || 0), 0);

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
                  NOTIFS <span className="edit-link" onClick={() => setTgModal(true)}>Edit</span>
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
              <button onClick={fetchBalance} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', cursor: 'pointer', fontSize: 16, padding: 4, borderRadius: 8, transition: 'color 0.2s' }} title="Refresh balance">↻</button>
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
              <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>TELEGRAM NOTIFS <span className="edit-link" onClick={() => setTgModal(true)}>Edit</span></label>
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
      <section className="rp-section">
        <div className="rp-hdr">
          <h3>PERFORMANCE</h3>
          <div className="mini-toggle">
            {['bot', 'manual'].map(m => (
              <span key={m} className={`m-tgl${tradingMode === m ? ' active' : ''}`} onClick={() => setTradingMode(m)}>{m.toUpperCase()}</span>
            ))}
          </div>
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
            <span className="stat-val highlight">{stats.win_rate || '68'}%</span>
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
            : positions.map((p, i) => (
                <div key={i} className="pos-item">
                  <div className="pos-info">
                    <span className="pos-coin">{p.coin}</span>
                    <span className={`pos-side ${p.side?.toLowerCase()}`}>{p.side} {p.leverage}x</span>
                  </div>
                  <div className="pos-pnl">
                    <span className={`pnl-val ${p.pnl_usd >= 0 ? 'pos' : 'neg'}`}>
                      {p.pnl_usd >= 0 ? '+' : '-'}${Math.abs(p.pnl_usd).toFixed(2)}
                    </span>
                    <span className="pnl-pct">({p.pnl_pct.toFixed(2)}%)</span>
                  </div>
                </div>
              ))}
        </div>
      </section>

      <section className="rp-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="rp-hdr"><h3>AI SIGNALS</h3></div>
        <div className="signals-list">
          {decisions.slice(0, 10).map((d, i) => (
            <SignalCard key={i} item={d} onClick={() => setModal(d)} />
          ))}
        </div>
      </section>
    </aside>
    </div>
  );
}
