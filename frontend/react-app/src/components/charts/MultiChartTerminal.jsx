import { useState, useEffect } from 'react';
import TvChart from './TvChart.jsx';

const DOT_COLORS = ['#14b86f', '#0a84ff', '#a855f7', '#f5b301'];

export default function MultiChartTerminal({ coins, onBack, theme }) {
  const [isCorrelation, setIsCorrelation] = useState(() => localStorage.getItem('correlation_mode') === 'true');
  const [activeIdx, setActiveIdx] = useState(() => JSON.parse(localStorage.getItem('active_corr_indices') || '[0,1,2,3]'));
  const [showTools, setShowTools] = useState(false);

  const [selectedCoins, setSelectedCoins] = useState(() => {
    const saved = localStorage.getItem('terminal_selected_coins_v4');
    if (saved) return JSON.parse(saved);
    return coins.length >= 4 ? coins.slice(0, 4) : ['BTC', 'ETH', 'SOL', 'SEI', 'HYPE', 'SUI'];
  });

  const [intervals, setIntervals] = useState(() => {
    const saved = localStorage.getItem('terminal_intervals_v1');
    if (saved) return JSON.parse(saved);
    return ['15', '15', '15', '15'];
  });

  const [availableOptions, setAvailableOptions] = useState(() => {
    return Array.from(new Set([...coins, 'BTC', 'ETH', 'SOL', 'SEI', 'HYPE', 'SUI']));
  });

  useEffect(() => {
    localStorage.setItem('terminal_intervals_v1', JSON.stringify(intervals));
  }, [intervals]);

  useEffect(() => {
    async function fetchTopVolatile() {
      try {
        // Fetch both watchlist and market data in parallel
        const [wRes, pRes] = await Promise.all([
          fetch('/api/watchlist'),
          fetch('/api/hl_top_perps')
        ]);

        const wJson = await wRes.json();
        const pJson = await pRes.json();

        const watchlistSymbols = wJson.watchlist || [];
        const assets = pJson.assets || [];

        // Calculate volatility for all assets
        const calculated = assets.map(a => {
          const mark = parseFloat(a.markPx || 0);
          const prev = parseFloat(a.prevDayPx || 0);
          const vol = prev > 0 ? Math.abs(mark - prev) / prev : 0;
          return { name: a.name, vol };
        });

        // Filter for assets in watchlist
        const watchlistMovers = calculated
          .filter(a => watchlistSymbols.includes(a.name))
          .sort((a, b) => b.vol - a.vol)
          .map(a => a.name);

        // Filter for global high volatile assets (not in watchlist)
        const globalMovers = calculated
          .filter(a => !watchlistSymbols.includes(a.name))
          .sort((a, b) => b.vol - a.vol)
          .slice(0, 15)
          .map(a => a.name);

        const defaults = [
          'BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'AVAX', 'DOT', 'POL', 'NEAR', 'ATOM',
          'FTM', 'ALGO', 'APT', 'SUI', 'OP', 'ARB', 'TON', 'TIA', 'SEI', 'INJ', 'HYPE', 'ZEC'
        ];

        // Final list: Watchlist Movers -> Defaults -> Other Global Movers
        const merged = Array.from(new Set([...watchlistMovers, ...defaults, ...globalMovers, ...coins])).sort();
        setAvailableOptions(merged);
      } catch (err) {
        console.error("Failed to fetch volatile assets:", err);
      }
    }
    fetchTopVolatile();
  }, [coins]);

  // Adaptive chart count: 3 for Correlation, 4 for Grid
  const displayCoins = selectedCoins.slice(0, isCorrelation ? 3 : 4);

  useEffect(() => {
    localStorage.setItem('terminal_selected_coins_v4', JSON.stringify(selectedCoins));
  }, [selectedCoins]);

  const toggleCorr = (checked) => {
    setIsCorrelation(checked);
    localStorage.setItem('correlation_mode', checked);
  };


  const toggleIdx = (idx, checked) => {
    const next = checked ? [...activeIdx, idx] : activeIdx.filter(i => i !== idx);
    setActiveIdx(next);
    localStorage.setItem('active_corr_indices', JSON.stringify(next));
  };

  const handleCoinChange = (idx, newCoin) => {
    const next = [...selectedCoins];
    next[idx] = newCoin;
    setSelectedCoins(next);
  };

  const handleIntervalChange = (idx, newInterval) => {
    const next = [...intervals];
    next[idx] = newInterval;
    setIntervals(next);
  };

  // Available options: handled by state

  return (
    <div className="main-area" id="chartsContent" style={{ gap: 0, padding: 0 }}>
      <div className="table-hdr" style={{ marginBottom: 0, padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="ttab active" onClick={onBack} style={{ padding: '6px 16px' }}>← Dashboard</button>
          <h2 style={{ margin: 0, fontSize: 13, letterSpacing: 1 }}>
            {isCorrelation ? 'CORRELATION TERMINAL' : 'MULTICHART TERMINAL'}
          </h2>
        </div>
        <div className="table-hdr-right" style={{ gap: 15 }}>
          {isCorrelation && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 15, borderRight: '1px solid var(--border)', paddingRight: 15 }}>
              <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--t3)' }}>ANALYSIS TOOLS</span>
              <label className="switch">
                <input type="checkbox" checked={showTools} onChange={e => setShowTools(e.target.checked)} />
                <span className="slider round" />
              </label>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
            <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--t3)' }}>CORRELATION</span>
            <label className="switch">
              <input type="checkbox" checked={isCorrelation} onChange={e => toggleCorr(e.target.checked)} />
              <span className="slider round" />
            </label>
          </div>
        </div>
      </div>

      <div className="corr-legend" style={{ padding: '8px 20px', borderBottom: '1px solid var(--border)', background: 'var(--white)', overflowX: 'auto' }}>
        <div className="cl-items" style={{ display: 'flex', gap: 18, minWidth: 'max-content' }}>
          <span className="cl-title" style={{ marginRight: 5 }}>SELECT ASSETS:</span>
          {displayCoins.map((c, i) => (
            <div key={i} className="cl-item" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {isCorrelation && (
                <input type="checkbox" checked={activeIdx.includes(i)} onChange={e => toggleIdx(i, e.target.checked)} />
              )}
              <div className="cl-dot" style={{ background: DOT_COLORS[i], width: 8, height: 8, borderRadius: '50%' }} />
              <select
                value={c}
                onChange={e => handleCoinChange(i, e.target.value)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: 800,
                  padding: '1px 4px',
                  color: 'var(--t1)',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              >
                {availableOptions.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>

              {isCorrelation && (
                <select
                  value={intervals[i]}
                  onChange={e => handleIntervalChange(i, e.target.value)}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    fontSize: 10,
                    fontWeight: 600,
                    padding: '1px 2px',
                    color: 'var(--t2)',
                    outline: 'none',
                    cursor: 'pointer',
                    marginLeft: 2
                  }}
                >
                  <option value="1">1m</option>
                  <option value="5">5m</option>
                  <option value="15">15m</option>
                  <option value="60">1h</option>
                  <option value="240">4h</option>
                  <option value="D">1D</option>
                  <option value="W">1W</option>
                </select>
              )}
            </div>
          ))}
        </div>
      </div>

      <div
        className={`charts-grid${isCorrelation ? ' correlation-mode' : ''}`}
        id="chartsGrid"
        data-theme={theme}
      >
        {isCorrelation && activeIdx.length === 0 ? (
          <div style={{
            gridColumn: '1 / -1',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--t3)',
            background: 'var(--bg-main)',
            gap: 15
          }}>
            <div style={{ fontSize: 32, opacity: 0.5 }}>📊</div>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 0.5 }}>SELECT ASSETS TO START CORRELATION</div>
            <div style={{ fontSize: 11, opacity: 0.7 }}>Tick the checkboxes to layer charts on top of each other</div>
          </div>
        ) : (
          displayCoins.map((coin, idx) => {
            const isActive = activeIdx.includes(idx);
            const hidden = isCorrelation && !isActive;
            const isInteractive = isCorrelation && isActive && idx === Math.min(...activeIdx);

            let dynamicOpacity = 1;
            let dynamicZIndex = 1;

            if (isCorrelation && isActive) {
              const firstActiveIdx = Math.min(...activeIdx);
              if (idx === firstActiveIdx) {
                dynamicOpacity = 1;
                dynamicZIndex = 10; // Interactive layer on top
              } else {
                dynamicOpacity = 0.8; // Overlays slightly transparent but still visible
                dynamicZIndex = 1; // Others below
              }
            }

            return (
              <div
                key={`${coin}-${idx}-${isCorrelation ? 'corr' : 'grid'}`}
                className={`chart-container tint-${idx}${hidden ? ' hidden' : ''}${isInteractive ? ' interactive-layer' : ''}`}
                style={isCorrelation && isActive ? {
                  opacity: dynamicOpacity,
                  zIndex: dynamicZIndex
                } : {}}
              >
                {(!isCorrelation || isActive) && (
                  <TvChart
                    coin={coin}
                    idx={idx}
                    isCorrelationMode={isCorrelation}
                    chartTheme={theme}
                    isBase={isInteractive}
                    accentColor={DOT_COLORS[idx]}
                    interval={intervals[idx]}
                    showTools={showTools}
                  />
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
