import { useState } from 'react';
import { fmt } from '../../utils.js';
import { useAuth } from '../../context/AuthContext.jsx';

export default function BalanceCard({ stats, onShowCharts, onRefresh }) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const { walletAddress, disconnectWallet } = useAuth();
  const pct = Number(stats?.pnl_pct) || 0;

  const handleRefresh = async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    try {
      await onRefresh();
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  const handleWalletClick = () => {
    if (walletAddress) {
      disconnectWallet();
    } else {
      window.dispatchEvent(new Event('trigger_wallet_connect'));
    }
  };

  return (
    <section className="bal-card compact">
      <div className="bal-top">
        <div className="bal-info">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span className="bal-label" style={{ marginBottom: 0 }}>TOTAL EQUITY</span>
            <div className="bot-status-chip" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', padding: '4px 10px', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <div className="bsc-dot running" style={{ background: 'var(--accent)', width: 6, height: 6, borderRadius: '50%' }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--t1)', letterSpacing: '0.5px' }}>Points: 0</span>
            </div>
          </div>
          <div className="bal-main-row">
            <h1 id="equityValue">${fmt(stats.equity)}</h1>
            <span className={`bal-badge${pct < 0 ? ' neg' : ''}`}>{pct >= 0 ? '+' : ''}{pct.toFixed(2)}%</span>
          </div>
          <span className="bal-eth">≈ {((stats.equity || 0) / (stats.eth_price || 3200)).toFixed(4)} ETH</span>
        </div>
        <div className="bal-actions-row" style={{ display: 'flex', gap: 8 }}>
          <button className={`qbtn tiny ${walletAddress ? 'active-wallet' : 'dark'}`} title={walletAddress ? 'Disconnect Wallet' : 'Connect Wallet'} onClick={handleWalletClick}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={walletAddress ? "#ff6b6b" : "currentColor"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
              <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
              <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
            </svg>
          </button>
          <button className="qbtn tiny" title="Refresh" onClick={handleRefresh}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: isRefreshing ? 'spin 0.6s linear infinite' : 'none' }}>
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
