import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';

export default function WalletConnectModal({ onConnect, onClose }) {
  const { connectWallet } = useAuth();
  const [error, setError] = useState('');

  const handleConnect = async (walletType) => {
    try {
      const address = await connectWallet(walletType);
      if (address) onConnect(address);
    } catch (e) {
      setError(e.message || `Failed to connect ${walletType}`);
    }
  };

  return (
    <div className="modal-overlay active" style={styles.overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-content" style={styles.modal}>
        <div style={styles.header}>
          <h3 style={{ margin: 0, fontSize: 18, color: 'var(--t1)' }}>Select your wallet to login</h3>
          <button onClick={onClose} style={styles.closeBtn}>&times;</button>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <button onClick={() => handleConnect('metamask')} style={styles.optionBtn}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <img src="https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg" width="28" height="28" alt="MetaMask" />
              <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--t1)' }}>MetaMask</span>
            </div>
          </button>
          
          <button onClick={() => handleConnect('phantom')} style={styles.optionBtn}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <svg width="28" height="28" viewBox="0 0 128 128" fill="none">
                <rect width="128" height="128" rx="24" fill="#AB9FF2"/>
                <path d="M96 83.3C96 90.7 90 96.7 82.7 96.7C80.4 96.7 78.2 96.1 76.3 95.1C75.3 94.5 74.1 94.5 73.1 95.1C71.2 96.1 69 96.7 66.7 96.7C64.3 96.7 62.2 96.1 60.3 95.1C59.3 94.5 58 94.5 57 95.1C55.1 96.1 53 96.7 50.7 96.7C43.3 96.7 37.3 90.7 37.3 83.3V58.7C37.3 42.5 50.5 29.3 66.7 29.3C82.9 29.3 96 42.5 96 58.7V83.3Z" fill="white"/>
                <circle cx="58.7" cy="58.7" r="5.3" fill="#AB9FF2"/>
                <circle cx="74.7" cy="58.7" r="5.3" fill="#AB9FF2"/>
              </svg>
              <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--t1)' }}>Phantom</span>
            </div>
          </button>
          
          <button onClick={() => handleConnect('rabby')} style={styles.optionBtn}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <svg width="28" height="28" viewBox="0 0 128 128" fill="none">
                <rect width="128" height="128" rx="24" fill="#8697FF"/>
                <path d="M64 96C81.7 96 96 81.7 96 64C96 46.3 81.7 32 64 32C46.3 32 32 46.3 32 64C32 81.7 46.3 96 64 96Z" fill="white"/>
                <path d="M48 45C48 45 40 28 48 28C56 28 58 42 58 42" stroke="white" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M80 45C80 45 88 28 80 28C72 28 70 42 70 42" stroke="white" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="54" cy="60" r="4" fill="#8697FF"/>
                <circle cx="74" cy="60" r="4" fill="#8697FF"/>
              </svg>
              <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--t1)' }}>Rabby Wallet</span>
            </div>
          </button>

          {error && <div style={{ color: 'var(--red)', fontSize: 13, marginTop: 8, textAlign: 'center' }}>{error}</div>}
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
    backdropFilter: 'blur(8px)'
  },
  modal: {
    backgroundColor: '#13171a',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '20px',
    padding: '24px',
    width: '90%',
    maxWidth: '400px',
    boxShadow: '0 24px 64px rgba(0, 0, 0, 0.8)'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px'
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--t3)',
    fontSize: '28px',
    cursor: 'pointer',
    padding: '0 4px',
    lineHeight: 1
  },
  optionBtn: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    padding: '16px',
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '14px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  input: {
    padding: '14px',
    borderRadius: '12px',
    border: '1px solid rgba(255,255,255,0.1)',
    backgroundColor: 'rgba(0,0,0,0.2)',
    color: 'var(--t1)',
    fontSize: '15px'
  },
  submitBtn: {
    flex: 2,
    padding: '14px',
    borderRadius: '12px',
    border: 'none',
    backgroundColor: 'var(--accent)',
    color: '#fff',
    fontSize: '15px',
    fontWeight: '800',
    cursor: 'pointer',
    transition: 'opacity 0.2s'
  },
  backBtn: {
    flex: 1,
    padding: '14px',
    borderRadius: '12px',
    border: '1px solid rgba(255,255,255,0.1)',
    backgroundColor: 'transparent',
    color: 'var(--t2)',
    fontSize: '15px',
    fontWeight: '700',
    cursor: 'pointer'
  }
};
