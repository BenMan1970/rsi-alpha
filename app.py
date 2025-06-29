# --- START OF FILE app.py ---

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import time # NOUVEAU: Pour gérer la limitation de l'API
from alpha_vantage.timeseries import TimeSeries # NOUVEAU: Librairie Alpha Vantage
from scipy.signal import find_peaks

warnings.filterwarnings('ignore')

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="RSI & Divergence Screener (Alpha Vantage)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded" # MODIFIÉ: Pour afficher la config API
)

# --- CSS (identique, aucune modification nécessaire) ---
st.markdown("""<style>/* ... VOTRE CSS COMPLET ICI ... */</style>""", unsafe_allow_html=True) # J'ai masqué le CSS pour la lisibilité, mais vous devez le laisser

# --- NOUVEAU: Configuration de l'API dans la barre latérale ---
st.sidebar.header("🔑 Configuration API")
api_key = st.sidebar.text_input("Entrez votre clé API Alpha Vantage", type="password")

st.sidebar.info(
    "Une clé API Alpha Vantage est requise. "
    "Le plan gratuit est limité à 5 appels/minute, l'analyse sera donc lente. "
    "[Obtenez une clé gratuite ici](https://www.alphavantage.co/support/#api-key)"
)

# --- Fonctions de calcul (RSI, Divergence) - Inchangées ---
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

# --- MODIFIÉ: Fonction de récupération de données pour Alpha Vantage ---
@st.cache_data(ttl=3600, show_spinner=False) # Mise en cache pour éviter les rappels inutiles
def fetch_forex_data_av(symbol, timeframe_key, api_key):
    """Récupère les données de Alpha Vantage et les formate."""
    try:
        ts = TimeSeries(key=api_key, output_format='pandas')
        from_symbol, to_symbol = symbol.split('/')

        data = None
        # Alpha Vantage n'a pas de timeframe H4 natif, on le reconstruit depuis H1
        if timeframe_key == 'H4':
             _data, _ = ts.get_intraday(from_symbol=from_symbol, to_symbol=to_symbol, interval='60min', outputsize='full')
             if _data is not None and not _data.empty:
                # Renommage et conversion
                _data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}, inplace=True)
                _data.index = pd.to_datetime(_data.index)
                _data = _data.astype(float)
                # Resampling en 4H
                data = _data.resample('4H').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last'
                }).dropna()

        elif timeframe_key == 'H1':
            data, _ = ts.get_intraday(from_symbol=from_symbol, to_symbol=to_symbol, interval='60min', outputsize='full')
        elif timeframe_key == 'D1':
            data, _ = ts.get_daily(symbol=f"{from_symbol}{to_symbol}", outputsize='full')
        elif timeframe_key == 'W1':
            data, _ = ts.get_weekly(symbol=f"{from_symbol}{to_symbol}")
        
        # Pause pour respecter la limite de l'API
        time.sleep(13) # 60s / 5 appels = 12s/appel. 13s pour la sécurité.

        if data is None or data.empty:
            return None

        # Nettoyage des données
        data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}, inplace=True)
        data.index = pd.to_datetime(data.index)
        data = data.astype(float)
        data.sort_index(inplace=True) # AV renvoie les données en ordre inversé

        return data

    except Exception as e:
        st.error(f"Erreur API pour {symbol} ({timeframe_key}): {e}")
        time.sleep(13) # Pause même en cas d'erreur
        return None

def format_rsi(value): return "N/A" if pd.isna(value) else f"{value:.2f}"
def get_rsi_class(value):
    if pd.isna(value): return "neutral-cell"
    elif value <= 20: return "oversold-cell"
    elif value >= 80: return "overbought-cell"
    return "neutral-cell"

# --- Constantes ---
FOREX_PAIRS = [ # Liste potentiellement à ajuster selon la dispo sur Alpha Vantage
    'EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD',
    'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'NZD/JPY', 'CAD/JPY', 'CHF/JPY',
    'EUR/GBP', 'EUR/AUD', 'EUR/CAD', 'EUR/NZD', 'EUR/CHF'
]
TIMEFRAMES_DISPLAY = ['H1', 'H4', 'Daily', 'Weekly']
TIMEFRAMES_FETCH_KEYS = ['H1', 'H4', 'D1', 'W1']

