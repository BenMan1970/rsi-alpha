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
    page_title="RSI & Divergence Screener (Alpha Vantage)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" # MODIFIÉ: La sidebar n'est plus nécessaire au démarrage
)

# --- CSS (identique, aucune modification nécessaire) ---
# Assurez-vous que votre CSS est bien présent ici
st.markdown("""<style>/* ... VOTRE CSS COMPLET ICI ... */</style>""", unsafe_allow_html=True)

# --- MODIFIÉ: Accès à l'API Key via st.secrets ---
try:
    # Tente de récupérer la clé API depuis les secrets de Streamlit
    api_key = st.secrets["alpha_vantage_api_key"]
except KeyError:
    # Si la clé n'est pas trouvée, affiche un message d'erreur et arrête l'application
    st.error("🔑 Clé API Alpha Vantage non trouvée !")
    st.info("Veuillez ajouter votre clé API dans les 'Secrets' des paramètres de l'application sur Streamlit Cloud.")
    st.code('alpha_vantage_api_key = "VOTRE_CLE_API"')
    st.stop()


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

# --- Fonction de récupération de données (légèrement modifiée pour ne plus passer la clé en argument partout) ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_forex_data_av(symbol, timeframe_key, av_api_key): # La clé est toujours nécessaire ici
    try:
        ts = TimeSeries(key=av_api_key, output_format='pandas')
        from_symbol, to_symbol = symbol.split('/')
        data = None
        if timeframe_key == 'H4':
             _data, _ = ts.get_intraday(from_symbol=from_symbol, to_symbol=to_symbol, interval='60min', outputsize='full')
             if _data is not None and not _data.empty:
                _data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}, inplace=True)
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
        data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}, inplace=True)
        data.index = pd.to_datetime(data.index)
        data = data.astype(float).sort_index(ascending=True)
        return data
    except Exception as e:
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

# --- Fonction principale d'analyse (reçoit toujours la clé) ---
def run_analysis_process(av_api_key):
    results_list = []
    total_pairs = len(FOREX_PAIRS)
    progress_widget = st.progress(0)
    status_widget = st.empty()

    for i, pair_name in enumerate(FOREX_PAIRS):
        status_widget.text(f"Analysing: {pair_name} ({i+1}/{total_pairs})... (API delay in effect)")
        row_data = {'Devises': pair_name}
        for tf_key, tf_display_name in zip(TIMEFRAMES_FETCH_KEYS, TIMEFRAMES_DISPLAY):
            data_ohlc = fetch_forex_data_av(pair_name, tf_key, av_api_key)
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

# SUPPRIMÉ: La vérification manuelle de la clé API n'est plus nécessaire ici.
# Elle est faite au tout début du script.

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Rescan All Forex Pairs", key="rescan_button", use_container_width=True):
        st.session_state.scan_done = False
        st.cache_data.clear()
        st.experimental_rerun()

if 'scan_done' not in st.session_state or not st.session_state.scan_done:
    run_analysis_process(api_key) # Passe la clé récupérée des secrets

# L'affichage des résultats reste le même.
# Assurez-vous que le code de la construction du tableau et des statistiques est bien là.
if 'results' in st.session_state and st.session_state.results:
    # ... (Le reste de votre code d'affichage est parfait et n'a pas besoin de changer)
    # ... Collez ici toute la partie qui commence par `last_scan_time_str = ...`
    # ... jusqu'à la fin du fichier.
    pass # Placeholder, mettez votre code ici

# --- END OF FILE app.py ---
