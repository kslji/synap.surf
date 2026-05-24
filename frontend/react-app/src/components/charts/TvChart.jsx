import { useEffect, useRef, useState } from 'react';

let tvScriptLoaded = false;
let tvScriptLoading = false;
const onLoadCallbacks = [];

function loadTvScript(cb) {
  if (tvScriptLoaded) { cb(); return; }
  onLoadCallbacks.push(cb);
  if (tvScriptLoading) return;
  tvScriptLoading = true;
  const s = document.createElement('script');
  s.src = 'https://s3.tradingview.com/tv.js';
  s.async = true;
  s.onload = () => {
    tvScriptLoaded = true;
    onLoadCallbacks.forEach(fn => fn());
    onLoadCallbacks.length = 0;
  };
  s.onerror = () => {
    tvScriptLoading = false;
    onLoadCallbacks.length = 0;
  };
  document.head.appendChild(s);
}

export default function TvChart({ coin, idx, isCorrelationMode, chartTheme, isBase, accentColor, interval, showTools }) {
  const containerId = `tv_${coin.toLowerCase()}_${idx}`;
  const ref = useRef(null);
  const [loading, setLoading] = useState(true);
  const cleanupRef = useRef(null);

  useEffect(() => {
    setLoading(true);

    // Cancel any previous cleanup (observer + timer) on prop change
    if (cleanupRef.current) cleanupRef.current();

    loadTvScript(() => {
      if (!ref.current || !window.TradingView) { setLoading(false); return; }
      ref.current.innerHTML = '';
      const div = document.createElement('div');
      div.id = containerId;
      div.style.height = '100%';
      ref.current.appendChild(div);

      const disabledFeatures = ['header_symbol_search', 'header_screenshot'];
      if (isCorrelationMode) disabledFeatures.push('create_volume_indicator_by_default');

      const isDark = chartTheme === 'dark';
      const bgColor = isCorrelationMode
        ? (isDark ? '#000000' : '#ffffff')
        : (isDark ? '#131722' : '#ffffff');

      new window.TradingView.widget({
        autosize: true,
        symbol: `MEXC:${coin.toUpperCase()}USDT`,
        interval: interval || '15',
        timezone: 'Etc/UTC',
        theme: chartTheme,
        style: '1',
        locale: 'en',
        toolbar_bg: isCorrelationMode ? 'transparent' : (isDark ? '#131722' : '#f1f3f6'),
        enable_publishing: false,
        hide_top_toolbar: isCorrelationMode,
        hide_side_toolbar: !showTools || !isBase,
        hide_legend: true,
        save_image: false,
        container_id: containerId,
        allow_symbol_change: true,
        details: false,
        hotlist: false,
        calendar: false,
        show_popup_button: true,
        popup_width: '1000',
        popup_height: '650',
        disabled_features: disabledFeatures,
        overrides: {
          'mainSeriesProperties.priceLineColor': accentColor,
          'paneProperties.background': bgColor,
          'paneProperties.backgroundType': 'solid',
          'mainSeriesProperties.candleStyle.upColor': '#089981',
          'mainSeriesProperties.candleStyle.downColor': '#f23645',
          'mainSeriesProperties.candleStyle.borderUpColor': '#089981',
          'mainSeriesProperties.candleStyle.borderDownColor': '#f23645',
          'mainSeriesProperties.candleStyle.wickUpColor': '#089981',
          'mainSeriesProperties.candleStyle.wickDownColor': '#f23645',
        },
      });

      // TradingView lightweight widget posts a message when the chart is ready.
      // Fall back to a 12 s timeout so the loader never stays forever.
      let done = false;
      const markDone = () => { if (!done) { done = true; setLoading(false); } };

      const onMsg = (e) => {
        try {
          const data = typeof e.data === 'string' ? JSON.parse(e.data) : e.data;
          // TV posts {name:"widgetReady"} or {name:"tv-widget-ready"} or similar
          if (data && typeof data.name === 'string' && data.name.toLowerCase().includes('ready')) {
            markDone();
          }
        } catch (_) {}
      };
      window.addEventListener('message', onMsg);

      // Also watch for the iframe appearing — once it loads, chart is likely ready
      const observer = new MutationObserver(() => {
        const iframe = div.querySelector('iframe');
        if (iframe) {
          observer.disconnect();
          // iframe load fires when the inner page HTML is parsed; chart renders shortly after
          iframe.addEventListener('load', () => {
            // Give TV 1 s after iframe load to render before hiding loader
            setTimeout(markDone, 1000);
          }, { once: true });
        }
      });
      observer.observe(div, { childList: true, subtree: true });

      // Hard timeout — 15 s max no matter what
      const timeout = setTimeout(markDone, 15000);

      cleanupRef.current = () => {
        window.removeEventListener('message', onMsg);
        observer.disconnect();
        clearTimeout(timeout);
      };
    });

    return () => { if (cleanupRef.current) cleanupRef.current(); };
  }, [coin, idx, isCorrelationMode, chartTheme, isBase, accentColor, interval, showTools]);

  return (
    <div style={{ height: '100%', position: 'relative' }}>
      {loading && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: chartTheme === 'dark' ? '#131722' : '#ffffff',
          zIndex: 5, gap: 12,
        }}>
          <div style={{
            width: 28, height: 28,
            border: '3px solid rgba(255,255,255,0.1)',
            borderTop: '3px solid #14b86f',
            borderRadius: '50%',
            animation: 'tv-spin 0.8s linear infinite',
          }} />
          <span style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', letterSpacing: 1 }}>
            LOADING CHART
          </span>
          <style>{`@keyframes tv-spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}
      <div ref={ref} style={{ height: '100%' }} />
    </div>
  );
}
