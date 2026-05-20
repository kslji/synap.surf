import { useState, useCallback, useRef, createContext, useContext } from 'react';

const ToastCtx = createContext(null);

const ICONS = {
  success: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
      <polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  ),
  error: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  ),
  info: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>
  ),
  warning: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  ),
};

const COLORS = {
  success: { bg: 'rgba(20, 184, 111, 0.12)', border: 'rgba(20, 184, 111, 0.35)', icon: '#14b86f', bar: '#14b86f' },
  error:   { bg: 'rgba(233, 69, 96, 0.12)',  border: 'rgba(233, 69, 96, 0.35)',  icon: '#e94560', bar: '#e94560' },
  info:    { bg: 'rgba(79, 124, 200, 0.12)', border: 'rgba(79, 124, 200, 0.35)', icon: '#4f7cc8', bar: '#4f7cc8' },
  warning: { bg: 'rgba(245, 179, 1, 0.12)',  border: 'rgba(245, 179, 1, 0.35)',  icon: '#f5b301', bar: '#f5b301' },
};

function ToastItem({ toast, onRemove }) {
  const c = COLORS[toast.type] || COLORS.info;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 14,
        background: 'rgba(18, 22, 30, 0.96)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: `1px solid ${c.border}`,
        borderRadius: 16,
        padding: '16px 18px',
        minWidth: 320,
        maxWidth: 420,
        boxShadow: `0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04), inset 0 1px 0 rgba(255,255,255,0.06)`,
        position: 'relative',
        overflow: 'hidden',
        animation: 'toastIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)',
      }}
    >
      {/* Colored left bar */}
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: c.bar, borderRadius: '16px 0 0 16px' }} />

      {/* Icon */}
      <div style={{ color: c.icon, flexShrink: 0, marginTop: 1 }}>{ICONS[toast.type]}</div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {toast.title && (
          <div style={{ fontSize: 13, fontWeight: 800, color: '#fff', marginBottom: toast.message ? 4 : 0, letterSpacing: '0.1px' }}>
            {toast.title}
          </div>
        )}
        {toast.message && (
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', lineHeight: 1.55, fontWeight: 500 }}>
            {toast.message}
          </div>
        )}
        {toast.action && (
          <button
            onClick={() => { toast.action.onClick(); onRemove(toast.id); }}
            style={{ marginTop: 10, fontSize: 11, fontWeight: 800, color: c.icon, background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, letterSpacing: '0.5px', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            {toast.action.label} →
          </button>
        )}
      </div>

      {/* Close */}
      <button
        onClick={() => onRemove(toast.id)}
        style={{ color: 'rgba(255,255,255,0.3)', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 18, lineHeight: 1, padding: '0 0 0 4px', flexShrink: 0, transition: 'color 0.2s' }}
        onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.8)'}
        onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.3)'}
      >
        ×
      </button>
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const remove = useCallback((id) => {
    clearTimeout(timers.current[id]);
    setToasts(t => t.filter(x => x.id !== id));
  }, []);

  const show = useCallback(({ type = 'info', title, message, duration = 5000, action }) => {
    const id = Date.now() + Math.random();
    setToasts(t => [...t, { id, type, title, message, action }]);
    if (duration > 0) {
      timers.current[id] = setTimeout(() => remove(id), duration);
    }
    return id;
  }, [remove]);

  return (
    <ToastCtx.Provider value={show}>
      {children}
      <div style={{ position: 'fixed', bottom: 28, right: 28, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 12, pointerEvents: 'none' }}>
        <style>{`
          @keyframes toastIn {
            from { opacity: 0; transform: translateX(60px) scale(0.92); }
            to   { opacity: 1; transform: translateX(0) scale(1); }
          }
        `}</style>
        {toasts.map(t => (
          <div key={t.id} style={{ pointerEvents: 'auto' }}>
            <ToastItem toast={t} onRemove={remove} />
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  return useContext(ToastCtx);
}
