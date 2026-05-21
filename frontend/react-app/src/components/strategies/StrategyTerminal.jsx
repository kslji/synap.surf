import React, { useState, useEffect, useRef, Component } from 'react';
import BacktestChart from './BacktestChart';

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() { if (this.state.hasError) return <div style={{color:'red'}}>{this.state.error?.toString()}</div>; return this.props.children; }
}

function CustomDropdown({ options, value, onChange, label }) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOpt = options.find(o => o.value === value) || options[0];

  return (
    <div className="custom-dropdown" ref={ref} style={{ position: 'relative', width: '100%' }}>
      <div 
        className="exec-input-wrap" 
        onClick={() => setIsOpen(!isOpen)}
        style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
      >
        <span>{selectedOpt.label}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </div>
      {isOpen && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 8px)', left: 0, right: 0,
          background: 'rgba(26, 30, 35, 0.85)', backdropFilter: 'blur(12px)',
          border: '1px solid rgba(0, 229, 255, 0.15)',
          borderRadius: '12px', zIndex: 50, overflowY: 'auto', maxHeight: '280px',
          boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(0, 229, 255, 0.05)',
          padding: '6px'
        }}>
          {options.map(opt => (
            <div
              key={opt.value}
              onClick={() => { onChange(opt.value); setIsOpen(false); }}
              style={{
                padding: '12px 16px', fontSize: '13px', cursor: 'pointer',
                color: opt.value === value ? '#00e5ff' : 'var(--t2)',
                background: opt.value === value ? 'rgba(0, 229, 255, 0.1)' : 'transparent',
                borderRadius: '8px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                transition: 'all 0.2s ease',
                fontWeight: opt.value === value ? '600' : '400',
                marginBottom: '2px'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = opt.value === value ? 'rgba(0, 229, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)';
                e.currentTarget.style.color = opt.value === value ? '#00e5ff' : 'var(--t1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = opt.value === value ? 'rgba(0, 229, 255, 0.1)' : 'transparent';
                e.currentTarget.style.color = opt.value === value ? '#00e5ff' : 'var(--t2)';
              }}
            >
              {opt.label}
              {opt.value === value && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
export default function StrategyTerminal() {
  const [strategies, setStrategies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState('');
  const [capital, setCapital] = useState(1000);
  const [timeframe, setTimeframe] = useState('1h');
  const [coin, setCoin] = useState('BTC');
  const [coinOptions, setCoinOptions] = useState([{ value: 'BTC', label: 'Bitcoin (BTC)' }]);
  const [leverage, setLeverage] = useState(5);
  const [maxLeverage, setMaxLeverage] = useState(50);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [status, setStatus] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [walletBalance, setWalletBalance] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    // Fetch global coin options
    fetch('/api/coins')
      .then(r => r.json())
      .then(data => {
        if (data.coins) {
          setCoinOptions(data.coins.map(c => ({ value: c, label: c })));
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    // Fetch strategies
    fetch(`/api/strategies?coin=${coin}`)
      .then(r => r.json())
      .then(data => {
        setStrategies(data);
        if (data.length > 0) setSelected(data[0]);
      })
      .catch(console.error);
      
    // Fetch wallet balance
    const savedWallet = localStorage.getItem('hl_wallet');
    const url = savedWallet 
      ? `/api/wallet/balance?wallet=${encodeURIComponent(savedWallet)}`
      : '/api/wallet/balance';
      
    fetch(url)
      .then(r => r.json())
      .then(data => {
        if (data.configured) setWalletBalance(data);
      })
      .catch(console.error);

    // Fetch max leverage for selected coin
    fetch(`/api/coin/leverage/${coin}`)
      .then(r => r.json())
      .then(data => {
        if (data.max_leverage) {
          setMaxLeverage(data.max_leverage);
          setLeverage(prev => Math.min(prev, data.max_leverage));
        }
      })
      .catch(console.error);
  }, [coin]);

  const filtered = strategies.filter(s => 
    s.name.toLowerCase().includes(search.toLowerCase()) || 
    (s.tags && s.tags.some(t => t.toLowerCase().includes(search.toLowerCase())))
  );

  const handleExecuteBtnClick = () => {
    if (isExecuting) {
      setIsExecuting(false);
      setStatus('');
      return;
    }
    const avail = walletBalance ? parseFloat(walletBalance.available) : 0;
    if (parseFloat(capital) > avail) {
      setErrorMsg(`Insufficient funds. You only have $${avail.toFixed(2)} available.`);
      return;
    }
    setErrorMsg('');
    setShowConfirm(true);
  };

  const handleConfirmExecute = async () => {
    setShowConfirm(false);
    try {
      const wallet = localStorage.getItem('hl_wallet') || 'TEST_WALLET';
      const res = await fetch('/api/strategies/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: wallet,
          strategy_id: selected.id,
          coin,
          capital: parseFloat(capital),
          leverage: parseInt(leverage),
          timeframe
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to subscribe');
      
      setIsExecuting(true);
      setStatus(data.subscription_status);
      setErrorMsg('');
    } catch (e) {
      setErrorMsg(e.message);
    }
  };

  const handleBacktest = async () => {
    setIsBacktesting(true);
    try {
      const res = await fetch(`/api/strategies/${selected.id}/backtest?timeframe=${timeframe}&coin=${coin}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to run backtest');
      
      // Update the local state with new metrics and trades
      setStrategies(prev => prev.map(s => 
        s.id === selected.id ? { ...s, metrics: data.metrics, trades: data.trades } : s
      ));
      setSelected(prev => ({ ...prev, metrics: data.metrics, trades: data.trades }));
      
    } catch (e) {
      console.error("Backtest error:", e);
    } finally {
      setIsBacktesting(false);
    }
  };

  if (!selected) {
    return (
      <div style={{
        height: '100%', width: '100%', display: 'flex', flexDirection: 'column', 
        alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', color: 'var(--t1)'
      }}>
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          width="80" 
          height="80" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="#ff9f43" 
          strokeWidth="1.5" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          className="brain-loader"
          style={{ background: 'transparent' }}
        >
          <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/>
          <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/>
        </svg>
        <h3 style={{ 
          marginTop: '32px', letterSpacing: '4px', fontWeight: '900', 
          background: 'linear-gradient(90deg, #ff9f43, #feca57)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          animation: 'pulse-text 2s ease-in-out infinite'
        }}>
          INITIALIZING STRATEGIES...
        </h3>
      </div>
    );
  }

  const metrics = selected.metrics || {
    winRate: 0,
    totalPnl: 0,
    drawdown: 0,
    trades: 0
  };

  return (
    <div className="strategy-terminal">
      <aside className="strat-sidebar">
        <div className="strat-search">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input 
            placeholder="Search strategies..." 
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        
        <div className="strat-list">
          {filtered.map(strat => (
            <div 
              key={strat.id} 
              className={`strat-item${selected.id === strat.id ? ' active' : ''}`}
              onClick={() => setSelected(strat)}
            >
              <h4 style={{ color: selected.id === strat.id ? '#feca57' : 'var(--t1)', transition: 'color 0.2s' }}>{strat.name}</h4>
              <p style={{ 
                margin: '6px 0 12px 0', 
                fontSize: '11.5px', 
                color: selected.id === strat.id ? 'rgba(255, 159, 67, 0.9)' : 'var(--t2)', 
                lineHeight: '1.5',
                opacity: selected.id === strat.id ? 1 : 0.8,
                transition: 'color 0.2s'
              }}>
                {strat.description}
              </p>
              <div className="strat-tags">
                {strat.tags.map(t => <span key={t} className="strat-tag" style={{ 
                  background: selected.id === strat.id ? 'rgba(255, 159, 67, 0.15)' : 'rgba(255,255,255,0.05)', 
                  color: selected.id === strat.id ? '#ff9f43' : 'var(--t3)',
                  border: selected.id === strat.id ? '1px solid rgba(255, 159, 67, 0.3)' : '1px solid transparent',
                  transition: 'all 0.2s'
                }}>{t}</span>)}
              </div>
            </div>
          ))}
        </div>
      </aside>

      <main className="strat-main">
        <div className="strat-header-card">
          <div className="strat-title-wrap">
            <h2 style={{ color: '#feca57', textShadow: '0 2px 10px rgba(254, 202, 87, 0.2)' }}>{selected.name}</h2>
            <p style={{ 
              marginTop: '10px', 
              fontSize: '14px', 
              lineHeight: '1.6', 
              color: 'rgba(255, 159, 67, 0.9)',
              maxWidth: '85%'
            }}>
              {selected.description || 'High-performance algorithmic strategy from library.'}
            </p>
          </div>
          <div className="strat-tags">
            {selected.tags && selected.tags.map(t => (
              <span key={t} className="strat-tag" style={{ 
                fontSize: 11, padding: '6px 12px', 
                background: 'rgba(255, 159, 67, 0.15)', 
                color: '#ff9f43',
                border: '1px solid rgba(255, 159, 67, 0.4)',
                boxShadow: '0 4px 12px rgba(255, 159, 67, 0.1)'
              }}>{t}</span>
            ))}
          </div>
        </div>

        <div style={{ padding: '0 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 12, color: '#feca57', letterSpacing: 1.5, textShadow: '0 2px 10px rgba(254, 202, 87, 0.3)' }}>
              STRATEGY PERFORMANCE <span style={{color: 'rgba(255, 159, 67, 0.8)', fontSize: 10, marginLeft: 8}}>(1 Month Window)</span>
            </h3>
            <button 
              className={`beautiful-backtest-btn ${isBacktesting ? 'loading' : ''}`}
              onClick={handleBacktest} 
              disabled={isBacktesting}
              style={{
                background: 'linear-gradient(90deg, #ff9f43, #feca57)',
                border: 'none', color: '#1a1e23', fontWeight: 900,
                padding: '8px 24px', borderRadius: '12px',
                boxShadow: '0 6px 20px rgba(255,159,67,0.4)',
                cursor: isBacktesting ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: '10px',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                letterSpacing: 1, opacity: isBacktesting ? 0.7 : 1
              }}
              onMouseOver={e => !isBacktesting && (e.currentTarget.style.transform = 'translateY(-2px)')}
              onMouseOut={e => !isBacktesting && (e.currentTarget.style.transform = 'translateY(0)')}
            >
              {isBacktesting ? (
                <>
                  <div className="spinner-glow" style={{ borderTopColor: '#1a1e23', borderLeftColor: '#1a1e23', width: 14, height: 14 }}></div>
                  RUNNING SIMULATION...
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                  RUN BACKTEST
                </>
              )}
            </button>
          </div>
          
          <div className="strat-perf-grid">
            <div className="perf-card">
              <span className="label">WIN RATE</span>
              <span className="value highlight" style={{ color: '#ffffff', textShadow: '0 2px 8px rgba(255,255,255,0.3)' }}>{metrics.winRate}%</span>
            </div>
            <div className="perf-card">
              <span className="label">EST. PROFIT</span>
              <span className="value pos">+${metrics.totalPnl}</span>
            </div>
            <div className="perf-card">
              <span className="label">MAX DRAWDOWN</span>
              <span className="value neg">-{metrics.drawdown}%</span>
            </div>
            <div className="perf-card">
              <span className="label">TOTAL TRADES</span>
              <span className="value" style={{ color: '#ff9f43', textShadow: '0 2px 8px rgba(255,159,67,0.3)' }}>{metrics.trades}</span>
            </div>
          </div>
          
          <ErrorBoundary>
            <BacktestChart 
              symbol={coin} 
              interval={timeframe}
              trades={selected.trades || []}
            />
          </ErrorBoundary>
        </div>

        <div className="strat-execution-panel">
          <div className="rp-hdr" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
            <h3>STRATEGY DEPLOYMENT</h3>
          </div>
          
          <div className="exec-controls">
            <div className="exec-field">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label>INITIAL CAPITAL</label>
                {walletBalance && (
                  <span style={{ fontSize: '10px', color: '#fff', fontWeight: 700 }}>
                    Avail: <strong style={{ color: '#ff9f43', textShadow: '0 0 8px rgba(255,159,67,0.4)' }}>${parseFloat(walletBalance.available).toFixed(2)}</strong>
                  </span>
                )}
              </div>
              <div className="exec-input-wrap" style={{ 
                marginBottom: '8px', 
                border: errorMsg.includes('Insufficient') ? '1px solid var(--red)' : '1px solid var(--border)'
              }}>
                <span style={{ color: 'var(--t3)', marginRight: 10 }}>$</span>
                <input 
                  type="number" 
                  value={capital} 
                  onChange={e => {
                    setCapital(e.target.value);
                    if (errorMsg.includes('Insufficient')) setErrorMsg('');
                  }}
                  style={{ width: '100%' }}
                />
              </div>
              {walletBalance && (
                <div style={{ display: 'flex', gap: '4px' }}>
                  {[25, 50, 75, 100].map(pct => (
                    <button
                      key={pct}
                      onClick={() => setCapital(((pct / 100) * parseFloat(walletBalance.available)).toFixed(2))}
                      style={{
                        flex: 1, padding: '4px 0', fontSize: '10px', background: 'rgba(255, 159, 67, 0.1)',
                        border: '1px solid rgba(255, 159, 67, 0.3)', borderRadius: '4px', color: '#ff9f43', cursor: 'pointer',
                        fontWeight: 700, transition: 'all 0.2s'
                      }}
                      onMouseOver={e => { e.currentTarget.style.background = 'rgba(255, 159, 67, 0.2)'; }}
                      onMouseOut={e => { e.currentTarget.style.background = 'rgba(255, 159, 67, 0.1)'; }}
                    >
                      {pct}%
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="exec-field">
              <label>ASSET</label>
              <CustomDropdown 
                value={coin} 
                onChange={setCoin} 
                options={coinOptions}
              />
            </div>

            <div className="exec-field">
              <label>TIMEFRAME</label>
              <CustomDropdown 
                value={timeframe} 
                onChange={setTimeframe} 
                options={[
                  { value: '1m', label: '1 Minute' },
                  { value: '5m', label: '5 Minutes' },
                  { value: '15m', label: '15 Minutes' },
                  { value: '1h', label: '1 Hour' },
                  { value: '4h', label: '4 Hours' },
                  { value: '1d', label: '1 Day' },
                ]}
              />
            </div>

            <div className="exec-field">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <label>LEVERAGE</label>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#ff9f43', textShadow: '0 0 8px rgba(255,159,67,0.4)' }}>{leverage}x</span>
              </div>
              <input 
                type="range" 
                min="1" 
                max={maxLeverage} 
                step="1"
                value={leverage} 
                onChange={e => setLeverage(e.target.value)}
                style={{ width: '100%', cursor: 'pointer', accentColor: '#ff9f43' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '9px', color: 'rgba(255, 159, 67, 0.7)' }}>
                <span>1x</span>
                <span>{maxLeverage}x Max</span>
              </div>
            </div>
          </div>

          <button 
            className={`strat-exec-btn${isExecuting ? (status === 'WAITING' ? ' waiting' : ' active') : ''}`}
            onClick={handleExecuteBtnClick}
            style={{ 
              background: isExecuting 
                ? (status === 'WAITING' ? '#f5b301' : 'linear-gradient(90deg, #ff758c, #ff7eb3)') 
                : 'linear-gradient(90deg, #a55eea, #8854d0)',
              color: '#fff',
              border: 'none',
              boxShadow: isExecuting 
                ? (status === 'WAITING' ? '0 6px 20px rgba(245, 179, 1, 0.4)' : '0 6px 20px rgba(255, 117, 140, 0.4)') 
                : '0 6px 20px rgba(165, 94, 234, 0.4)',
              transition: 'all 0.3s ease',
              transform: 'translateY(0)'
            }}
            onMouseOver={e => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}
          >
            {isExecuting ? (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                </svg>
                {status === 'WAITING' ? 'WAITING FOR ENTRY' : 'STOP EXECUTION'}
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                EXECUTE STRATEGY
              </>
            )}
          </button>
          
          {errorMsg && <div style={{ fontSize: 11, color: 'var(--red)', textAlign: 'center', marginTop: 10 }}>{errorMsg}</div>}
          
          <div style={{ fontSize: 11, color: 'var(--t3)', textAlign: 'center', fontStyle: 'italic', marginTop: 8 }}>
            {isExecuting 
              ? (status === 'WAITING' ? 'Strategy is currently in a trade. You will enter on the next signal.' : 'Strategy active. Monitoring market for signals...') 
              : 'Select parameters and press execute to start automated trading.'}
          </div>
        </div>

        {showConfirm && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, backdropFilter: 'blur(4px)'
          }}>
            <div style={{
              background: 'var(--card)', padding: '24px', borderRadius: '16px',
              border: '1px solid var(--border)', maxWidth: '360px', width: '100%',
              boxShadow: '0 20px 40px rgba(0,0,0,0.4)', textAlign: 'center'
            }}>
              <h3 style={{ margin: '0 0 16px', color: 'var(--t1)' }}>Confirm Deployment</h3>
              <p style={{ margin: '0 0 24px', color: 'var(--t2)', fontSize: '13px', lineHeight: '1.5' }}>
                You are about to deploy <strong>${parseFloat(capital).toFixed(2)}</strong> on the <strong>{selected.name}</strong> strategy trading <strong>{coin}</strong> at <strong>{leverage}x</strong> leverage.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button 
                  onClick={() => setShowConfirm(false)}
                  style={{ flex: 1, padding: '12px', background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--t2)', borderRadius: '8px', cursor: 'pointer', fontWeight: 700 }}
                >
                  CANCEL
                </button>
                <button 
                  onClick={handleConfirmExecute}
                  style={{ flex: 1, padding: '12px', background: 'var(--accent)', border: 'none', color: '#fff', borderRadius: '8px', cursor: 'pointer', fontWeight: 700 }}
                >
                  CONFIRM
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
