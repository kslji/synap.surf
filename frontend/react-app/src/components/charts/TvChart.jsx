import { useEffect, useRef } from 'react';

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
  s.onload = () => { tvScriptLoaded = true; onLoadCallbacks.forEach(fn => fn()); onLoadCallbacks.length = 0; };
  document.head.appendChild(s);
}

export default function TvChart({ coin, idx, isCorrelationMode, chartTheme, isBase, accentColor, interval, showTools }) {
  const containerId = `tv_${coin.toLowerCase()}_${idx}`;
  const ref = useRef(null);

  useEffect(() => {
    loadTvScript(() => {
      if (!ref.current || !window.TradingView) return;
      ref.current.innerHTML = '';
      const div = document.createElement('div');
      div.id = containerId;
      div.style.height = '100%';
      ref.current.appendChild(div);

      const disabledFeatures = ["header_symbol_search", "header_screenshot"];
      if (isCorrelationMode) {
        disabledFeatures.push("create_volume_indicator_by_default");
      }

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
          "mainSeriesProperties.priceLineColor": accentColor,
          "paneProperties.background": bgColor,
          "paneProperties.backgroundType": "solid",
          "mainSeriesProperties.candleStyle.upColor": "#089981",
          "mainSeriesProperties.candleStyle.downColor": "#f23645",
          "mainSeriesProperties.candleStyle.borderUpColor": "#089981",
          "mainSeriesProperties.candleStyle.borderDownColor": "#f23645",
          "mainSeriesProperties.candleStyle.wickUpColor": "#089981",
          "mainSeriesProperties.candleStyle.wickDownColor": "#f23645",
        }
      });
    });
  }, [coin, idx, isCorrelationMode, chartTheme, isBase, accentColor, interval, showTools]);

  return <div ref={ref} style={{ height: '100%' }} />;
}
