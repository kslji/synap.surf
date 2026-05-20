import React, { useState, useEffect } from 'react';
import { useToast } from './Toast.jsx';

export default function Settings() {
  const toast = useToast();
  const [showKey, setShowKey] = useState(false);

  // ── Private Key ──────────────────────────────────────────────────
  const [hlKey, setHlKey] = useState('');
  const [keyStatus, setKeyStatus] = useState(() => localStorage.getItem('hl_key_status') || null);

  const handleSaveKey = async () => {
    if (!hlKey) return;
    setKeyStatus('saving');
    try {
      const res = await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl_private_key: hlKey }),
      });
      const text = await res.text();
      if (!res.ok) {
        const d = (() => { try { return JSON.parse(text); } catch { return {}; } })();
        throw new Error(d.detail || text);
      }
      setKeyStatus('saved');
      localStorage.setItem('hl_key_status', 'saved');
      toast({ type: 'success', title: 'Private Key Saved', message: 'Your Hyperliquid key has been saved and is ready for trading.', duration: 5000 });
    } catch (err) {
      setKeyStatus('error');
      localStorage.removeItem('hl_key_status');
      toast({ type: 'error', title: 'Invalid Private Key', message: err.message, duration: 7000 });
    }
  };

  // ── Wallet Connect ───────────────────────────────────────────────
  const [connectedWallet, setConnectedWallet] = useState(() => localStorage.getItem('hl_wallet') || '');
  const [walletStatus, setWalletStatus] = useState(() => localStorage.getItem('hl_wallet') ? 'connected' : null);

  // On mount, re-check MetaMask still has the same account
  useEffect(() => {
    const saved = localStorage.getItem('hl_wallet');
    if (saved && window.ethereum) {
      window.ethereum.request({ method: 'eth_accounts' }).then(accounts => {
        if (accounts[0]?.toLowerCase() === saved.toLowerCase()) {
          setConnectedWallet(saved);
          setWalletStatus('connected');
        } else {
          // MetaMask switched accounts or disconnected — clear cache
          localStorage.removeItem('hl_wallet');
          setConnectedWallet('');
          setWalletStatus(null);
        }
      }).catch(() => {});
    }
  }, []);

  const handleConnectWallet = async () => {
    if (!window.ethereum) {
      return toast({ type: 'warning', title: 'No Wallet Found', message: 'Please install MetaMask or another EVM wallet extension to connect.', duration: 6000 });
    }
    setWalletStatus('connecting');
    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const address = accounts[0];

      // Save to localStorage immediately
      setConnectedWallet(address);
      localStorage.setItem('hl_wallet', address);
      setWalletStatus('connected');
      toast({ type: 'success', title: 'Wallet Connected', message: `${address.substring(0,6)}...${address.slice(-4)} is now your trading wallet.`, duration: 5000 });

      // Try to save to backend (non-blocking — don't fail if backend is offline)
      fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl_wallet: address }),
      }).catch(() => {/* backend offline — wallet is still saved in localStorage */});

    } catch (err) {
      setWalletStatus('error');
      toast({ type: 'error', title: 'Wallet Connection Failed', message: err.message, duration: 7000 });
    }
  };

  return (
    <div className="main-content dashboard fade-in" style={{ padding: '40px', overflowY: 'auto', flex: 1, backgroundColor: 'var(--bg)' }}>
      <header className="dash-header" style={{ marginBottom: 40, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 36, margin: 0, fontWeight: 900, letterSpacing: '-1px', color: 'var(--t1)' }}>Settings</h2>
          <p style={{ color: 'var(--t3)', fontSize: 15, marginTop: 8, fontWeight: 500 }}>Manage your profile, API keys, and subscription plan.</p>
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '32px', maxWidth: '1200px' }}>
        
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          
          {/* User Profile Section */}
          <section style={{ backgroundColor: 'var(--card)', borderRadius: 24, padding: 32, border: '1px solid var(--border)', boxShadow: 'var(--shadow)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: -50, right: -50, width: 200, height: 200, background: 'radial-gradient(circle, rgba(108, 92, 231, 0.15) 0%, rgba(255,255,255,0) 70%)', borderRadius: '50%' }}></div>
            
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 24, letterSpacing: '1.5px', textTransform: 'uppercase' }}>User Profile</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
              <div style={{ width: 88, height: 88, borderRadius: '50%', background: 'linear-gradient(135deg, #6c5ce7, #00d2d3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 36, fontWeight: 800, color: '#fff', boxShadow: '0 8px 32px rgba(108, 92, 231, 0.4)' }}>
                AS
              </div>
              <div style={{ flex: 1, zIndex: 1 }}>
                <h4 style={{ fontSize: 26, margin: '0 0 4px 0', fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--t1)' }}>Arjun Singh</h4>
                <p style={{ color: 'var(--t2)', fontSize: 14, margin: '0 0 20px 0', fontWeight: 500 }}>arjun@example.com</p>
                <div style={{ display: 'flex', gap: 12 }}>
                  <button style={{ padding: '10px 24px', height: 'auto', fontSize: 13, borderRadius: 12, fontWeight: 700, transition: 'all 0.2s', background: 'var(--t1)', color: 'var(--bg)' }}>Edit Profile</button>
                  <button style={{ padding: '10px 24px', height: 'auto', fontSize: 13, borderRadius: 12, fontWeight: 700, background: 'rgba(233, 69, 96, 0.1)', color: 'var(--red)', transition: 'all 0.2s' }}>Logout</button>
                </div>
              </div>
            </div>
          </section>

          {/* Hyperliquid API Settings */}
          <section style={{ backgroundColor: 'var(--card)', borderRadius: 24, padding: 32, border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 24, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Exchange Integration</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

              {/* ── Step 1: Private Key ── */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <label style={{ fontSize: 14, fontWeight: 800, color: 'var(--t1)' }}>Hyperliquid Private Key</label>
                  {keyStatus === 'saved' && (
                    <span style={{ fontSize: 11, color: 'var(--green)', fontWeight: 800, background: 'rgba(24,184,122,0.15)', padding: '4px 10px', borderRadius: 8 }}>SAVED ✓</span>
                  )}
                </div>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder="Enter your L1 Private Key (0x...)"
                    value={hlKey}
                    onChange={(e) => setHlKey(e.target.value)}
                    style={{
                      width: '100%', padding: '14px 80px 14px 16px', borderRadius: 14,
                      border: `1px solid ${keyStatus === 'saved' ? 'var(--green)' : 'var(--border)'}`,
                      background: 'var(--bg)', color: 'var(--t1)', fontSize: 14,
                      fontWeight: 600, fontFamily: 'monospace', outline: 'none',
                      transition: 'border 0.2s', letterSpacing: '1px',
                    }}
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'var(--border)', padding: '6px 14px', borderRadius: 10, fontSize: 12, fontWeight: 800, color: 'var(--t2)' }}
                  >
                    {showKey ? 'HIDE' : 'SHOW'}
                  </button>
                </div>
                <p style={{ fontSize: 12, color: 'var(--t3)', marginTop: 10, lineHeight: 1.6, fontWeight: 500 }}>
                  Used to sign trades. Never share this with anyone. Stored locally in your <code>.env</code>.
                </p>
                <button
                  onClick={handleSaveKey}
                  disabled={keyStatus === 'saving' || !hlKey}
                  style={{
                    marginTop: 12, width: '100%', padding: '13px', borderRadius: 12, fontSize: 13,
                    fontWeight: 800, background: keyStatus === 'saved' ? 'var(--green)' : 'var(--accent)',
                    color: '#fff', border: 'none', opacity: (!hlKey || keyStatus === 'saving') ? 0.5 : 1,
                    transition: 'all 0.2s', cursor: !hlKey ? 'not-allowed' : 'pointer',
                  }}
                >
                  {keyStatus === 'saving' ? 'Saving...' : keyStatus === 'saved' ? 'Private Key Saved ✓' : 'Save Private Key'}
                </button>
              </div>

              <div style={{ height: 1, background: 'var(--border)' }} />

              {/* ── Step 2: Wallet Address ── */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <label style={{ fontSize: 14, fontWeight: 800, color: 'var(--t1)' }}>Wallet Address (HL_WALLET)</label>
                  {walletStatus === 'connected' && (
                    <span style={{ fontSize: 11, color: 'var(--green)', fontWeight: 800, background: 'rgba(24,184,122,0.15)', padding: '4px 10px', borderRadius: 8 }}>CONNECTED ✓</span>
                  )}
                </div>

                {connectedWallet ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(24,184,122,0.08)', border: '1px solid rgba(24,184,122,0.25)', borderRadius: 14, padding: '14px 16px' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 10px var(--green)', flexShrink: 0 }} />
                    <span style={{ fontFamily: 'monospace', fontSize: 13, fontWeight: 700, color: 'var(--t1)', wordBreak: 'break-all' }}>{connectedWallet}</span>
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: 'var(--t3)', marginBottom: 0, fontWeight: 500 }}>
                    Connect your MetaMask or EVM wallet. The address will be used as your HL_WALLET for trading.
                  </p>
                )}

                <button
                  onClick={handleConnectWallet}
                  disabled={walletStatus === 'connecting'}
                  style={{
                    marginTop: 14, width: '100%', padding: '13px', borderRadius: 12, fontSize: 13,
                    fontWeight: 800,
                    background: walletStatus === 'connected' ? 'rgba(24,184,122,0.15)' : 'linear-gradient(135deg, #6c5ce7, #00d2d3)',
                    color: walletStatus === 'connected' ? 'var(--green)' : '#fff',
                    border: walletStatus === 'connected' ? '1px solid rgba(24,184,122,0.4)' : 'none',
                    transition: 'all 0.2s', cursor: walletStatus === 'connecting' ? 'wait' : 'pointer',
                  }}
                >
                  {walletStatus === 'connecting' ? 'Connecting...' : walletStatus === 'connected' ? 'Wallet Connected ✓' : '🔗 Connect EVM Wallet (MetaMask)'}
                </button>
              </div>

            </div>
          </section>


        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          
          {/* Subscription Model */}
          <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Tier 1 */}
            <div style={{ 
              background: 'linear-gradient(145deg, #1e2329, #0d1117)', 
              borderRadius: 24, padding: '2px', position: 'relative', overflow: 'hidden',
              boxShadow: '0 12px 30px rgba(0,0,0,0.1)'
            }}>
              <div style={{ 
                background: 'linear-gradient(145deg, #2b3139, #1a1e24)', 
                borderRadius: 22, padding: 24, height: '100%', display: 'flex', flexDirection: 'column'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                  <div>
                    <h3 style={{ fontSize: 12, fontWeight: 800, color: 'var(--t3)', marginBottom: 8, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Current Plan</h3>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <h2 style={{ fontSize: 32, fontWeight: 900, color: '#fff', margin: 0, letterSpacing: '-1px' }}>Algo Pro</h2>
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.1)', color: '#fff', padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 800, letterSpacing: '1px' }}>
                    ACTIVE
                  </div>
                </div>

                <div style={{ flex: 1 }}>
                  <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px 0', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {['Submit Community Hub proposals', 'Instant Telegram alerts', 'Automated AI trading (Powered by Claude AI)', '25+ fully backtested automated strategies'].map((feat, i) => (
                      <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, color: '#e6edf3', fontSize: 13, fontWeight: 600, lineHeight: 1.4 }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 2 }}>
                          <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        {feat}
                      </li>
                    ))}
                  </ul>
                </div>
                <button style={{ width: '100%', padding: '12px', borderRadius: 12, fontSize: 13, fontWeight: 800, background: 'rgba(255,255,255,0.08)', color: '#fff', border: 'none' }}>
                  Manage Plan
                </button>
              </div>
            </div>

            {/* Tier 2 */}
            <div style={{ 
              background: 'linear-gradient(145deg, #00d2d3, #6c5ce7)', 
              borderRadius: 24, padding: '3px', position: 'relative', overflow: 'hidden',
              boxShadow: '0 24px 48px rgba(108, 92, 231, 0.2)'
            }}>
              <div style={{ 
                background: 'linear-gradient(145deg, #1a1e24, #0d1117)', 
                borderRadius: 21, padding: 28, height: '100%', display: 'flex', flexDirection: 'column'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                  <div>
                    <h3 style={{ fontSize: 12, fontWeight: 800, color: '#00d2d3', marginBottom: 8, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Upgrade Available</h3>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <h2 style={{ fontSize: 32, fontWeight: 900, color: '#fff', margin: 0, letterSpacing: '-1px' }}>
                        Algo Elite <span style={{ fontSize: 18, fontWeight: 700, color: 'rgba(255,255,255,0.6)' }}>(Business)</span>
                      </h2>
                    </div>
                  </div>
                </div>

                <div style={{ flex: 1 }}>
                  <p style={{ color: '#00d2d3', fontSize: 13, fontWeight: 800, marginBottom: 16 }}>Includes everything in Pro, plus:</p>
                  <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px 0', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <li style={{ display: 'flex', alignItems: 'flex-start', gap: 12, color: '#e6edf3', fontSize: 13, fontWeight: 600, lineHeight: 1.5 }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00d2d3" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 2 }}>
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                      <div>
                        <span style={{ color: '#fff', fontWeight: 800 }}>Private Strategy Builder:</span> Seamlessly build, provision, and deploy your own unique trading strategies directly from your dashboard. Turn your vision into a private, automated strategy—no developers required!
                      </div>
                    </li>
                  </ul>
                </div>
                <button style={{ width: '100%', padding: '14px', borderRadius: 12, fontSize: 14, fontWeight: 800, background: '#00d2d3', color: '#000', border: 'none', boxShadow: '0 4px 16px rgba(0, 210, 211, 0.3)' }}>
                  Upgrade to Elite
                </button>
              </div>
            </div>
          </section>

          {/* Account Settings */}
          <section style={{ backgroundColor: 'var(--card)', borderRadius: 24, padding: 32, border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 28, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Security & Preferences</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 6, color: 'var(--t1)' }}>Two-Factor Authentication</div>
                  <div style={{ fontSize: 13, color: 'var(--t3)', fontWeight: 600 }}>Secure your account with 2FA</div>
                </div>
                <label className="switch mini">
                  <input type="checkbox" defaultChecked />
                  <span className="slider round" />
                </label>
              </div>
              
              <div style={{ height: 1, background: 'var(--border)', width: '100%' }}></div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 6, color: 'var(--t1)' }}>Email Notifications</div>
                  <div style={{ fontSize: 13, color: 'var(--t3)', fontWeight: 600 }}>Receive trade summaries daily</div>
                </div>
                <label className="switch mini">
                  <input type="checkbox" defaultChecked />
                  <span className="slider round" />
                </label>
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
