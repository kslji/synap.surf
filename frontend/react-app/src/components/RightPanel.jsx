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
  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-content" style={{ maxWidth: 400 }}>
        <span className="modal-close" onClick={onClose}>×</span>
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ margin: 0, fontSize: 24 }}>Telegram Setup</h2>
          <div style={{ color: 'var(--t3)', fontSize: 12, marginTop: 4 }}>Configure your bot notifications</div>
        </div>
        <div className="bot-config" style={{ background: 'var(--bg)', border: 'none' }}>
          <div className="bc-field" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 10 }}>
            <label style={{ fontSize: 11 }}>BOT TOKEN</label>
            <input 
              type="password" 
              placeholder="123456789:ABCdefGHI..." 
              style={{ width: '100%', textAlign: 'left', padding: '14px', borderRadius: 12 }} 
            />
          </div>
          <button className="bc-save-btn" style={{ width: '100%', marginTop: 24 }} onClick={onClose}>SAVE TELEGRAM CONFIG</button>
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
  const [aiEngine, setAiEngine] = useState('claude');
  const [hlOrderMode, setHlOrderMode] = useState('market');
  const [astOrderMode, setAstOrderMode] = useState('market');
  const [showTPSL, setShowTPSL] = useState(false);

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

  // Per-coin max leverage from Hyperliquid
  const [maxLeverage, setMaxLeverage] = useState(20);
  useEffect(() => {
    fetch(`/api/coin/leverage/${tradeCoin}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.max_leverage) { setMaxLeverage(d.max_leverage); setTradeLev(1); } })
      .catch(() => {});
  }, [tradeCoin]);

  const [botParams, setBotParams] = useState({
    MAX_CAPITAL_PER_TRADE_PCT: '5',
    MAX_LEVERAGE: '10',
    MAX_HOLD_HOURS: '24',
    MAX_OPEN_POSITIONS: '2',
    TARGET_ROE_PCT: 'AUTO',
    STOP_LOSS_PCT: 'AUTO'
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
      <aside className="right-panel">
        {tgModal && <TelegramModal onClose={() => setTgModal(false)} />}
        
        {/* HYPERLIQUID SECTION */}
        <section className="rp-section">
          <div className="rp-hdr"><h3>HYPERLIQUID</h3></div>
          <div className="trade-ticket">
            <div className="tt-tabs">
              <div style={{ display: 'flex', gap: 16 }}>
                <span className={`tt-tab ${hlOrderMode === 'market' ? 'active' : ''}`} onClick={() => setHlOrderMode('market')}>MARKET</span>
                <span className={`tt-tab ${hlOrderMode === 'limit' ? 'active' : ''}`} onClick={() => setHlOrderMode('limit')}>LIMIT</span>
              </div>
              <div className="bc-field" style={{ gap: 8 }}>
                <label style={{ fontSize: 9 }}>NOTIFS <span className="edit-link" onClick={() => setTgModal(true)}>Edit</span></label>
                <label className="switch mini">
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
          <div className="rp-hdr"><h3>ALGO AI BOT</h3></div>
          <div className="bot-config">
            {Object.entries(botParams).map(([key, val]) => {
              const isAutoCapable = key === 'TARGET_ROE_PCT' || key === 'STOP_LOSS_PCT';
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
                          onChange={(e) => handleBotChange(key, e.target.checked ? 'AUTO' : '10')}
                        />
                        AI AUTO
                      </label>
                    )}
                  </div>
                  <input 
                    type={isAuto ? "text" : "number"} 
                    value={isAuto ? "AUTO" : val} 
                    disabled={isAuto}
                    onChange={e => handleBotChange(key, e.target.value)} 
                    style={isAuto ? { opacity: 0.5, cursor: 'not-allowed', textAlign: 'center' } : {}}
                  />
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
                {['claude', 'grok'].map(m => (
                  <span key={m} className={`m-tgl${aiEngine === m ? ' active' : ''}`} onClick={() => setAiEngine(m)} style={{ fontSize: 8, padding: '4px 10px' }}>{m.toUpperCase()}</span>
                ))}
              </div>
            </div>
            <button className="bc-save-btn">SAVE PARAMETERS</button>
          </div>
        </section>
      </aside>
    );
  }

  return (
    <aside className="right-panel">
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
  );
}
