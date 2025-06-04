# --- START OF FILE app.py ---

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="RSI Forex Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS personnalisé (identique à votre version précédente) ---
st.markdown("""
<style>
    /* ... (VOTRE CSS COMPLET ICI) ... */
    /* Styles généraux */
    .main > div { padding-top: 2rem; }
    .stApp {
        /* background-color: #0E1117; */
        /* color: #FAFAFA; */
    }
    .screener-header { 
        font-size: 28px; 
        font-weight: bold; 
        color: #FAFAFA; 
        margin-bottom: 15px; 
        text-align: center;
    }
    .update-info { 
        background-color: #262730; 
        padding: 8px 15px; 
        border-radius: 5px; 
        margin-bottom: 20px; 
        font-size: 14px; 
        color: #A9A9A9; 
        border: 1px solid #333A49;
        text-align: center;
    }
    .legend-container { 
        display: flex; 
        justify-content: center; 
        gap: 40px; 
        margin: 25px 0; 
        padding: 10px; 
        border-radius: 5px;
        background-color: #1A1C22; 
    }
    .legend-item { 
        display: flex; 
        align-items: center; 
        gap: 8px; 
        font-size: 14px; 
        color: #D3D3D3; 
    }
    .legend-dot { 
        width: 12px; 
        height: 12px; 
        border-radius: 50%; 
    }
    .oversold-dot { background-color: #FF4B4B; } 
    .overbought-dot { background-color: #3D9970; } 
    
    h3 { 
        color: #EAEAEA;
        text-align: center;
        margin-top: 30px;
        margin-bottom: 15px;
    }

    .rsi-table { 
        width: 100%; 
        border-collapse: collapse; 
        margin: 20px 0; 
        font-size: 13px; 
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1); 
    }
    .rsi-table th { 
        background-color: #333A49; 
        color: #EAEAEA !important; 
        padding: 14px 10px; 
        text-align: center; 
        font-weight: bold; 
        font-size: 15px; 
        border: 1px solid #262730; 
    }
    .rsi-table td { 
        padding: 12px 10px; 
        text-align: center; 
        border: 1px solid #262730; 
        font-size: 14px; 
    }
    
    .devises-cell { 
        font-weight: bold !important;
        color: #E0E0E0 !important; 
        font-size: 15px !important; 
        text-align: left !important; 
        padding-left: 15px !important;
    }
    
    .oversold-cell { 
        background-color: #FF4B4B !important; 
        color: white !important; 
        font-weight: bold; 
    }
    .overbought-cell { 
        background-color: #3D9970 !important; 
        color: white !important; 
        font-weight: bold; 
    }
    
    .neutral-cell { 
        color: #C0C0C0 !important; 
        background-color: #161A1D; 
    }

    .stats-container { margin-top: 30px; }
    .stMetric { 
        background-color: #1A1C22;
        border: 1px solid #333A49;
        border-radius: 5px;
        padding: 15px;
    }
    .stMetric > label { 
        color: #A9A9A9 !important;
    }
    .stMetric > div:nth-child(2) > div { 
        color: #EAEAEA !important;
        font-size: 1.75rem !important;
    }
    .stMetric > div:nth-child(3) > div { 
        color: #A9A9A9 !important; 
    }

    .stExpander > summary {
        background-color: #1A1C22;
        color: #EAEAEA;
        font-size: 16px;
        border-radius: 5px;
    }
    .stExpander > summary:hover {
        background-color: #262730;
    }
    .stExpanderDetails {
        background-color: #0E1117; 
        color: #D3D3D3;
        padding: 15px;
        border: 1px solid #333A49;
        border-top: none; 
        border-radius: 0 0 5px 5px;
    }
    .stExpanderDetails h2, .stExpanderDetails h3 { color: #EAEAEA; }
    .stExpanderDetails li { margin-bottom: 5px; }

    .footer {
        text-align: center;
        font-size: 12px;
        color: #A9A9A9;
        margin-top: 40px;
        padding-bottom: 20px;
    }
    #MainMenu {visibility: hidden;} /* Cacher le menu Streamlit hamburger */
    footer {visibility: hidden;} /* Cacher le footer "Made with Streamlit" */

</style>
""", unsafe_allow_html=True)


