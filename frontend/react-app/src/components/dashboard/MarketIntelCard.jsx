import { relTime } from '../../utils.js';

export default function MarketIntelCard({ intel }) {
  const fg = intel.fear_greed;
  const isFear = fg && fg.classification.toLowerCase().includes('fear');
  const status = intel.updated_at ? `Updated ${relTime(intel.updated_at)}` : 'Syncing...';
  const renderText = (text) => {
    if (!text) return 'Syncing...';
    const parts = text.split(/(\b[A-Z][A-Z_0-9]{2,}\b)/);
    return parts.map((part, i) => 
      /^[A-Z][A-Z_0-9]{2,}$/.test(part) 
        ? <span key={i} className="text-highlight">{part}</span> 
        : part
    );
  };

  return (
    <section className="intel-card premium">
      <div className="intel-header">
        <div className="intel-title-group">
          <h3>MARKET INTELLIGENCE</h3>
          <span className="intel-status" style={{ 
            color: 'var(--t3)',
            opacity: 0.8,
            fontWeight: 700
          }}>{status}</span>
        </div>
        <div className="fg-badge-wrap">
          <span className="fg-label" style={{ color: '#fff' }}>SENTIMENT</span>
          <div className="badge" style={fg ? {
            background: isFear ? 'rgba(233,69,96,0.15)' : 'rgba(24,184,122,0.15)',
            color: isFear ? 'var(--red)' : 'var(--green)',
            fontWeight: 900
          } : {}}>
            {fg ? `${fg.value} ${fg.classification}` : '--'}
          </div>
        </div>
      </div>
      <div className="intel-grid">
        <div className="intel-col-left">
          <div className="intel-body-box">{renderText(intel.market_view)}</div>
        </div>
        <div className="intel-col-right">
          <span className="intel-sub">TRENDING</span>
          <div className="trending-list">
            {(intel.trending_coins || []).map((c, i) => (
              <div key={i} className="trend-item">{c} <span>#{i + 1}</span></div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
