import { absTime, coinIcon, coinClass } from '../../utils.js';

export default function TradeHistory({ trades }) {
  // Show all meaningful trade events: OPEN, CLOSE, and bot EXECUTED
  const visible = (Array.isArray(trades) ? trades : []).filter(t => {
    const ev = t.event || '';
    const st = t.status || '';
    return (
      ev === 'TRADE_OPEN' ||
      ev === 'TRADE_CLOSE' ||
      ev === 'FILL' ||
      st === 'EXECUTED' ||
      st === 'FILLED'
    );
  });

  return (
    <section className="table-section">
      <div className="table-hdr">
        <h2>TRADE HISTORY</h2>
        <div className="table-hdr-right">
          <span className="tbl-badge">{visible.length} trades</span>
        </div>
      </div>
      <div className="data-table">
        <div className="dt-head">
          <span>Asset</span><span>Size</span><span>Type</span><span>Exec</span><span>Entry</span><span>Exit</span><span>P&amp;L</span>
        </div>
        {!visible.length
          ? <div className="dt-empty">No trades yet.</div>
          : visible.map((t, i) => {
            const isClose = t.event === 'TRADE_CLOSE' || t.event === 'FILL';
            const isPos = (t.pnl_usd || 0) >= 0;
            const icon = coinIcon(t.coin);
            const cls = coinClass(t.coin);
            const isManual = !t.action || t.action === 'MANUAL_OR_EXTERNAL_TRADE';
            const execLabel = t.action === 'BOT' ? 'BOT' : (isManual ? 'MANUAL' : 'BOT');
            const sizeUsd = t.position_size_usd || t.size_usd || 0;
            return (
              <div key={t._id || i} className="dt-row">
                <div className="dt-asset">
                  <div className={`dt-coin-circle ${cls}`}>{icon}</div>
                  <div>
                    <div className="dt-asset-name">{t.coin || '—'}</div>
                    <div className="dt-asset-sub">{absTime(t.timestamp)}</div>
                  </div>
                </div>
                <div className="dt-col">${Number(sizeUsd).toFixed(0)}</div>
                <div className="dt-col-type">
                  <span className={`dt-side ${(t.side || 'LONG').toLowerCase()}`}>{t.side || 'LONG'}</span>
                </div>
                <div className="dt-col-type">
                  <span className={`dt-side ${execLabel === 'BOT' ? 'long' : 'short'}`}>{execLabel}</span>
                </div>
                <div className="dt-col">${Number(t.entry_price || 0).toFixed(2)}</div>
                <div className="dt-col">
                  {isClose && t.exit_price != null ? '$' + Number(t.exit_price).toFixed(2) : <span style={{ color: 'var(--t3)' }}>Open</span>}
                </div>
                <div className={`dt-col dt-pnl ${isClose && t.pnl_usd != null ? (isPos ? 'pos' : 'neg') : ''}`}>
                  {isClose && t.pnl_usd != null
                    ? (isPos ? '+' : '-') + '$' + Math.abs(t.pnl_usd).toFixed(2)
                    : <span style={{ color: 'var(--t3)' }}>—</span>}
                </div>
              </div>
            );
          })
        }
      </div>
    </section>
  );
}