# --- Fonctions de calcul et de récupération de données (identiques) ---
def calculate_rsi(prices, period=10):
    try:
        if prices is None or len(prices) < period + 1: return np.nan
        close_col = 'Adj Close' if 'Adj Close' in prices.columns else 'Close'
        o = prices['Open']
        h = prices['High']
        l = prices['Low']
        c = prices[close_col] 
        ohlc4 = (o + h + l + c) / 4
        delta = ohlc4.diff()
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        if len(gains.dropna()) < period or len(losses.dropna()) < period: return np.nan
        avg_gains = gains.ewm(com=period - 1, adjust=False, min_periods=period).mean()
        avg_losses = losses.ewm(com=period - 1, adjust=False, min_periods=period).mean()
        if avg_losses.empty or avg_gains.empty or avg_losses.iloc[-1] is np.nan or avg_gains.iloc[-1] is np.nan:
            return np.nan
        last_avg_loss = avg_losses.iloc[-1]
        last_avg_gain = avg_gains.iloc[-1]
        if pd.isna(last_avg_loss) or pd.isna(last_avg_gain): return np.nan
        if last_avg_loss == 0: return 100.0 if last_avg_gain > 0 else 50.0
        rs = last_avg_gain / last_avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi if pd.notna(rsi) else np.nan
    except Exception:
        return np.nan

def get_yahoo_symbol(pair): return pair.replace('/', '') + '=X'

def fetch_forex_data(symbol, timeframe_key):
    try:
        yahoo_symbol = get_yahoo_symbol(symbol)
        params = {
            'H1': {'period': '5d', 'interval': '1h'},
            'H4': {'period': '20d', 'interval': '4h'},
            'D1': {'period': '60d', 'interval': '1d'},
            'W1': {'period': '1y', 'interval': '1wk'}
        }
        if timeframe_key not in params: return None
        ticker = yf.Ticker(yahoo_symbol)
        data = ticker.history(
            period=params[timeframe_key]['period'], 
            interval=params[timeframe_key]['interval'],
            auto_adjust=False, 
            prepost=False,
            actions=False
        )
        if data is None or data.empty or not all(col in data.columns for col in ['Open', 'High', 'Low', 'Close']):
            data = ticker.history(
                period=params[timeframe_key]['period'], 
                interval=params[timeframe_key]['interval'],
                auto_adjust=True, 
                prepost=False,
                actions=False
            )
        if data is None or data.empty or len(data) < 15 or not all(col in data.columns for col in ['Open', 'High', 'Low', 'Close']):
            return None
        return data
    except Exception:
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
    'EUR/GBP', 'EUR/AUD', 'EUR/CAD', 'EUR/NZD', 'EUR/CHF',
    'GBP/AUD', 'GBP/CAD', 'GBP/CHF', 'GBP/NZD',
    'AUD/CAD', 'AUD/CHF', 'AUD/NZD',
    'CAD/CHF',
    'NZD/CAD', 'NZD/CHF'
]
TIMEFRAMES_DISPLAY = ['H1', 'H4', 'Daily', 'Weekly']
TIMEFRAMES_FETCH_KEYS = ['H1', 'H4', 'D1', 'W1']

