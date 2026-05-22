import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { AuthProvider } from './context/AuthContext.jsx';

// Global ErrorBoundary — catches ANY crash in the entire app and shows the error
// instead of a blank white screen. This is the #1 fix for the blank page issue.
class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('App crashed:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          background: '#0b0e11',
          color: '#eaecef',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          padding: 40
        }}>
          <div style={{
            background: '#1e2329',
            borderRadius: 20,
            padding: '40px 48px',
            maxWidth: 600,
            width: '100%',
            textAlign: 'center',
            border: '1px solid rgba(255,159,67,0.2)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
            <h2 style={{ margin: '0 0 8px', fontSize: 20, fontWeight: 900, color: '#ff9f43' }}>
              Something went wrong
            </h2>
            <p style={{ margin: '0 0 20px', color: '#929aa5', fontSize: 13, lineHeight: 1.6 }}>
              The dashboard encountered an error. This usually fixes itself on reload.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: 'linear-gradient(90deg, #ff9f43, #feca57)',
                border: 'none',
                color: '#1a1e23',
                fontWeight: 900,
                padding: '12px 32px',
                borderRadius: 12,
                fontSize: 14,
                cursor: 'pointer',
                letterSpacing: 1,
                marginBottom: 20
              }}
            >
              RELOAD DASHBOARD
            </button>
            <details style={{ textAlign: 'left', marginTop: 16, fontSize: 11, color: '#474d57' }}>
              <summary style={{ cursor: 'pointer', color: '#929aa5', marginBottom: 8 }}>Error details</summary>
              <pre style={{
                background: '#161a1e',
                padding: 12,
                borderRadius: 8,
                overflow: 'auto',
                maxHeight: 200,
                fontSize: 10,
                color: '#f6465d',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all'
              }}>
                {this.state.error?.toString()}
                {'\n\n'}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <AuthProvider>
        <App />
      </AuthProvider>
    </AppErrorBoundary>
  </React.StrictMode>
);
