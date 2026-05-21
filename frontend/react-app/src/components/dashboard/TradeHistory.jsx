import { absTime, coinIcon, coinClass } from '../../utils.js';

export default function TradeHistory({ trades }) {
  const closed = trades.filter(t => t.event === 'TRADE_CLOSE' || t.event === 'FILL');
  return (
    <section className="table-section">
      <div className="table-hdr">
        <h2>TRADE HISTORY</h2>
        <div className="table-hdr-right">
          <span className="tbl-badge">{closed.length} trades</span>
        </div>
      </div>
      <div className="data-table">
        <div className="dt-head">
          <span>Asset</span><span>Size</span><span>Type</span><span>Exec</span><span>Entry</span><span>Exit</span><span>P&amp;L</span>
        </div>
        {!closed.length
          ? <div className="dt-empty">No closed trades yet.</div>
          : closed.map((t, i) => {
            const isPos = (t.pnl_usd || 0) >= 0;
            const icon = coinIcon(t.coin);
            const cls = coinClass(t.coin);
            const isManual = t.action === 'MANUAL_OR_EXTERNAL_TRADE';
            return (
              <div key={i} className="dt-row">
                <div className="dt-asset">
                  <div className={`dt-coin-circle ${cls}`}>{icon}</div>
                  <div>
                    <div className="dt-asset-name">{t.coin || '—'}</div>
                    <div className="dt-asset-sub">{absTime(t.timestamp)}</div>
                  </div>
                </div>
                <div className="dt-col">${(t.position_size_usd || 0).toFixed(0)}</div>
                <div className="dt-col-type">
                  <span className={`dt-side ${(t.side || 'LONG').toLowerCase()}`}>{t.side || 'LONG'}</span>
                </div>
                <div className="dt-col-type">
                  <span className={`dt-side ${isManual ? 'short' : 'long'}`}>{isManual ? 'MANUAL' : 'BOT'}</span>
                </div>
                <div className="dt-col">${(t.entry_price || 0).toFixed(2)}</div>
                <div className="dt-col">{t.exit_price != null ? '$' + t.exit_price.toFixed(2) : '—'}</div>
                <div className={`dt-col dt-pnl ${t.pnl_usd != null ? (isPos ? 'pos' : 'neg') : ''}`}>
                  {t.pnl_usd != null ? (isPos ? '+' : '-') + '$' + Math.abs(t.pnl_usd).toFixed(2) : '—'}
                </div>
              </div>
            );
          })
        }
      </div>
    </section>
  );
}
