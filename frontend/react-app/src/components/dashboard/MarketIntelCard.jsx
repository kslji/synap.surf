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
        <div className="intel-col-left" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="intel-body-box">
            <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--t3)', letterSpacing: 1, display: 'block', marginBottom: 6 }}>MACRO ASSESSMENT</span>
            {renderText(intel.market_view)}
          </div>
          {intel.scan_reasoning && (
            <div className="intel-body-box" style={{ background: 'rgba(0, 210, 211, 0.05)', border: '1px solid rgba(0, 210, 211, 0.15)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent)', letterSpacing: 1 }}>OPPORTUNITY SCAN</span>
                {intel.top_coins && intel.top_coins.length > 0 && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    {intel.top_coins.map(c => <span key={c} style={{ fontSize: 9, fontWeight: 800, background: 'var(--accent)', color: '#fff', padding: '2px 6px', borderRadius: 4 }}>{c}</span>)}
                  </div>
                )}
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--t2)' }}>
                {renderText(intel.scan_reasoning)}
              </div>
            </div>
          )}
        </div>
        <div className="intel-col-right" style={{ borderLeft: '1px solid rgba(255,255,255,0.05)', paddingLeft: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ff9f43" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
            <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--t1)', letterSpacing: 1.5 }}>TRENDING</span>
          </div>
          <div className="trending-list" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(intel.trending_coins || []).slice(0, 5).map((c, i) => (
              <div key={i} style={{ 
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: i === 0 ? 'linear-gradient(90deg, rgba(255,159,67,0.1), transparent)' : 'rgba(255,255,255,0.02)',
                border: i === 0 ? '1px solid rgba(255,159,67,0.2)' : '1px solid rgba(255,255,255,0.05)',
                padding: '6px 12px', borderRadius: 8, transition: 'all 0.2s ease'
              }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: i === 0 ? '#ff9f43' : 'var(--t1)' }}>{c}</span>
                <div style={{ 
                  background: i === 0 ? '#ff9f43' : 'var(--card-hover)', color: i === 0 ? '#000' : 'var(--t3)',
                  fontSize: 10, fontWeight: 900, padding: '2px 6px', borderRadius: 4
                }}>
                  #{i + 1}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
