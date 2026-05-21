
export default function TickerRow({ perps }) {
  return (
    <section className="ticker-row">
      <div className="ticker-meta">
        <svg width="8" height="8" viewBox="0 0 8 8"><circle cx="4" cy="4" r="4" fill="#18b87a" /></svg>
        20 MOST VOLATILE 24H
      </div>
      <div className="ticker-chips">
        {!perps.length
          ? <span className="perp-loading">Syncing perps…</span>
          : perps.slice(0, 20).map((c, i) => (
            <div key={i} className="wchip">
              <div className="wchip-icon">
                {(c.name || '??').slice(0, 2)}
              </div>
              <span className="wchip-name">{c.name}</span>
              <span className={`wchip-pct ${c.chg >= 0 ? 'pos' : 'neg'}`}>
                {c.chg >= 0 ? '+' : ''}{c.chg.toFixed(2)}%
              </span>
            </div>
          ))
        }
      </div>
    </section>
  );
}