# --- Fonction principale d'analyse ---
def run_analysis_process():
    """Exécute l'analyse RSI pour toutes les paires et stocke les résultats en session_state."""
    results_list = []
    total_pairs = len(FOREX_PAIRS)
    
    # Réinitialiser la barre de progression et le texte de statut
    if 'progress_bar' not in st.session_state:
        st.session_state.progress_bar = st.empty()
    if 'status_text' not in st.session_state:
        st.session_state.status_text = st.empty()
        
    progress_widget = st.session_state.progress_bar.progress(0)
    status_widget = st.session_state.status_text.empty() # Pour s'assurer qu'il est vide avant d'écrire

    for i, pair_name in enumerate(FOREX_PAIRS):
        status_widget.text(f"Analysing: {pair_name} ({i+1}/{total_pairs})")
        row_data = {'Devises': pair_name}
        for tf_key, tf_display_name in zip(TIMEFRAMES_FETCH_KEYS, TIMEFRAMES_DISPLAY):
            data_ohlc = fetch_forex_data(pair_name, tf_key)
            rsi_value = calculate_rsi(data_ohlc, period=10)
            row_data[tf_display_name] = rsi_value
        results_list.append(row_data)
        progress_widget.progress((i + 1) / total_pairs)

    st.session_state.results = results_list
    st.session_state.last_scan_time = datetime.now()
    st.session_state.scan_done = True
    
    # Nettoyer la barre de progression et le texte de statut après la fin
    status_widget.empty()
    progress_widget.empty()
    st.success(f"✅ Analysis complete! {len(FOREX_PAIRS)} pairs analyzed.")


# --- Interface Utilisateur Streamlit ---
st.markdown('<h1 class="screener-header">📊 Screener Analysis</h1>', unsafe_allow_html=True)

# Bouton pour relancer l'analyse
# Placer le bouton en haut pour qu'il soit visible
col1, col2, col3 = st.columns([1,2,1]) # Pour centrer le bouton ou le mettre sur le côté
with col2: # Ou utilisez st.columns pour un meilleur placement
    if st.button("🔄 Rescan All Forex Pairs", key="rescan_button", use_container_width=True):
        st.session_state.scan_done = False # Force le rescan
        # On ne lance pas run_analysis_process() ici directement pour éviter des exécutions multiples
        # Streamlit va ré-exécuter le script, et la logique ci-dessous s'en chargera.
        # st.experimental_rerun() # Optionnel, pour forcer un rerun immédiat si besoin


# Logique pour exécuter l'analyse (initiale ou rescan)
if 'scan_done' not in st.session_state or not st.session_state.scan_done:
    with st.spinner("🔍 Performing analysis... This may take a moment."):
        # Créer des placeholders pour la barre de progression et le texte de statut s'ils n'existent pas
        if 'progress_bar_placeholder' not in st.session_state:
            st.session_state.progress_bar_placeholder = st.empty()
        if 'status_text_placeholder' not in st.session_state:
            st.session_state.status_text_placeholder = st.empty()
        
        # Assigner les widgets de progression à ces placeholders
        # Cette approche de placeholder doit être affinée si on utilise un spinner global.
        # Il est plus simple de les créer dans run_analysis_process et les vider.
        # Pour cette version, je vais les créer à l'intérieur de run_analysis_process
        # et le spinner s'occupera de l'indication globale.
        run_analysis_process()

