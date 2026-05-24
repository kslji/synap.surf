import React, { useState, useEffect, useRef, Component } from 'react';
import BacktestChart from './BacktestChart';
import { useToast } from '../Toast';

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
  const [capital, setCapital] = useState('100');
  const [timeframe, setTimeframe] = useState('1h');
  const [coin, setCoin] = useState('BTC');
  const [coinOptions, setCoinOptions] = useState([{ value: 'BTC', label: 'Bitcoin (BTC)' }]);
  const [leverage, setLeverage] = useState(10);
  const [marginMode, setMarginMode] = useState('cross');
  const [maxLeverage, setMaxLeverage] = useState(50);
  const [targetPct, setTargetPct] = useState('2');
  const [stopLossPct, setStopLossPct] = useState('1');
  const [isExecuting, setIsExecuting] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [status, setStatus] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [walletBalance, setWalletBalance] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [activeStrategyInfo, setActiveStrategyInfo] = useState(null);
  const [showConflictModal, setShowConflictModal] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [panelWidth, setPanelWidth] = useState(280);
  const [isResizing, setIsResizing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const togglePanel = () => {
    const opening = !isPanelOpen;
    setIsPanelOpen(opening);
    if (opening) setIsSidebarOpen(false);
  };

  const toggleSidebar = () => {
    const opening = !isSidebarOpen;
    setIsSidebarOpen(opening);
    if (opening) setIsPanelOpen(false);
  };

  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e) => {
      let w = window.innerWidth - e.clientX;
      if (w < 220) w = 220;
      if (w > 600) w = 600;
      setPanelWidth(w);
    };
    const onUp = () => setIsResizing(false);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    document.body.style.userSelect = 'none';
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  const [liveTrades, setLiveTrades] = useState([]);
  const [positions, setPositions] = useState([]);
  const [closingCoin, setClosingCoin] = useState(null);
  const [posModal, setPosModal] = useState(false);

  const fetchPositions = () => {
    const w = localStorage.getItem('wallet_address');
    if (!w || w === 'null') return;
    fetch(`/api/stats?wallet=${encodeURIComponent(w)}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.positions) setPositions(data.positions); })
      .catch(() => {});
  };

  const handleClosePosition = async (coin) => {
    const w = localStorage.getItem('wallet_address');
    if (!w || closingCoin) return;
    setClosingCoin(coin);
    try {
      await fetch('/api/close_position', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: w, coin }),
      });
      setTimeout(fetchPositions, 1500);
    } catch (e) { console.error(e); }
    finally { setClosingCoin(null); }
  };

  const fetchActiveStrategy = () => {
    const w = localStorage.getItem('wallet_address');
    if (!w || w === 'null') return;
    fetch(`/api/strategy/active?wallet_address=${encodeURIComponent(w)}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setActiveStrategyInfo(data); else setActiveStrategyInfo(null); })
      .catch(() => setActiveStrategyInfo(null));
  };

  useEffect(() => {
    fetchActiveStrategy();
    fetchPositions();
    const posInterval = setInterval(fetchPositions, 10000);
    return () => clearInterval(posInterval);
  }, []);

  useEffect(() => {
    // Fetch global coin options
    fetch('/api/coins/leverages')
      .then(r => r.json())
      .then(data => {
        if (data.leverages) {
          const allCoins = Object.keys(data.leverages).sort();
          setCoinOptions(allCoins.map(c => ({ 
            value: c, 
            label: (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  width: '20px', height: '20px', borderRadius: '50%',
                  background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)',
                  color: '#ffffff', fontSize: '11px', fontWeight: '800', flexShrink: 0
                }}>
                  {c.charAt(0).toUpperCase()}
                </div>
                <span style={{ fontWeight: '600' }}>{c}</span>
              </div>
            ) 
          })));
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selected) return;
    const w = localStorage.getItem('wallet_address');
    if (!w || w === 'null') return;
    
    // Fetch live trades for this strategy
    fetch(`/api/trade/logs/strategy/${selected.id}?wallet_address=${encodeURIComponent(w)}`)
      .then(r => r.ok ? r.json() : {logs: []})
      .then(data => {
        if (data && data.logs) {
          const formatted = data.logs.map(t => ({
            time: Math.floor(new Date(t.timestamp).getTime() / 1000),
            price: t.entry_price || t.size_usd,
            side: t.side === 'LONG' ? 'buy' : 'sell',
            text: `Live ${t.event.replace('TRADE_', '')} (${t.side})`,
            color: t.event === 'TRADE_OPEN' ? '#00e5ff' : '#ff9f43'
          }));
          setLiveTrades(formatted);
        }
      })
      .catch(() => setLiveTrades([]));
  }, [selected?.id]);

  const [lastLogId, setLastLogId] = useState(null);
  const lastLogIdRef = useRef(null);

  const toast = useToast();
  const toastRef = useRef(toast);
  useEffect(() => { toastRef.current = toast; }, [toast]);

  useEffect(() => {
    // Fetch strategies
    fetch(`/api/strategies?coin=${coin}`)
      .then(r => r.json())
      .then(data => {
        setStrategies(data || []);
        if (data && data.length > 0 && !selected) setSelected(data[0]);
      })
      .catch(console.error);
      
    // Fetch wallet balance
    const savedWallet = localStorage.getItem('wallet_address');
    if (!savedWallet || savedWallet === 'null') {
      setWalletBalance(null);
    } else {
      fetch(`/api/wallet/balance?wallet=${encodeURIComponent(savedWallet)}`)
        .then(r => r.json())
        .then(data => {
          if (data.configured) setWalletBalance(data);
        })
        .catch(console.error);
    }

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

  useEffect(() => {
    if (!selected) return;
    const savedWallet = localStorage.getItem('wallet_address');
    if (!savedWallet || savedWallet === 'null') return;

    // Poll for status and trade logs
    const checkStatusAndLogs = async () => {
      try {
        const [statusRes, logsRes] = await Promise.all([
          fetch(`/api/strategy/status?wallet_address=${encodeURIComponent(savedWallet)}&strategy_id=${encodeURIComponent(selected.id)}`),
          fetch(`/api/trade/logs/strategy/${selected.id}?wallet_address=${encodeURIComponent(savedWallet)}&limit=1`)
        ]);

        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (statusData.subscription_status === 'ACTIVE' || statusData.subscription_status === 'WAITING') {
            setIsExecuting(true);
            setStatus(statusData.subscription_status);
            if (statusData.asset_name && statusData.asset_name !== 'AUTO') setCoin(statusData.asset_name);
          } else {
            setIsExecuting(false);
            setStatus('');
          }
        }

        if (logsRes.ok) {
          const logsData = await logsRes.json();
          if (logsData.logs && logsData.logs.length > 0) {
            const latestLog = logsData.logs[0];
            if (lastLogIdRef.current && lastLogIdRef.current !== latestLog._id) {
              toastRef.current({
                type: 'success',
                title: 'Order Executed',
                message: `Your ${latestLog.side} order for ${latestLog.coin} has been executed by the AI bot!`,
                duration: 8000
              });
            }
            lastLogIdRef.current = latestLog._id;
            setLastLogId(latestLog._id);
          }
        }
      } catch (e) {
        console.error("Failed to check status/logs:", e);
      }
    };

    checkStatusAndLogs();
    const interval = setInterval(checkStatusAndLogs, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [selected?.id]);

  const filtered = strategies.filter(s => 
    s.name.toLowerCase().includes(search.toLowerCase()) || 
    (s.tags && s.tags.some(t => t.toLowerCase().includes(search.toLowerCase())))
  );

  const notifyBacktestRequired = () => {
    toast({ 
      type: 'info', 
      title: 'Action Required', 
      message: 'Please click RUN BACKTEST to simulate this strategy on historical data.\nStay Updated !!', 
      duration: 5000 
    });
  };

  const handleDeactivateCurrent = async () => {
    const wallet = localStorage.getItem('wallet_address') || '';
    const stratId = activeStrategyInfo?.strategy_id || selected.id;
    try {
      await fetch('/api/strategy/unsubscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: wallet, strategy_id: stratId })
      });
    } catch (e) { console.error(e); }
    setIsExecuting(false);
    setStatus('');
    setActiveStrategyInfo(null);
    setShowConflictModal(false);
  };

  const handleExecuteBtnClick = async () => {
    if (isExecuting) {
      // Unsubscribe from current strategy
      const wallet = localStorage.getItem('wallet_address') || '';
      try {
        await fetch('/api/strategy/unsubscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ wallet_address: wallet, strategy_id: selected.id })
        });
      } catch (e) { console.error(e); }
      setIsExecuting(false);
      setStatus('');
      setActiveStrategyInfo(null);
      return;
    }

    // Block if a DIFFERENT strategy is already active
    if (activeStrategyInfo && activeStrategyInfo.strategy_id !== selected.id) {
      setShowConflictModal(true);
      return;
    }

    const avail = walletBalance ? parseFloat(walletBalance.available) : 0;
    const cap = parseFloat(capital);

    if (cap < 10) {
      toast({ type: 'error', title: 'Minimum Capital Required', message: 'A minimum of $10 is required to execute a strategy trade.' });
      return;
    }
    if (cap > avail) {
      setErrorMsg(`Insufficient funds. You only have $${avail.toFixed(2)} available.`);
      return;
    }
    setErrorMsg('');
    setShowConfirm(true);
  };

  const handleConfirmExecute = async () => {
    setShowConfirm(false);
    const cap = parseFloat(capital);
    try {
      const wallet = localStorage.getItem('wallet_address') || 'TEST_WALLET';
      const payload = { 
        wallet_address: wallet, 
        strategy_id: selected.id, 
        capital: cap, 
        leverage: leverage,
        coin, 
        timeframe,
        margin_mode: marginMode,
        target_pct: parseFloat(targetPct) || null,
        stop_loss_pct: parseFloat(stopLossPct) || null
      };
      const res = await fetch('/api/strategies/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to subscribe');
      
      setIsExecuting(true);
      setStatus(data.subscription_status);
      setErrorMsg('');
      setActiveStrategyInfo({ strategy_id: selected.id, strategy_name: selected.name, coin, asset_name: coin });
    } catch (e) {
      setErrorMsg(e.message);
    }
  };

  const handleBacktest = async () => {
    setIsBacktesting(true);
    const cap = parseFloat(capital);
    try {
      const res = await fetch(`/api/strategies/${selected.id}/backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          timeframe, 
          coin, 
          capital: cap, 
          leverage: parseInt(leverage),
          target_pct: parseFloat(targetPct) || 2.0,
          stop_loss_pct: parseFloat(stopLossPct) || 1.0
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to run backtest');
      
      // Update the local state with new metrics and trades
      setStrategies(prev => prev.map(s => 
        s.id === selected.id ? { ...s, metrics: data.metrics, trades: data.trades, hasBacktest: true } : s
      ));
      setSelected(prev => ({ ...prev, metrics: data.metrics, trades: data.trades, hasBacktest: true }));
      
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
  const hasBacktest = selected.hasBacktest === true;

  return (
    <div className="strategy-terminal">
      {/* Strategy list sidebar with collapse */}
      <div style={{ display: 'flex', flexDirection: 'row', flexShrink: 0, position: 'relative' }}>
        <aside className="strat-sidebar" style={{
          width: isSidebarOpen ? 320 : 0,
          overflow: 'hidden',
          transition: 'width 0.25s ease',
          flexShrink: 0,
        }}>
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
                onClick={() => { setSelected(strat); notifyBacktestRequired(); }}
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

        {/* Sidebar toggle button */}
        <button
          onClick={toggleSidebar}
          title={isSidebarOpen ? 'Collapse strategies' : 'Expand strategies'}
          style={{
            position: 'absolute', right: -14, top: '50%', transform: 'translateY(-50%)',
            zIndex: 10, width: 28, height: 28, borderRadius: '50%',
            background: 'var(--card)', border: '1px solid var(--border)',
            color: 'var(--t2)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.4)', transition: 'all 0.2s',
            flexShrink: 0,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.color = '#fff'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--card)'; e.currentTarget.style.color = 'var(--t2)'; }}
        >
          {isSidebarOpen
            ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="15 18 9 12 15 6"/></svg>
            : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="9 18 15 12 9 6"/></svg>
          }
        </button>
      </div>

      <main className="strat-main">
        <div className="strat-header-card">
          <div className="strat-title-wrap">
            <h2 style={{ color: '#feca57', textShadow: '0 2px 10px rgba(254, 202, 87, 0.2)' }}>{selected.name}</h2>
            <p style={{
              marginTop: '6px',
              fontSize: '13px',
              color: 'rgba(255, 159, 67, 0.9)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: '100%'
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

        {/* Main content: chart area (left) + execution panel (right), side by side */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'row', gap: 12, overflow: 'hidden' }}>

          {/* Chart column */}
          <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexShrink: 0 }}>
              <h3 style={{ margin: 0, fontSize: 12, color: '#feca57', letterSpacing: 1.5, textShadow: '0 2px 10px rgba(254, 202, 87, 0.3)' }}>
                HISTORICAL PERFORMANCE
                <span style={{color: 'rgba(255, 159, 67, 0.8)', fontSize: 10, marginLeft: 8}}>(3 Month)</span>
              </h3>
              <button
                className={`beautiful-backtest-btn ${isBacktesting ? 'loading' : ''}`}
                onClick={handleBacktest}
                disabled={isBacktesting}
                style={{
                  background: 'linear-gradient(90deg, #ff9f43, #feca57)',
                  border: 'none', color: '#1a1e23', fontWeight: 900,
                  padding: '6px 18px', borderRadius: '10px',
                  boxShadow: '0 6px 20px rgba(255,159,67,0.4)',
                  cursor: isBacktesting ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: '8px',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  letterSpacing: 1, opacity: isBacktesting ? 0.7 : 1, fontSize: 11, flexShrink: 0
                }}
                onMouseOver={e => !isBacktesting && (e.currentTarget.style.transform = 'translateY(-2px)')}
                onMouseOut={e => !isBacktesting && (e.currentTarget.style.transform = 'translateY(0)')}
              >
                {isBacktesting ? (
                  <>
                    <div className="spinner-glow" style={{ borderTopColor: '#1a1e23', borderLeftColor: '#1a1e23', width: 12, height: 12 }}></div>
                    SIMULATING...
                  </>
                ) : (
                  <>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    RUN BACKTEST
                  </>
                )}
              </button>
            </div>

            <div className="strat-perf-grid" style={{ flexShrink: 0 }}>
              {!hasBacktest ? (
                <div style={{ gridColumn: '1 / -1', padding: '10px 12px', textAlign: 'center', color: 'var(--t2)', fontSize: '11px' }}>
                  Click <strong>RUN BACKTEST</strong> to simulate this strategy on historical data.
                </div>
              ) : (
                <>
                  <div className="perf-card">
                    <span className="label">WIN RATE</span>
                    <span className="value highlight" style={{ color: '#ffffff', textShadow: '0 2px 8px rgba(255,255,255,0.3)' }}>{metrics.winRate}%</span>
                  </div>
                  <div className="perf-card">
                    <span className="label">EST. PROFIT</span>
                    <span className={`value ${metrics.totalPnl >= 0 ? 'pos' : 'neg'}`}>
                      {metrics.totalPnl >= 0 ? '+' : '-'}${Math.abs(metrics.totalPnl).toFixed(2)}
                    </span>
                  </div>
                  <div className="perf-card">
                    <span className="label">MAX DRAWDOWN</span>
                    <span className="value neg">-{Math.abs(metrics.drawdown).toFixed(2)}%</span>
                  </div>
                  <div className="perf-card">
                    <span className="label">TOTAL TRADES</span>
                    <span className="value" style={{ color: '#ff9f43', textShadow: '0 2px 8px rgba(255,159,67,0.3)' }}>{metrics.trades}</span>
                  </div>
                </>
              )}
            </div>

            <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
              <ErrorBoundary>
                <BacktestChart
                  symbol={coin}
                  interval={timeframe}
                  trades={[...(selected.trades || []), ...liveTrades].sort((a,b) => a.time - b.time)}
                />
              </ErrorBoundary>
            </div>
          </div>

          {/* Execution panel — right column, fixed width, scrollable */}
          <div className="strat-execution-panel" style={{ width: 280, flexShrink: 0, overflowY: 'auto' }}>
          <div className="rp-hdr" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 10, marginBottom: 2 }}>
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
                      onClick={() => {
                        setCapital(((pct / 100) * parseFloat(walletBalance.available)).toFixed(2));
                      }}
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
                onChange={val => { setCoin(val); }}  
                options={coinOptions}
              />
            </div>

            <div className="exec-field">
              <label>TIMEFRAME</label>
              <CustomDropdown 
                value={timeframe} 
                onChange={val => { setTimeframe(val); }}  
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

            <div className="exec-field">
              <label>MARGIN MODE</label>
              <CustomDropdown 
                value={marginMode} 
                onChange={val => { setMarginMode(val); }}  
                options={[
                  { value: 'cross', label: 'Cross Margin' },
                  { value: 'isolated', label: 'Isolated Margin' }
                ]}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '12px' }}>
              <div className="exec-field" style={{ flex: 1 }}>
                <label>TAKE PROFIT</label>
                <div className="exec-input-wrap" style={{ border: '1px solid var(--border)' }}>
                  <input 
                    type="number" 
                    step="0.1"
                    value={targetPct} 
                    onChange={e => {
                      setTargetPct(e.target.value);
                    }}
                    style={{ width: '100%', paddingRight: '0' }}
                  />
                  <span style={{ color: 'var(--t3)', marginLeft: 4, width: 'auto' }}>%</span>
                </div>
              </div>

              <div className="exec-field" style={{ flex: 1 }}>
                <label>STOP LOSS</label>
                <div className="exec-input-wrap" style={{ border: '1px solid var(--border)' }}>
                  <input 
                    type="number" 
                    step="0.1"
                    value={stopLossPct} 
                    onChange={e => {
                      setStopLossPct(e.target.value);
                    }}
                    style={{ width: '100%', paddingRight: '0' }}
                  />
                  <span style={{ color: 'var(--t3)', marginLeft: 4, width: 'auto' }}>%</span>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', background: 'rgba(255,255,255,0.02)', padding: '8px 12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: '10px', fontWeight: 800, color: 'var(--t3)', letterSpacing: '1px' }}>STATUS</div>
            {isExecuting ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: status === 'WAITING' ? '#f5b301' : '#10ac84', boxShadow: `0 0 10px ${status === 'WAITING' ? '#f5b301' : '#10ac84'}` }}></div>
                <span style={{ fontSize: '11px', fontWeight: 900, color: status === 'WAITING' ? '#f5b301' : '#10ac84' }}>
                  {status === 'WAITING' ? 'ACTIVE (WAITING FOR SIGNAL)' : 'ACTIVE (TRADING)'}
                </span>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ff4757', opacity: 0.5 }}></div>
                <span style={{ fontSize: '11px', fontWeight: 900, color: '#ff4757', opacity: 0.8 }}>INACTIVE</span>
              </div>
            )}
            <label className="switch mini" style={{ marginLeft: 10 }}>
              <input 
                type="checkbox" 
                checked={isExecuting} 
                onChange={handleExecuteBtnClick}
              />
              <span className="slider round" />
            </label>
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
              borderRadius: '12px',
              padding: '12px 20px',
              width: '100%',
              fontSize: '13px',
              fontWeight: 900,
              letterSpacing: '1.5px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: isExecuting
                ? (status === 'WAITING' ? '0 4px 16px rgba(245, 179, 1, 0.35)' : '0 4px 16px rgba(255, 117, 140, 0.35)')
                : '0 4px 16px rgba(165, 94, 234, 0.35)',
              transition: 'all 0.25s ease',
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
        </div>{/* end execution panel */}
        </div>{/* end side-by-side flex row */}

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
                <button onClick={() => setShowConfirm(false)} style={{ flex: 1, padding: '12px', background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--t2)', borderRadius: '8px', cursor: 'pointer', fontWeight: 700 }}>CANCEL</button>
                <button onClick={handleConfirmExecute} style={{ flex: 1, padding: '12px', background: 'var(--accent)', border: 'none', color: '#fff', borderRadius: '8px', cursor: 'pointer', fontWeight: 700 }}>CONFIRM</button>
              </div>
            </div>
          </div>
        )}

        {showConflictModal && activeStrategyInfo && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, backdropFilter: 'blur(6px)'
          }}>
            <div style={{
              background: 'var(--card)', padding: '28px', borderRadius: '16px',
              border: '1px solid rgba(255,71,87,0.3)', maxWidth: '400px', width: '100%',
              boxShadow: '0 20px 60px rgba(0,0,0,0.5)', textAlign: 'center'
            }}>
              <div style={{ fontSize: 28, marginBottom: 12 }}>⚠️</div>
              <h3 style={{ margin: '0 0 8px', color: '#ff4757', fontSize: 16 }}>Strategy Already Active</h3>
              <p style={{ margin: '0 0 6px', color: 'var(--t1)', fontSize: 14, fontWeight: 700 }}>
                {activeStrategyInfo.strategy_name || activeStrategyInfo.strategy_id}
              </p>
              <p style={{ margin: '0 0 24px', color: 'var(--t2)', fontSize: 13, lineHeight: 1.5 }}>
                You can only run one strategy at a time. Deactivate the current strategy first before starting <strong>{selected.name}</strong>.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button onClick={() => setShowConflictModal(false)} style={{ flex: 1, padding: '12px', background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--t2)', borderRadius: '8px', cursor: 'pointer', fontWeight: 700, fontSize: 12 }}>KEEP CURRENT</button>
                <button onClick={handleDeactivateCurrent} style={{ flex: 1, padding: '12px', background: '#ff4757', border: 'none', color: '#fff', borderRadius: '8px', cursor: 'pointer', fontWeight: 700, fontSize: 12 }}>DEACTIVATE &amp; SWITCH</button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Right panel — matches multichart/dashboard right-panel design */}
      {posModal && (
        <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && setPosModal(false)} style={{ backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="modal-content" style={{ maxWidth: 1000, width: '90%', background: '#13171a', border: '1px solid var(--border)', borderRadius: 16, padding: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--t1)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ display: 'inline-block', width: 4, height: 16, background: 'var(--accent)', borderRadius: 2 }} />
                Active Positions
              </h2>
              <button onClick={() => setPosModal(false)} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', fontSize: 24, cursor: 'pointer', padding: 0 }}>×</button>
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
                    <th style={{ padding: '16px 24px', fontWeight: 600 }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.length === 0 ? (
                    <tr><td colSpan="9" style={{ textAlign: 'center', padding: '40px', color: 'var(--t3)' }}>No active positions.</td></tr>
                  ) : positions.map((p, i) => {
                    const isLong = p.side?.toUpperCase() === 'LONG';
                    const pnlUsd = p.pnl_usd !== undefined ? p.pnl_usd : (p.unrealized_pnl || 0);
                    const pnlPct = p.pnl_pct !== undefined ? p.pnl_pct : (p.unrealized_pnl_pct || 0);
                    const isPos = pnlUsd >= 0;
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', position: 'relative' }}>
                        <td style={{ padding: '16px 24px' }}>
                          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: isLong ? 'var(--green)' : 'var(--red)' }} />
                          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                            <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--t1)' }}>{p.coin}</span>
                            <span style={{ fontSize: 12, color: 'var(--t3)' }}>{p.leverage}x</span>
                          </div>
                        </td>
                        <td style={{ padding: '16px', fontSize: 13, color: isLong ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>{p.size} {p.coin}</td>
                        <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>{Number(p.size_usd || 0).toFixed(2)} USDC</td>
                        <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>{Number(p.entry_price || 0).toFixed(4)}</td>
                        <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>{Number(p.mark_price || p.entry_price || 0).toFixed(4)}</td>
                        <td style={{ padding: '16px', fontSize: 13, color: isPos ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                          {isPos ? '+' : '-'}${Math.abs(pnlUsd).toFixed(2)} ({isPos ? '+' : ''}{Number(pnlPct).toFixed(1)}%)
                          <a href={`https://app.hyperliquid.xyz/trade/${p.coin}`} target="_blank" rel="noreferrer" style={{ marginLeft: 6, color: 'var(--t3)', textDecoration: 'none' }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                          </a>
                        </td>
                        <td style={{ padding: '16px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>{Number(p.liquidation_price || 0).toFixed(4)}</td>
                        <td style={{ padding: '16px 24px', fontSize: 13, color: 'var(--t1)', fontWeight: 600 }}>
                          ${Number(p.margin_used || 0).toFixed(2)} <span style={{ color: 'var(--t3)', fontWeight: 400 }}>({(p.leverage_type || 'cross')})</span>
                        </td>
                        <td style={{ padding: '16px 24px' }}>
                          <button onClick={e => { e.stopPropagation(); handleClosePosition(p.coin); }} disabled={closingCoin === p.coin}
                            style={{ background: 'rgba(233,69,96,0.15)', color: 'var(--red)', border: 'none', padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 800, cursor: 'pointer' }}>
                            {closingCoin === p.coin ? 'CLOSING...' : 'CLOSE'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <div className={`rp-container ${isPanelOpen ? 'open' : 'closed'} ${isResizing ? 'resizing' : ''}`}>
        <div className="rp-resizer" onMouseDown={() => { setIsPanelOpen(true); setIsResizing(true); }} />
        <button className="rp-toggle-btn" onClick={togglePanel} title={isPanelOpen ? 'Collapse Panel' : 'Expand Panel'}>
          {isPanelOpen
            ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          }
        </button>
        <aside className="right-panel" style={isPanelOpen ? { width: panelWidth } : {}}>
        <section className="rp-section">
          <div className="rp-hdr">
            <h3>ACTIVE STRATEGY</h3>
          </div>

          {activeStrategyInfo ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#14b86f', flexShrink: 0, boxShadow: '0 0 8px #14b86f' }} />
                <span style={{ fontSize: 11, fontWeight: 800, color: '#14b86f', letterSpacing: 1 }}>LIVE</span>
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--t1)', marginBottom: 14 }}>
                {activeStrategyInfo.strategy_name || activeStrategyInfo.strategy_id}
              </div>

              {/* Settings grid from DB */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 12px', marginBottom: 16 }}>
                {[
                  { label: 'ASSET', value: activeStrategyInfo.asset_name && activeStrategyInfo.asset_name !== 'AUTO' ? activeStrategyInfo.asset_name : 'AUTO' },
                  { label: 'CAPITAL', value: activeStrategyInfo.capital != null ? `$${activeStrategyInfo.capital}` : '—' },
                  { label: 'LEVERAGE', value: activeStrategyInfo.leverage === 'AUTO' || activeStrategyInfo.leverage == null ? 'AUTO' : `${activeStrategyInfo.leverage}x` },
                  { label: 'MARGIN', value: activeStrategyInfo.margin_mode ? activeStrategyInfo.margin_mode.charAt(0).toUpperCase() + activeStrategyInfo.margin_mode.slice(1) : 'Cross' },
                  { label: 'TAKE PROFIT', value: activeStrategyInfo.target_pct != null ? `${activeStrategyInfo.target_pct}%` : 'AUTO' },
                  { label: 'STOP LOSS', value: activeStrategyInfo.stop_loss_pct != null ? `${activeStrategyInfo.stop_loss_pct}%` : 'AUTO' },
                ].map(({ label, value }) => (
                  <div key={label} style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 8, padding: '8px 10px' }}>
                    <div style={{ fontSize: 9, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 3 }}>{label}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--t1)' }}>{value}</div>
                  </div>
                ))}
              </div>

              <button onClick={handleDeactivateCurrent} style={{
                width: '100%', padding: '10px 0', borderRadius: 8, cursor: 'pointer',
                fontWeight: 800, fontSize: 11, letterSpacing: 1,
                background: 'rgba(255,71,87,0.12)', border: '1px solid rgba(255,71,87,0.35)', color: '#ff4757',
              }}>DEACTIVATE</button>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 28, marginBottom: 10, opacity: 0.25 }}>💤</div>
              <div style={{ fontSize: 12, color: 'var(--t2)', fontWeight: 600 }}>No strategy running</div>
              <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 4 }}>Execute a strategy below</div>
            </div>
          )}
        </section>

        <section className="rp-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div className="rp-hdr"><h3>OPEN POSITIONS ({positions.length})</h3></div>
          <div className="positions-list" style={{ flex: 1, overflowY: 'auto' }}>
            {!positions.length ? (
              <div className="pos-empty">
                <div className="empty-icon">📁</div>
                <span>NO ACTIVE POSITIONS</span>
                <p>Open trades will appear here automatically.</p>
              </div>
            ) : positions.map((p, i) => {
              const pnlUsd = p.pnl_usd !== undefined ? p.pnl_usd : (p.unrealized_pnl || 0);
              const pnlPct = p.pnl_pct !== undefined ? p.pnl_pct : (p.unrealized_pnl_pct || 0);
              const isLong = p.side?.toUpperCase() === 'LONG';
              return (
                <div key={i} className="pos-item" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, padding: 16, marginBottom: 12, display: 'flex', flexDirection: 'column', gap: 12, boxShadow: 'var(--shadow)', cursor: 'pointer' }}
                  onClick={() => setPosModal(true)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ width: 40, height: 40, borderRadius: 12, background: isLong ? 'rgba(24,184,122,0.1)' : 'rgba(233,69,96,0.1)', color: isLong ? 'var(--green)' : 'var(--red)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 900 }}>
                        {p.coin?.slice(0, 2)}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: 16, fontWeight: 900, color: 'var(--t1)', lineHeight: 1.2 }}>{p.coin}</span>
                        <span style={{ fontSize: 11, fontWeight: 800, color: isLong ? 'var(--green)' : 'var(--red)' }}>
                          {isLong ? '↑' : '↓'} {p.side?.toUpperCase()} {p.leverage}x
                        </span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                      <span style={{ fontSize: 16, fontWeight: 900, color: pnlUsd >= 0 ? 'var(--green)' : 'var(--red)' }}>
                        {pnlUsd >= 0 ? '+' : '-'}${Math.abs(pnlUsd).toFixed(2)}
                      </span>
                      <span style={{ fontSize: 11, fontWeight: 800, color: pnlUsd >= 0 ? 'var(--green)' : 'var(--red)', background: pnlUsd >= 0 ? 'rgba(24,184,122,0.1)' : 'rgba(233,69,96,0.1)', padding: '2px 8px', borderRadius: 6, marginTop: 4 }}>
                        {pnlUsd >= 0 ? '+' : ''}{(Number(pnlPct) || 0).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed var(--border)', paddingTop: 12 }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Margin</div>
                      <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--t1)' }}>${(Number(p.size_usd) || 0).toFixed(2)}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Entry</div>
                      <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--t1)' }}>${Number(p.entry_price || 0).toFixed(4)}</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleClosePosition(p.coin)}
                    disabled={closingCoin === p.coin}
                    style={{ width: '100%', background: 'rgba(233,69,96,0.15)', color: 'var(--red)', border: 'none', padding: '8px 12px', borderRadius: 8, fontSize: 11, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                  >
                    {closingCoin === p.coin ? 'CLOSING...' : 'CLOSE POSITION'}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rp-section">
          <div className="rp-hdr"><h3>RULE</h3></div>
          <p style={{ fontSize: 12, color: 'var(--t2)', lineHeight: 1.7, margin: 0 }}>
            Only <strong style={{ color: '#ff9f43' }}>1 strategy</strong> can be active at a time.<br/>
            Deactivate the current one before launching another.
          </p>
        </section>
      </aside>
      </div>
    </div>
  );
}
