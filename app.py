# --- START OF FILE app.py ---

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import time
from alpha_vantage.timeseries import TimeSeries
from scipy.signal import find_peaks

warnings.filterwarnings('ignore')

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="RSI & Divergence Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS personnalisé (Assurez-vous que votre CSS est bien ici) ---
st.markdown("""
<style>
    /* ... (VOTRE CSS COMPLET ICI, il est essentiel) ... */
    /* Styles généraux */
    .main > div { padding-top: 2rem; }
    .screener-header { font-size: 28px; font-weight: bold; color: #FAFAFA; margin-bottom: 15px; text-align: center; }
    .update-info { background-color: #262730; padding: 8px 15px; border-radius: 5px; margin-bottom: 20px; font-size: 14px; color: #A9A9A9; border: 1px solid #333A49; text-align: center; }
    .legend-container { display: flex; justify-content: center; flex-wrap: wrap; gap: 25px; margin: 25px 0; padding: 15px; border-radius: 5px; background-color: #1A1C22; }
    .legend-item { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #D3D3D3; }
    .legend-dot { width: 12px; height: 12px; border-radius: 50%; }
    .oversold-dot { background-color: #FF4B4B; }
    .overbought-dot { background-color: #3D9970; }
    h3 { color: #EAEAEA; text-align: center; margin-top: 30px; margin-bottom: 15px; }
    .rsi-table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1); }
    .rsi-table th { background-color: #333A49; color: #EAEAEA !important; padding: 14px 10px; text-align: center; font-weight: bold; font-size: 15px; border: 1px solid #262730; }
    .rsi-table td { padding: 12px 10px; text-align: center; border: 1px solid #262730; font-size: 14px; }
    .devises-cell { font-weight: bold !important; color: #E0E0E0 !important; font-size: 15px !important; text-align: left !important; padding-left: 15px !important; }
    .oversold-cell { background-color: rgba(255, 75, 75, 0.7) !important; color: white !important; font-weight: bold; }
    .overbought-cell { background-color: rgba(61, 153, 112, 0.7) !important; color: white !important; font-weight: bold; }
    .neutral-cell { color: #C0C0C0 !important; background-color: #161A1D; }
    .divergence-icon { font-size: 16px; vertical-align: middle; margin-left: 5px; }
</style>
""", unsafe_allow_html=True)


# --- Accès à l'API Key via st.secrets (méthode sécurisée) ---
try:
    api_key = st.secrets["alpha_vantage_api_key"]
except KeyError:
    st.error("🔑 Clé API Alpha Vantage non trouvée !")
    st.info("Veuillez ajouter votre clé API dans les 'Secrets' des paramètres de l'application sur Streamlit Cloud.")
    st.code('alpha_vantage_api_key = "VOTRE_CLE_API"')
    st.stop()


# --- Fonctions de calcul et de récupération de données ---
def calculate_rsi(prices, period=10):
    try:
        if prices is None or len(prices) < period + 1: return np.nan, None
        ohlc4 = (prices['Open'] + prices['High'] + prices['Low'] + prices['Close']) / 4
        delta = ohlc4.diff()
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        if len(gains.dropna()) < period or len(losses.dropna()) < period: return np.nan, None
        avg_gains = gains.ewm(com=period - 1, adjust=False, min_periods=period).mean()
        avg_losses = losses.ewm(com=period - 1, adjust=False, min_periods=period).mean()
        rs = avg_gains / avg_losses
        rs[avg_losses == 0] = np.inf
        rsi_series = 100.0 - (100.0 / (1.0 + rs))
        if rsi_series.empty or pd.isna(rsi_series.iloc[-1]): return np.nan, None
        return rsi_series.iloc[-1], rsi_series
    except Exception:
        return np.nan, None

