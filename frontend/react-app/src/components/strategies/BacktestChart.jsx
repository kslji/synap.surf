import React, { useEffect, useRef, useState } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';

export default function BacktestChart({ symbol, interval, trades }) {
  const containerRef = useRef();
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    const tfCandles = { '1m': 129600, '5m': 25920, '15m': 8640, '1h': 2160, '4h': 540, '1d': 90 };
    const lookback = Math.min(3000, Math.max(50, tfCandles[interval] || 2160));
    fetch(`/api/candles?coin=${symbol}&timeframe=${interval}&lookback=${lookback}`)
      .then(r => r.json())
      .then(data => {
        if (!isMounted) return;
        const unique = Array.from(new Map(data.map(d => [d.time, d])).values()).sort((a, b) => a.time - b.time);
        setChartData(unique);
      })
      .catch(() => {})
      .finally(() => { if (isMounted) setLoading(false); });
    return () => { isMounted = false; };
  }, [symbol, interval]);

  // Create chart once container is ready
  useEffect(() => {
    if (!containerRef.current || chartData.length === 0) return;

    const el = containerRef.current;
    const w = el.clientWidth || 600;
    const h = el.clientHeight || 360;

    const chart = createChart(el, {
      width: w,
      height: h,
      layout: {
        background: { type: 'solid', color: 'rgba(26,30,35,1)' },
        textColor: '#D9D9D9',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.06)' },
        horzLines: { color: 'rgba(255,255,255,0.06)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { width: 1, color: 'rgba(255,159,67,0.5)', style: 3, labelBackgroundColor: '#ff9f43' },
        horzLine: { width: 1, color: 'rgba(255,159,67,0.5)', style: 3, labelBackgroundColor: '#ff9f43' },
      },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: 'rgba(255,255,255,0.1)' },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
    });

    const series = chart.addCandlestickSeries({
      upColor: '#00e5ff', downColor: '#ff3366',
      borderDownColor: '#ff3366', borderUpColor: '#00e5ff',
      wickDownColor: '#ff3366', wickUpColor: '#00e5ff',
    });
    series.setData(chartData);
    chartRef.current = chart;
    seriesRef.current = series;

    // ResizeObserver — reacts to panel collapse/expand and window resize
    const ro = new ResizeObserver(() => {
      if (!el || !chartRef.current) return;
      const nw = el.clientWidth;
      const nh = el.clientHeight;
      if (nw > 0 && nh > 0) chartRef.current.resize(nw, nh);
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [chartData]);

  // Update markers when trades change without recreating the chart
  useEffect(() => {
    if (!seriesRef.current || !chartData.length) return;
    const validTimes = new Set(chartData.map(d => d.time));
    const markers = (trades || [])
      .filter(t => validTimes.has(t.time) && (!t.text || !t.text.includes('end_of_data')))
      .map(t => ({
        time: t.time,
        position: t.side === 'buy' ? 'belowBar' : 'aboveBar',
        color: t.side === 'buy' ? '#00e5ff' : '#ff3366',
        shape: t.side === 'buy' ? 'arrowUp' : 'arrowDown',
        text: t.text || (t.side === 'buy' ? 'BUY' : 'SELL'),
      }))
      .sort((a, b) => a.time - b.time);
    seriesRef.current.setMarkers(markers);
  }, [trades, chartData]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', borderRadius: 16, overflow: 'hidden', border: '1px solid var(--border)' }}>
      {loading && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 10,
          background: 'rgba(26,30,35,0.85)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12,
        }}>
          <div className="spinner-glow" style={{ width: 36, height: 36 }} />
          <span style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', letterSpacing: 2 }}>LOADING CHART</span>
        </div>
      )}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}
