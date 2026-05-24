import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [walletAddress, setWalletAddress] = useState(() => localStorage.getItem('wallet_address') || '');
  const [userProfile, setUserProfile] = useState({ email: '', subscriptions: [] });

  const fetchUserProfile = async (address) => {
    try {
      const res = await fetch(`/api/auth/me?wallet=${address}`);
      if (res.ok) {
        const data = await res.json();
        setUserProfile(data);
      }
    } catch (e) {
      console.error('Failed to fetch user profile', e);
    }
  };

  const loginWallet = async (address) => {
    try {
      await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: address })
      });
      await fetchUserProfile(address);
    } catch (e) {
      console.error('Login failed', e);
    }
  };

  const connectWallet = async (walletType = 'metamask') => {
    let provider = window.ethereum;
    if (walletType === 'phantom' && window.phantom?.ethereum) provider = window.phantom.ethereum;
    if (walletType === 'backpack' && window.backpack?.ethereum) provider = window.backpack.ethereum;
    
    // Rabby typically injects into window.ethereum, but we can check window.rabby just in case
    // For now we assume Rabby intercepts window.ethereum if it's the active wallet
    
    if (provider) {
      try {
        const accounts = await provider.request({ method: 'eth_requestAccounts' });
        const address = accounts[0];
        setWalletAddress(address);
        localStorage.setItem('wallet_address', address);
        window.dispatchEvent(new Event('wallet_changed'));
        await loginWallet(address);
        return address;
      } catch (err) {
        console.error(`Error connecting ${walletType}`, err);
        throw err;
      }
    } else {
      let name = 'MetaMask';
      if (walletType === 'phantom') name = 'Phantom';
      if (walletType === 'backpack') name = 'Backpack';
      if (walletType === 'rabby') name = 'Rabby';
      throw new Error(`${name} is not installed`);
    }
  };

  const disconnectWallet = async () => {
    // Attempt to natively disconnect providers so next login forces popup
    try {
      if (window.ethereum?.disconnect) window.ethereum.disconnect();
      if (window.phantom?.ethereum?.disconnect) window.phantom.ethereum.disconnect();
      if (window.phantom?.solana?.disconnect) window.phantom.solana.disconnect();
      if (window.rabby?.disconnect) window.rabby.disconnect();
      
      // Revoke permissions if supported (EIP-2255)
      const revokeParams = { method: "wallet_revokePermissions", params: [{ eth_accounts: {} }] };
      if (window.ethereum) await window.ethereum.request(revokeParams).catch(() => {});
      if (window.phantom?.ethereum) await window.phantom.ethereum.request(revokeParams).catch(() => {});
      if (window.rabby) await window.rabby.request(revokeParams).catch(() => {});
    } catch(e) {}

    setWalletAddress('');
    localStorage.removeItem('wallet_address');
    setUserProfile({ email: '', subscriptions: [] });
    window.dispatchEvent(new Event('wallet_changed'));
    window.location.reload(); // Instantly refresh UI state
  };

  // Watch for account changes
  useEffect(() => {
    if (typeof window.ethereum !== 'undefined') {
      window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts.length > 0) {
          const address = accounts[0];
          setWalletAddress(address);
          localStorage.setItem('wallet_address', address);
          window.dispatchEvent(new Event('wallet_changed'));
          loginWallet(address);
        } else {
          disconnectWallet();
        }
      });
    }
  }, []);

  // Watch for local storage changes from manual connection
  useEffect(() => {
    const syncWallet = () => {
      const address = localStorage.getItem('wallet_address') || '';
      setWalletAddress(address);
      if (address) loginWallet(address);
    };
    window.addEventListener('wallet_changed', syncWallet);
    return () => window.removeEventListener('wallet_changed', syncWallet);
  }, []);

  // Fetch initial profile
  useEffect(() => {
    if (walletAddress) {
      loginWallet(walletAddress);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ walletAddress, userProfile, connectWallet, disconnectWallet, fetchUserProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
