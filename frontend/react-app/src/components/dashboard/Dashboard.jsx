import BalanceCard from './BalanceCard.jsx';
import MarketIntelCard from './MarketIntelCard.jsx';
import TickerRow from './TickerRow.jsx';
import TradeHistory from './TradeHistory.jsx';

export default function Dashboard({ stats, trades, perps, intel, onShowCharts, onRefresh }) {
  const now = new Date(), last = stats.last_updated ? new Date(stats.last_updated) : null;
  const isRunning = last && (now - last) / 60000 < 15;
  return (
    <div className="main-area" id="dashboardContent">
      <header className="topbar">
        <div className="topbar-search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input type="text" placeholder="Search coins, trades…" />
        </div>
        <div className="topbar-right">
          <div className="bot-status-chip">
            <div className="bsc-dot running" style={{ background: 'var(--accent)' }} />
            <span>Points: 0</span>
          </div>
        </div>
      </header>

      <div className="hero-row">
        <BalanceCard stats={stats} onShowCharts={onShowCharts} onRefresh={onRefresh} />
        <MarketIntelCard intel={intel} />
      </div>

      <TickerRow perps={perps} />
      <TradeHistory trades={trades} />
    </div>
  );
}
