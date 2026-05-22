import BalanceCard from './BalanceCard.jsx';
import MarketIntelCard from './MarketIntelCard.jsx';
import TickerRow from './TickerRow.jsx';
import TradeHistory from './TradeHistory.jsx';

export default function Dashboard({ stats, trades, perps, intel, onShowCharts, onRefresh }) {
  const safeStats = stats || {};
  const safeIntel = intel || {};
  const safeTrades = trades || [];
  const safePerps = perps || [];
  
  const now = new Date(), last = safeStats.last_updated ? new Date(safeStats.last_updated) : null;
  const isRunning = last && (now - last) / 60000 < 15;
  return (
    <div className="main-area" id="dashboardContent">
      <div className="hero-row">
        <BalanceCard stats={safeStats} onShowCharts={onShowCharts} onRefresh={onRefresh} />
        <MarketIntelCard intel={safeIntel} />
      </div>

      <TickerRow perps={safePerps} />
      <TradeHistory trades={safeTrades} />
    </div>
  );
}