def detect_divergence(price_data, rsi_series, lookback=30, peak_distance=5):
    if rsi_series is None or len(price_data) < lookback: return "Aucune"
    recent_price = price_data.iloc[-lookback:]
    recent_rsi = rsi_series.iloc[-lookback:]
    price_peaks_idx, _ = find_peaks(recent_price['High'], distance=peak_distance)
    if len(price_peaks_idx) >= 2:
        if recent_price['High'].iloc[price_peaks_idx[-1]] > recent_price['High'].iloc[price_peaks_idx[-2]]:
            if recent_rsi.iloc[price_peaks_idx[-1]] < recent_rsi.iloc[price_peaks_idx[-2]]:
                return "Baissière"
    price_troughs_idx, _ = find_peaks(-recent_price['Low'], distance=peak_distance)
    if len(price_troughs_idx) >= 2:
        if recent_price['Low'].iloc[price_troughs_idx[-1]] < recent_price['Low'].iloc[price_troughs_idx[-2]]:
            if recent_rsi.iloc[price_troughs_idx[-1]] > recent_rsi.iloc[price_troughs_idx[-2]]:
                return "Haussière"
    return "Aucune"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_forex_data_av(symbol, timeframe_key, av_api_key):
    try:
        ts = TimeSeries(key=av_api_key, output_format='pandas')
        from_symbol, to_symbol = symbol.split('/')
        data = None
        if timeframe_key == 'H4':
             _data, _ = ts.get_intraday(from_symbol=from_symbol, to_symbol=to_symbol, interval='60min', outputsize='full')
             if _data is not None and not _data.empty:
                _data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close'}, inplace=True)
                _data.index = pd.to_datetime(_data.index)
                _data = _data.astype(float)
                data = _data.resample('4H').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
        elif timeframe_key == 'H1':
            data, _ = ts.get_intraday(from_symbol=from_symbol, to_symbol=to_symbol, interval='60min', outputsize='compact')
        elif timeframe_key == 'D1':
            data, _ = ts.get_daily(symbol=f"{from_symbol}{to_symbol}", outputsize='full')
        elif timeframe_key == 'W1':
            data, _ = ts.get_weekly(symbol=f"{from_symbol}{to_symbol}")
        
        time.sleep(13)

        if data is None or data.empty: return None
        data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close'}, inplace=True, errors='ignore')
        data.index = pd.to_datetime(data.index)
        data = data.astype(float).sort_index(ascending=True)
        return data[['Open', 'High', 'Low', 'Close']]
    except Exception:
        time.sleep(13)
        return None

def format_rsi(value): return "N/A" if pd.isna(value) else f"{value:.2f}"
def get_rsi_class(value):
    if pd.isna(value): return "neutral-cell"
    elif value <= 20: return "oversold-cell"
    elif value >= 80: return "overbought-cell"
    return "neutral-cell"

# --- Constantes ---
FOREX_PAIRS = [
    'EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD',
    'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'NZD/JPY', 'CAD/JPY', 'CHF/JPY',
    'EUR/GBP', 'EUR/AUD', 'EUR/CAD', 'EUR/NZD', 'EUR/CHF'
]
TIMEFRAMES_DISPLAY = ['H1', 'H4', 'Daily', 'Weekly']
TIMEFRAMES_FETCH_KEYS = ['H1', 'H4', 'D1', 'W1']

# --- Fonction principale d'analyse ---
def run_analysis_process(av_api_key):
    results_list = []
    total_calls = len(FOREX_PAIRS) * len(TIMEFRAMES_FETCH_KEYS)
    progress_widget = st.progress(0)
    status_widget = st.empty()
    call_count = 0

    for pair_name in FOREX_PAIRS:
        row_data = {'Devises': pair_name}
        for tf_key, tf_display_name in zip(TIMEFRAMES_FETCH_KEYS, TIMEFRAMES_DISPLAY):
            call_count += 1
            status_widget.text(f"Analysing: {pair_name} ({tf_display_name}) - Call {call_count}/{total_calls}... (API delay in effect)")
            data_ohlc = fetch_forex_data_av(pair_name, tf_key, av_api_key)
            
            rsi_value, rsi_series = calculate_rsi(data_ohlc, period=10)
            divergence_signal = "Aucune"
            if data_ohlc is not None and rsi_series is not None:
                divergence_signal = detect_divergence(data_ohlc, rsi_series)
            
            row_data[tf_display_name] = {'rsi': rsi_value, 'divergence': divergence_signal}
            progress_widget.progress(call_count / total_calls)

        results_list.append(row_data)

    st.session_state.results = results_list
    st.session_state.last_scan_time = datetime.now()
    st.session_state.scan_done = True
    status_widget.empty()
    progress_widget.empty()


