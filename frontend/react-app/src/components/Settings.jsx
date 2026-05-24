import React, { useState, useEffect } from 'react';
import { useToast } from './Toast.jsx';
import { useAuth } from '../context/AuthContext.jsx';

export default function Settings() {
  const toast = useToast();
  const { walletAddress, connectWallet, disconnectWallet, userProfile, fetchUserProfile } = useAuth();
  
  const [showKey, setShowKey] = useState(false);

  // Local state for profile edits
  const [emailInput, setEmailInput] = useState('');
  useEffect(() => {
    if (userProfile.email) setEmailInput(userProfile.email);
  }, [userProfile.email]);

  const [emailNotifs, setEmailNotifs] = useState(false);
  const [tgToken, setTgToken] = useState(() => localStorage.getItem('tg_token') || '');
  const [tgNotifs, setTgNotifs] = useState(false);

  // ── Private Key ──────────────────────────────────────────────────
  const [hlKey, setHlKey] = useState('');
  const [keyStatus, setKeyStatus] = useState(() => localStorage.getItem('hl_key_status') || null);

  useEffect(() => {
    if (userProfile?.has_private_key) {
      setKeyStatus('saved');
    } else {
      setHlKey('');
      setKeyStatus(null);
    }
  }, [userProfile?.has_private_key]);

  const handleSaveKey = async () => {
    if (!walletAddress) {
      toast({ type: 'error', title: 'Wallet Required', message: 'Please connect your wallet first.', duration: 5000 });
      return;
    }
    setKeyStatus('saving');
    try {
      const res = await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl_private_key: hlKey, hl_wallet: walletAddress }),
      });
      const text = await res.text();
      if (!res.ok) {
        const d = (() => { try { return JSON.parse(text); } catch { return {}; } })();
        throw new Error(d.detail || text);
      }
      
      if (!hlKey) {
        setKeyStatus(null);
        localStorage.removeItem('hl_key_status');
        toast({ type: 'success', title: 'Private Key Removed', message: 'Your Hyperliquid key has been removed.', duration: 5000 });
      } else {
        setKeyStatus('saved');
        localStorage.setItem('hl_key_status', 'saved');
        toast({ type: 'success', title: 'Private Key Saved', message: 'Your Hyperliquid key has been saved and is ready for trading.', duration: 5000 });
      }
      await fetchUserProfile(walletAddress); // Refresh profile to get updated key
    } catch (err) {
      setKeyStatus('error');
      localStorage.removeItem('hl_key_status');
      toast({ type: 'error', title: 'Invalid Private Key', message: err.message, duration: 7000 });
    }
  };

  // ── Wallet Connect ───────────────────────────────────────────────
  const [walletStatus, setWalletStatus] = useState(() => walletAddress ? 'connected' : null);

  useEffect(() => {
    setWalletStatus(walletAddress ? 'connected' : null);
  }, [walletAddress]);

  const handleConnectWallet = async () => {
    try {
      setWalletStatus('connecting');
      const address = await connectWallet();
      setWalletStatus('connected');
      toast({ type: 'success', title: 'Wallet Connected', message: `${address.substring(0,6)}...${address.slice(-4)} is now connected.`, duration: 5000 });
    } catch (err) {
      setWalletStatus('error');
      toast({ type: 'error', title: 'Wallet Connection Failed', message: err.message, duration: 7000 });
    }
  };

  const handleSaveProfile = async () => {
    if (!walletAddress) return toast({ type: 'error', title: 'Not connected', message: 'Connect wallet first' });
    try {
      await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl_wallet: walletAddress, email: emailInput }),
      });
      await fetchUserProfile(walletAddress);
      toast({ type: 'success', title: 'Profile Updated', message: 'Your email has been saved.' });
    } catch (err) {
      toast({ type: 'error', title: 'Error', message: 'Failed to update profile' });
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
                {walletAddress ? walletAddress.substring(2, 4).toUpperCase() : '?'}
              </div>
              <div style={{ flex: 1, zIndex: 1 }}>
                <h4 style={{ fontSize: 26, margin: '0 0 4px 0', fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--t1)' }}>{walletAddress ? `${walletAddress.substring(0,6)}...${walletAddress.slice(-4)}` : 'Not Connected'}</h4>
                <input 
                  type="email" 
                  placeholder="Enter your email address"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', padding: '6px 12px', borderRadius: 8, color: 'var(--t1)', fontSize: 14, margin: '0 0 20px 0', fontWeight: 500, width: '100%', maxWidth: '250px' }} 
                  disabled={!walletAddress}
                />
                <div style={{ display: 'flex', gap: 12 }}>
                  <button onClick={handleSaveProfile} disabled={!walletAddress} style={{ padding: '10px 24px', height: 'auto', fontSize: 13, borderRadius: 12, fontWeight: 700, transition: 'all 0.2s', background: 'var(--t1)', color: 'var(--bg)', opacity: !walletAddress ? 0.5 : 1 }}>Save Profile</button>
                  <button onClick={disconnectWallet} disabled={!walletAddress} style={{ padding: '10px 24px', height: 'auto', fontSize: 13, borderRadius: 12, fontWeight: 700, background: 'rgba(233, 69, 96, 0.1)', color: 'var(--red)', transition: 'all 0.2s', opacity: !walletAddress ? 0.5 : 1 }}>Disconnect</button>
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

                {walletAddress ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(24,184,122,0.08)', border: '1px solid rgba(24,184,122,0.25)', borderRadius: 14, padding: '14px 16px' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 10px var(--green)', flexShrink: 0 }} />
                    <span style={{ fontFamily: 'monospace', fontSize: 13, fontWeight: 700, color: 'var(--t1)', wordBreak: 'break-all' }}>{walletAddress}</span>
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: 'var(--t3)', marginBottom: 0, fontWeight: 500 }}>
                    <button onClick={() => window.dispatchEvent(new Event('trigger_wallet_connect'))} 
                    disabled={walletStatus === 'connecting'}
                    style={{ 
                    padding: '16px 24px', fontSize: 15, fontWeight: 800, borderRadius: 16, border: 'none',
                    background: walletStatus === 'connected' ? 'rgba(24,184,122,0.15)' : 'linear-gradient(135deg, #6c5ce7, #00d2d3)',
                    color: walletStatus === 'connected' ? 'var(--green)' : '#fff',
                    border: walletStatus === 'connected' ? '1px solid rgba(24,184,122,0.4)' : 'none',
                    transition: 'all 0.2s', cursor: walletStatus === 'connecting' ? 'wait' : 'pointer',
                    boxShadow: walletStatus === 'connected' ? 'none' : '0 8px 24px rgba(108,92,231,0.4)'
                  }}>
                    {walletStatus === 'connecting' ? 'Connecting...' : walletStatus === 'connected' ? 'Wallet Connected ✓' : '🔗 Connect Wallet'}
                  </button>
                  </p>
                )}
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
                    <h3 style={{ fontSize: 12, fontWeight: 800, color: 'var(--t3)', marginBottom: 8, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Subscription</h3>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <h2 style={{ fontSize: 32, fontWeight: 900, color: '#fff', margin: 0, letterSpacing: '-1px' }}>Synap Pro</h2>
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.1)', color: '#fff', padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 800, letterSpacing: '1px' }}>
                    {userProfile.subscriptions?.length > 0 ? 'ACTIVE' : 'INACTIVE'}
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
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 'auto' }}>
                  <button style={{ padding: '12px 8px', borderRadius: 12, background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }} onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.background = 'rgba(0,210,211,0.1)'; }} onMouseOut={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}>
                    <div style={{ fontSize: 18, fontWeight: 900, marginBottom: 4 }}>$2</div>
                    <div style={{ fontSize: 11, color: 'var(--t3)', fontWeight: 600 }}>2 Days</div>
                  </button>
                  <button style={{ padding: '12px 8px', borderRadius: 12, background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 15px rgba(0,210,211,0.3)' }} onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,210,211,0.4)'; }} onMouseOut={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 15px rgba(0,210,211,0.3)'; }}>
                    <div style={{ fontSize: 18, fontWeight: 900, marginBottom: 4 }}>$5</div>
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>7 Days</div>
                  </button>
                  <button style={{ padding: '12px 8px', borderRadius: 12, background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }} onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.background = 'rgba(0,210,211,0.1)'; }} onMouseOut={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}>
                    <div style={{ fontSize: 18, fontWeight: 900, marginBottom: 4 }}>$15</div>
                    <div style={{ fontSize: 11, color: 'var(--t3)', fontWeight: 600 }}>1 Month</div>
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* Account Settings */}
          <section style={{ backgroundColor: 'var(--card)', borderRadius: 24, padding: 32, border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 28, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Security & Preferences</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 6, color: 'var(--t1)' }}>Email Notifications</div>
                  <div style={{ fontSize: 13, color: 'var(--t3)', fontWeight: 600 }}>Receive trade summaries daily</div>
                </div>
                <label className="switch mini">
                  <input type="checkbox" checked={emailNotifs} onChange={(e) => {
                    if (!email || !email.includes('@')) {
                      toast({ type: 'error', title: 'Invalid Email', message: 'Please add a valid email address in your profile first.', duration: 3000 });
                      return;
                    }
                    setEmailNotifs(e.target.checked);
                  }} />
                  <span className="slider round" />
                </label>
              </div>

              <div style={{ height: 1, background: 'var(--border)', width: '100%' }}></div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 6, color: 'var(--t1)' }}>Telegram Notifications</div>
                    <div style={{ fontSize: 13, color: 'var(--t3)', fontWeight: 600 }}>Receive alerts in your Telegram group</div>
                  </div>
                  <label className="switch mini">
                    <input type="checkbox" checked={tgNotifs} onChange={(e) => {
                      if (!tgToken) {
                        toast({ type: 'error', title: 'Missing Bot Token', message: 'Please add a valid Telegram Bot Token below first.', duration: 3000 });
                        return;
                      }
                      setTgNotifs(e.target.checked);
                    }} />
                    <span className="slider round" />
                  </label>
                </div>
                <input 
                  type="text" 
                  placeholder="Enter Telegram Bot Token (e.g. 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)" 
                  value={tgToken}
                  onChange={(e) => {
                    setTgToken(e.target.value);
                    localStorage.setItem('tg_token', e.target.value);
                    if (!e.target.value) setTgNotifs(false);
                  }}
                  style={{ width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid var(--border)', background: 'rgba(255,255,255,0.02)', color: 'var(--t1)', fontSize: 13 }}
                />
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
