import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [walletAddress, setWalletAddress] = useState(() => localStorage.getItem('hl_wallet') || '');
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

  const connectWallet = async () => {
    if (typeof window.ethereum !== 'undefined') {
      try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const address = accounts[0];
        setWalletAddress(address);
        localStorage.setItem('hl_wallet', address);
        await loginWallet(address);
        return address;
      } catch (err) {
        console.error('Error connecting wallet', err);
        throw err;
      }
    } else {
      throw new Error('MetaMask is not installed');
    }
  };

  const disconnectWallet = () => {
    setWalletAddress('');
    setUserProfile({ email: '', subscriptions: [] });
    localStorage.removeItem('hl_wallet');
  };

  // Watch for account changes
  useEffect(() => {
    if (typeof window.ethereum !== 'undefined') {
      window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts.length > 0) {
          const address = accounts[0];
          setWalletAddress(address);
          localStorage.setItem('hl_wallet', address);
          loginWallet(address);
        } else {
          disconnectWallet();
        }
      });
    }
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