# --- Interface Utilisateur Streamlit ---
st.markdown('<h1 class="screener-header">📊 Screener RSI & Divergence</h1>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Rescan All Forex Pairs", key="rescan_button", use_container_width=True):
        st.session_state.scan_done = False
        st.cache_data.clear()
        st.rerun() # CORRIGÉ: Utilisation de la nouvelle fonction st.rerun()

if 'scan_done' not in st.session_state or not st.session_state.scan_done:
    run_analysis_process(api_key)
    st.success(f"✅ Analysis complete! {len(FOREX_PAIRS)} pairs analyzed.")

if 'results' in st.session_state and st.session_state.results:
    last_scan_time_str = st.session_state.last_scan_time.strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"""<div class="update-info">🔄 Last update: {last_scan_time_str} (Data from Alpha Vantage)</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="legend-container">
        <div class="legend-item"><div class="legend-dot oversold-dot"></div><span>Oversold (RSI ≤ 20)</span></div>
        <div class="legend-item"><div class="legend-dot overbought-dot"></div><span>Overbought (RSI ≥ 80)</span></div>
        <div class="legend-item"><span class="divergence-icon">🐂</span><span>Bullish Divergence</span></div>
        <div class="legend-item"><span class="divergence-icon">🐻</span><span>Bearish Divergence</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("### 📈 RSI & Divergence Analysis Results")
    
    html_table = '<table class="rsi-table">'
    html_table += '<thead><tr><th>Devises</th>'
    for tf_display_name in TIMEFRAMES_DISPLAY: html_table += f'<th>{tf_display_name}</th>'
    html_table += '</tr></thead><tbody>'

    for row in st.session_state.results:
        html_table += f'<tr><td class="devises-cell">{row["Devises"]}</td>'
        for tf_display_name in TIMEFRAMES_DISPLAY:
            cell_data = row.get(tf_display_name, {'rsi': np.nan, 'divergence': 'Aucune'})
            rsi_val = cell_data.get('rsi', np.nan)
            divergence = cell_data.get('divergence', 'Aucune')
            css_class = get_rsi_class(rsi_val)
            formatted_val = format_rsi(rsi_val)
            divergence_icon = ""
            if divergence == "Haussière": divergence_icon = '<span class="divergence-icon">🐂</span>'
            elif divergence == "Baissière": divergence_icon = '<span class="divergence-icon">🐻</span>'
            html_table += f'<td class="{css_class}">{formatted_val} {divergence_icon}</td>'
        html_table += '</tr>'
    html_table += '</tbody></table>'
    st.markdown(html_table, unsafe_allow_html=True)

    st.markdown("### 📊 Signal Statistics")
    stat_cols = st.columns(len(TIMEFRAMES_DISPLAY))
    for i, tf_display_name in enumerate(TIMEFRAMES_DISPLAY):
        tf_data = [row.get(tf_display_name, {}) for row in st.session_state.results]
        valid_rsi_values = [d.get('rsi') for d in tf_data if pd.notna(d.get('rsi'))]
        bullish_div_count = sum(1 for d in tf_data if d.get('divergence') == 'Haussière')
        bearish_div_count = sum(1 for d in tf_data if d.get('divergence') == 'Baissière')

        if valid_rsi_values:
            oversold_count = sum(1 for x in valid_rsi_values if x <= 20)
            overbought_count = sum(1 for x in valid_rsi_values if x >= 80)
            total_signals = oversold_count + overbought_count + bullish_div_count + bearish_div_count
            delta_text = f"🔴 {oversold_count} S | 🟢 {overbought_count} B | 🐂 {bullish_div_count} | 🐻 {bearish_div_count}"
            with stat_cols[i]: st.metric(label=f"Signals {tf_display_name}", value=str(total_signals), delta=delta_text, delta_color="off")
        else:
            with stat_cols[i]: st.metric(label=f"Signals {tf_display_name}", value="N/A", delta="No data")

# --- Guide Utilisateur et Footer ---
with st.expander("ℹ️ User Guide & Configuration", expanded=False):
    st.markdown("""
    ## Data Source: Alpha Vantage
    - **API Key**: Securely loaded from Streamlit Secrets.
    - **Rate Limit**: The free plan is limited to 5 API calls per minute. A 13-second delay is added between each data request, so a full scan takes several minutes.
    ## Analysis Configuration
    - **RSI Period**: 10 | **Source**: OHLC4
    - **Divergence**: Checks for regular bullish/bearish divergences on the last 30 candles.
    """)
st.markdown("<div class='footer'>*Data provided by Alpha Vantage*</div>", unsafe_allow_html=True)

# --- END OF FILE app.py ---
