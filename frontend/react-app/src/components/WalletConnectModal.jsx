import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';

export default function WalletConnectModal({ onConnect, onClose }) {
  const { connectWallet } = useAuth();
  const [error, setError] = useState('');

  const handleConnect = async () => {
    try {
      const address = await connectWallet('metamask'); // Defaults to window.ethereum
      if (address) {
        onConnect(address);
        onClose();
      }
    } catch (e) {
      setError(e.message || `Failed to connect wallet`);
    }
  };

  return (
    <div className="modal-overlay active" style={styles.overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-content" style={styles.modal}>
        <div style={styles.header}>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 20, fontWeight: 700, color: '#fff', textAlign: 'center' }}>Select a Wallet to Connect</h2>
          <p style={{ margin: 0, fontSize: 13, color: '#8a929a', textAlign: 'center' }}>Connect using your installed browser wallet</p>
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button onClick={handleConnect} style={{...styles.optionBtn, width: '100%'}}>
            <div style={styles.iconWrapper}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent)' }}>
                <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
                <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
                <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
              </svg>
            </div>
            <span style={{ fontSize: '16px', fontWeight: '700', color: '#fff' }}>Connect Web3 Wallet</span>
          </button>
        </div>
        {error && <div style={{ color: '#ff6b6b', fontSize: 13, marginTop: 16, textAlign: 'center' }}>{error}</div>}
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: '#0a0e14', // Solid dark background
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999
  },
  modal: {
    backgroundColor: 'transparent',
    padding: '24px',
    width: '100%',
    maxWidth: '380px'
  },
  header: {
    marginBottom: '32px'
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: '16px'
  },
  optionBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px 16px',
    background: '#13171a',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: '16px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  iconWrapper: {
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  btnText: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#fff'
  }
};