# --- Fonction principale d'analyse (modifiée pour passer la clé API) ---
def run_analysis_process(api_key):
    results_list = []
    total_pairs = len(FOREX_PAIRS)
    
    if 'progress_bar' not in st.session_state: st.session_state.progress_bar = st.empty()
    if 'status_text' not in st.session_state: st.session_state.status_text = st.empty()
        
    progress_widget = st.session_state.progress_bar.progress(0)
    status_widget = st.session_state.status_text.empty()

    for i, pair_name in enumerate(FOREX_PAIRS):
        # MODIFIÉ: Message informant de la pause
        status_widget.text(f"Analysing: {pair_name} ({i+1}/{total_pairs})... (API delay in effect)")
        
        row_data = {'Devises': pair_name}
        for tf_key, tf_display_name in zip(TIMEFRAMES_FETCH_KEYS, TIMEFRAMES_DISPLAY):
            # MODIFIÉ: Appel de la nouvelle fonction avec la clé API
            data_ohlc = fetch_forex_data_av(pair_name, tf_key, api_key)
            
            rsi_value, rsi_series = calculate_rsi(data_ohlc, period=10)
            divergence_signal = "Aucune"
            if data_ohlc is not None and rsi_series is not None:
                divergence_signal = detect_divergence(data_ohlc, rsi_series)
            
            row_data[tf_display_name] = {'rsi': rsi_value, 'divergence': divergence_signal}
            
        results_list.append(row_data)
        progress_widget.progress((i + 1) / total_pairs)

    st.session_state.results = results_list
    st.session_state.last_scan_time = datetime.now()
    st.session_state.scan_done = True
    
    status_widget.empty()
    progress_widget.empty()
    st.success(f"✅ Analysis complete! {len(FOREX_PAIRS)} pairs analyzed.")


# --- Interface Utilisateur Streamlit ---
st.markdown('<h1 class="screener-header">📊 Screener RSI & Divergence (Alpha Vantage)</h1>', unsafe_allow_html=True)

# Vérification de la clé API avant de continuer
if not api_key:
    st.warning("Veuillez entrer votre clé API Alpha Vantage dans la barre latérale pour commencer.")
    st.stop() # Arrête l'exécution du script si pas de clé

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Rescan All Forex Pairs", key="rescan_button", use_container_width=True):
        st.session_state.scan_done = False
        st.cache_data.clear() # Vider le cache pour forcer un nouveau scan
        st.experimental_rerun()

# Logique d'exécution
if 'scan_done' not in st.session_state or not st.session_state.scan_done:
    run_analysis_process(api_key) # Passe la clé API

# Affichage des résultats (le reste du code est presque identique)
if 'results' in st.session_state and st.session_state.results:
    last_scan_time_str = st.session_state.last_scan_time.strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"""<div class="update-info">🔄 Last update: {last_scan_time_str} (Data from Alpha Vantage)</div>""", unsafe_allow_html=True)
    
    # Légende et tableau (inchangés)
    st.markdown("""<div class="legend-container">...</div>""", unsafe_allow_html=True) # Masqué pour la lisibilité
    st.markdown("### 📈 RSI & Divergence Analysis Results")
    html_table = '<table class="rsi-table">...</table>' # Le code du tableau est identique, masqué pour la lisibilité
    # Vous devez copier/coller la logique de construction du tableau de la version précédente ici
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Statistiques (inchangées)
    st.markdown("### 📊 Signal Statistics")
    # La logique des statistiques est identique, masquée pour la lisibilité
    # Vous devez copier/coller la logique d'affichage des `st.metric` ici

# Guide et Footer
with st.expander("ℹ️ User Guide & Configuration", expanded=False):
    st.markdown("""
    ## Data Source: Alpha Vantage
    - **API Key**: Required. Please enter it in the sidebar.
    - **Rate Limit**: The free plan is limited to 5 API calls per minute. A 13-second delay is added between each data request, so a full scan can take several minutes.
    
    ## Analysis Configuration
    - **RSI Period**: 10 | **Source**: OHLC4
    - **H4 Timeframe**: Note that Alpha Vantage does not provide a native 4-hour timeframe. It is calculated by resampling 1-hour data.
    - **Divergence**: Checks for regular bullish/bearish divergences on the last 30 candles.
    """)
st.markdown("<div class='footer'>*Data provided by Alpha Vantage*</div>", unsafe_allow_html=True)
# --- END OF FILE app.py ---