# Affichage des résultats si l'analyse a été faite
if 'results' in st.session_state and st.session_state.results:
    last_scan_time_str = st.session_state.last_scan_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    st.markdown(f"""<div class="update-info">🔄 Analysis updated. Last update: {last_scan_time_str}</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="legend-container">
        <div class="legend-item"><div class="legend-dot oversold-dot"></div><span>Oversold (RSI ≤ 20)</span></div>
        <div class="legend-item"><div class="legend-dot overbought-dot"></div><span>Overbought (RSI ≥ 80)</span></div>
    </div>""", unsafe_allow_html=True)

    # Placeholder pour la barre de progression et le texte de statut (doivent être créés avant leur utilisation dans run_analysis_process)
    # Ces placeholders seront remplis par run_analysis_process
    st.session_state.progress_bar = st.empty() 
    st.session_state.status_text = st.empty()


    st.markdown("### 📈 RSI Analysis Results")
    html_table = '<table class="rsi-table">'
    html_table += '<thead><tr><th>Devises</th>'
    for tf_display_name in TIMEFRAMES_DISPLAY: html_table += f'<th>{tf_display_name}</th>'
    html_table += '</tr></thead><tbody>'

    for row_idx, row in enumerate(st.session_state.results):
        devises_text = str(row.get("Devises", f"N/A_ROW_{row_idx}")).strip()
        if not devises_text: devises_text = f"EMPTY_ROW_{row_idx}"
        html_table += f'<tr><td class="devises-cell">{devises_text}</td>'
        for tf_display_name in TIMEFRAMES_DISPLAY:
            rsi_val = row.get(tf_display_name, np.nan)
            css_class = get_rsi_class(rsi_val)
            formatted_val = format_rsi(rsi_val)
            html_table += f'<td class="{css_class}">{formatted_val}</td>'
        html_table += '</tr>'
    html_table += '</tbody></table>'
    st.markdown(html_table, unsafe_allow_html=True)

    st.markdown('<div class="stats-container">', unsafe_allow_html=True)
    st.markdown("### 📊 Signal Statistics")
    num_timeframes = len(TIMEFRAMES_DISPLAY)
    stat_cols = st.columns(num_timeframes)
    for i, tf_display_name in enumerate(TIMEFRAMES_DISPLAY):
        rsi_values_for_tf = [row.get(tf_display_name, np.nan) for row in st.session_state.results]
        valid_rsi_values = [val for val in rsi_values_for_tf if pd.notna(val)]
        if valid_rsi_values:
            oversold_count = sum(1 for x in valid_rsi_values if x <= 20)
            overbought_count = sum(1 for x in valid_rsi_values if x >= 80)
            total_signals_count = oversold_count + overbought_count
            with stat_cols[i]: st.metric(
                label=f"Signals {tf_display_name}",
                value=str(total_signals_count),
                delta=f"🔴 {oversold_count} S | 🟢 {overbought_count} B", 
                delta_color="off"
            )
        else:
            with stat_cols[i]: st.metric(label=f"Signals {tf_display_name}", value="N/A", delta="No data")
    st.markdown('</div>', unsafe_allow_html=True)
    # Le message st.success est maintenant dans run_analysis_process

elif 'scan_done' in st.session_state and not st.session_state.scan_done:
    # Si le scan est en cours (défini par le spinner), ne rien afficher d'autre ici
    pass
else:
    st.info("Click 'Rescan All Forex Pairs' to start the analysis.")


# --- Guide Utilisateur et Footer (identiques) ---
with st.expander("ℹ️ User Guide & Configuration", expanded=False):
    st.markdown("""
    ## RSI Configuration
    - **Period**: 10
    - **Source**: OHLC4 (average of Open, High, Low, Close prices)
    - **Thresholds**: Oversold ≤ 20 | Overbought ≥ 80
    ## Timeframes & Data Source
    - **H1**: Hourly data (last 5 days)
    - **H4**: 4-hour data (last 20 days)
    - **Daily (D1)**: Daily data (last 60 days)
    - **Weekly (W1)**: Weekly data (last 1 year)
    - *Data sourced from Yahoo Finance.*
    ## How to Use
    - Click 'Rescan All Forex Pairs' to start or update the analysis.
    - The analysis may take a moment to complete.
    - Colored cells indicate potential opportunities:
      - <span style="color:#FF4B4B; font-weight:bold;">🔴 Red</span>: Oversold (RSI ≤ 20) - Potential Buy Signal
      - <span style="color:#3D9970; font-weight:bold;">🟢 Green</span>: Overbought (RSI ≥ 80) - Potential Sell Signal
    - *This tool is for informational purposes only and not financial advice.*
    ## Analyzed Pairs
    The screener analyzes a comprehensive list of major and minor Forex pairs.
    """, unsafe_allow_html=True)

st.markdown("<div class='footer'>*Developed with Streamlit | RSI OHLC4 Period 10*</div>", unsafe_allow_html=True)

# --- END OF FILE app.py ---
