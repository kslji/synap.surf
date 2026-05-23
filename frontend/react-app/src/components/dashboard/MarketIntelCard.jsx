import { useState } from 'react';
import { relTime } from '../../utils.js';

export default function MarketIntelCard({ intel: rawIntel }) {
  const intel = rawIntel || {};
  const [activeModal, setActiveModal] = useState(null);
  
  const fg = intel.fear_greed;
  const isFear = fg && fg.classification && fg.classification.toLowerCase().includes('fear');
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
    <>
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
        <div className="intel-col-left" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {intel.market_headlines && intel.market_headlines.length > 0 ? (
            <div className="intel-body-box" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path><path d="M18 14h-8"></path><path d="M15 18h-5"></path><path d="M10 6h8v4h-8V6Z"></path></svg>
                <span style={{ fontSize: 13, fontWeight: 900, color: '#fff', letterSpacing: 1.5 }}>MARKET HEADLINES</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {intel.market_headlines.slice(0, 3).map((hl, i) => (
                  <a key={i} href={hl.link} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', display: 'block', padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: '3px solid var(--accent)', transition: 'background 0.2s' }}
                     onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.06)'}
                     onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--t1)', marginBottom: 4, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{hl.title}</div>
                    {hl.description && (
                      <div style={{ fontSize: 12, color: 'var(--t2)', marginBottom: 6, lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{hl.description}</div>
                    )}
                    <div style={{ fontSize: 11, color: 'var(--t3)', display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                      <span>{hl.source}</span>
                      {hl.published && <span>{new Date(hl.published).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>}
                    </div>
                  </a>
                ))}
                {(intel.market_headlines.length > 3 || (intel.coin_headlines && Object.keys(intel.coin_headlines).length > 0)) && (
                  <button onClick={() => setActiveModal('headlines')} style={{
                    background: 'rgba(255,255,255,0.05)', border: 'none', color: 'var(--accent)',
                    padding: '8px 12px', borderRadius: '6px', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                    marginTop: 4, transition: 'background 0.2s'
                  }} onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,0.1)'} onMouseLeave={e => e.currentTarget.style.background='rgba(255,255,255,0.05)'}>
                    View All Headlines & Coin News...
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="intel-body-box" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px', cursor: 'pointer', transition: 'all 0.2s' }}
                 onClick={() => setActiveModal('macro')}
                 onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 4px 15px rgba(0,0,0,0.2)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
                 onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)'; }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 10px var(--accent)' }}></span>
                <span style={{ fontSize: 13, fontWeight: 900, color: '#fff', letterSpacing: 1.5 }}>MACRO ASSESSMENT</span>
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--t2)', fontWeight: 500, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {renderText(intel.market_view)}
              </div>
            </div>
          )}
          
          {intel.scan_reasoning && (
            <div className="intel-body-box" style={{ background: 'rgba(24, 184, 122, 0.05)', border: '1px solid rgba(24, 184, 122, 0.2)', padding: '16px', borderRadius: '12px', position: 'relative', overflow: 'hidden', cursor: 'pointer', transition: 'all 0.2s' }}
                 onClick={() => setActiveModal('scan')}
                 onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(24, 184, 122, 0.15)'; e.currentTarget.style.borderColor = 'rgba(24, 184, 122, 0.4)'; }}
                 onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.borderColor = 'rgba(24, 184, 122, 0.2)'; }}>
              <div style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: 3, background: 'var(--green)' }}></div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 16 16 12 12 8"></polyline><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                  <span style={{ fontSize: 13, fontWeight: 900, color: 'var(--green)', letterSpacing: 1.5, textShadow: '0 0 15px rgba(24,184,122,0.4)' }}>OPPORTUNITY SCAN</span>
                </div>
                {intel.top_coins && intel.top_coins.length > 0 && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    {intel.top_coins.map(c => <span key={c} style={{ fontSize: 11, fontWeight: 800, background: 'rgba(24,184,122,0.2)', color: 'var(--green)', padding: '4px 8px', borderRadius: 6 }}>{c}</span>)}
                  </div>
                )}
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--t1)', fontWeight: 500, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
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

    {activeModal === 'macro' && (
      <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && setActiveModal(null)} style={{ backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
        <div className="modal-content" style={{ maxWidth: 800, width: '90%', background: '#13171a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: 0, overflow: 'hidden', boxShadow: '0 20px 50px rgba(0,0,0,0.5)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'linear-gradient(to right, rgba(0,210,211,0.05), transparent)' }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 900, color: '#fff', display: 'flex', alignItems: 'center', gap: 12, letterSpacing: 1.5 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 15px var(--accent)' }}></span>
              MACRO ASSESSMENT
            </h2>
            <button onClick={() => setActiveModal(null)} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', fontSize: 24, cursor: 'pointer', padding: 0, transition: 'color 0.2s' }}>×</button>
          </div>
          <div style={{ padding: '32px 24px', fontSize: 16, lineHeight: 1.8, color: 'var(--t1)', fontWeight: 500, maxHeight: '70vh', overflowY: 'auto' }}>
            {renderText(intel.market_view)}
          </div>
        </div>
      </div>
    )}

    {activeModal === 'scan' && intel.scan_reasoning && (
      <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && setActiveModal(null)} style={{ backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
        <div className="modal-content" style={{ maxWidth: 800, width: '90%', background: '#13171a', border: '1px solid rgba(24,184,122,0.2)', borderRadius: '16px', padding: 0, overflow: 'hidden', boxShadow: '0 20px 50px rgba(24,184,122,0.1)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px', borderBottom: '1px solid rgba(24,184,122,0.1)', background: 'linear-gradient(to right, rgba(24,184,122,0.05), transparent)' }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 900, color: 'var(--green)', display: 'flex', alignItems: 'center', gap: 12, letterSpacing: 1.5, textShadow: '0 0 20px rgba(24,184,122,0.4)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 16 16 12 12 8"></polyline><line x1="8" y1="12" x2="16" y2="12"></line></svg>
              OPPORTUNITY SCAN
            </h2>
            <button onClick={() => setActiveModal(null)} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', fontSize: 24, cursor: 'pointer', padding: 0, transition: 'color 0.2s' }}>×</button>
          </div>
          <div style={{ padding: '32px 24px', fontSize: 16, lineHeight: 1.8, color: 'var(--t1)', fontWeight: 500, maxHeight: '70vh', overflowY: 'auto' }}>
            <div style={{ marginBottom: 24, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {intel.top_coins && intel.top_coins.map(c => <span key={c} style={{ fontSize: 14, fontWeight: 800, background: 'rgba(24,184,122,0.2)', color: 'var(--green)', padding: '6px 12px', borderRadius: 8 }}>{c}</span>)}
            </div>
            {renderText(intel.scan_reasoning)}
          </div>
        </div>
      </div>
    )}

    {activeModal === 'headlines' && (
      <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && setActiveModal(null)} style={{ backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
        <div className="modal-content" style={{ maxWidth: 800, width: '90%', background: '#13171a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: 0, overflow: 'hidden', boxShadow: '0 20px 50px rgba(0,0,0,0.5)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'linear-gradient(to right, rgba(0,210,211,0.05), transparent)' }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 900, color: '#fff', display: 'flex', alignItems: 'center', gap: 12, letterSpacing: 1.5 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 15px var(--accent)' }}></span>
              MARKET & COIN NEWS
            </h2>
            <button onClick={() => setActiveModal(null)} style={{ background: 'transparent', border: 'none', color: 'var(--t3)', fontSize: 24, cursor: 'pointer', padding: 0, transition: 'color 0.2s' }}>×</button>
          </div>
          <div style={{ padding: '24px', maxHeight: '70vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 32 }}>
            {intel.market_headlines && intel.market_headlines.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 800, color: 'var(--accent)', marginBottom: 16, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 8, letterSpacing: 1.5 }}>GLOBAL MARKET NEWS</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {intel.market_headlines.map((hl, i) => (
                    <a key={i} href={hl.link} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', display: 'block', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', borderLeft: '4px solid var(--accent)', transition: 'background 0.2s' }}
                       onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,0.04)'} onMouseLeave={e => e.currentTarget.style.background='rgba(255,255,255,0.02)'}>
                      <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', marginBottom: 8, lineHeight: 1.4 }}>{hl.title}</div>
                      {hl.description && <div style={{ fontSize: 13, color: 'var(--t2)', marginBottom: 12, lineHeight: 1.6 }}>{hl.description}</div>}
                      <div style={{ fontSize: 12, color: 'var(--t3)', display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                        <span>{hl.source}</span>
                        {hl.published && <span>{new Date(hl.published).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>}
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}
            
            {intel.coin_headlines && Object.keys(intel.coin_headlines).length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 800, color: 'var(--green)', marginBottom: 16, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 8, letterSpacing: 1.5 }}>COIN-SPECIFIC NEWS</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                  {Object.entries(intel.coin_headlines).map(([coin, hls]) => (
                    <div key={coin}>
                      <h4 style={{ fontSize: 13, color: 'var(--t1)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ background: 'rgba(24,184,122,0.15)', color: 'var(--green)', padding: '4px 10px', borderRadius: '6px', fontWeight: 900 }}>{coin} NEWS</span>
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingLeft: 12 }}>
                        {hls.map((hl, i) => (
                          <a key={i} href={hl.link} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', display: 'block', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', borderLeft: '4px solid var(--green)', transition: 'background 0.2s' }}
                             onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,0.04)'} onMouseLeave={e => e.currentTarget.style.background='rgba(255,255,255,0.02)'}>
                            <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', marginBottom: 8, lineHeight: 1.4 }}>{hl.title}</div>
                            {hl.description && <div style={{ fontSize: 13, color: 'var(--t2)', marginBottom: 12, lineHeight: 1.6 }}>{hl.description}</div>}
                            <div style={{ fontSize: 12, color: 'var(--t3)', display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                              <span>{hl.source}</span>
                              {hl.published && <span>{new Date(hl.published).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>}
                            </div>
                          </a>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    )}
    </>
  );
}
