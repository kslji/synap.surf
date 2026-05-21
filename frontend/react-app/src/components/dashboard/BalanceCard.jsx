import { fmt } from '../../utils.js';

export default function BalanceCard({ stats, onShowCharts, onRefresh }) {
  const pct = stats.pnl_pct || 0;
  return (
    <section className="bal-card compact">
      <div className="bal-top">
        <div className="bal-info">
          <span className="bal-label">TOTAL EQUITY</span>
          <div className="bal-main-row">
            <h1 id="equityValue">${fmt(stats.equity)}</h1>
            <span className={`bal-badge${pct < 0 ? ' neg' : ''}`}>{pct >= 0 ? '+' : ''}{pct.toFixed(2)}%</span>
          </div>
          <span className="bal-eth">≈ {((stats.equity || 0) / (stats.eth_price || 3200)).toFixed(4)} ETH</span>
        </div>
        <div className="bal-actions-row">
          <button className="qbtn tiny" title="Refresh" onClick={onRefresh}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
          </button>
          <button className="qbtn tiny dark" title="Live Chart" onClick={onShowCharts}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
}
