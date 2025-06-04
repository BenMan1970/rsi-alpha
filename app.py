# --- START OF FILE code rsi gem.py ---

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuration de la page Streamlit
st.set_page_config(
    page_title="RSI Forex Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé
st.markdown("""
<style>
    .main > div { padding-top: 2rem; }
    .screener-header { font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
    .update-info { background-color: #f8f9fa; padding: 8px 15px; border-radius: 5px; margin-bottom: 15px; font-size: 14px; color: #495057; }
    .legend-container { display: flex; justify-content: center; gap: 40px; margin: 20px 0; padding: 10px; }
    .legend-item { display: flex; align-items: center; gap: 8px; font-size: 14px; }
    .legend-dot { width: 12px; height: 12px; border-radius: 50%; }
    .oversold-dot { background-color: #dc3545; }
    .overbought-dot { background-color: #28a745; }
    .rsi-table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px; }
    .rsi-table th {
        background-color: #6c757d;
        color: white !important;
        padding: 12px 8px;
        text-align: center;
        font-weight: bold;
        border: 1px solid #dee2e6;
    }
    .rsi-table td {
        padding: 10px 8px;
        text-align: center;
        border: 1px solid #dee2e6;
    }

    /* MODIFICATION: Style de la cellule 'Devises' rendu plus standard */
    .devises-cell {
        font-weight: bold !important;
        /* color: #FF0000 !important;  Exemple de débogage retiré */
        /* border: 2px dashed #00FF00 !important; Exemple de débogage retiré */
        /* font-size: 16px !important;  Peut être ajusté si nécessaire, sinon utilise la taille par défaut de la table */
        color: #2c3e50 !important; /* Couleur de texte plus sobre */
    }

    .oversold-cell { background-color: #dc3545 !important; color: white !important; font-weight: bold; }
    .overbought-cell { background-color: #28a745 !important; color: white !important; font-weight: bold; }

    .neutral-cell {
        color: #1E1E1E !important;
    }
    .stats-container { margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

def calculate_rsi(prices, period=10):
    try:
        if prices is None or len(prices) < period + 1: return np.nan
        ohlc4 = (prices['Open'] + prices['High'] + prices['Low'] + prices['Close']) / 4
        delta = ohlc4.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        if len(gains.dropna()) < period or len(losses.dropna()) < period: return np.nan
        avg_gains = gains.ewm(span=period, adjust=False, min_periods=period).mean()
        avg_losses = losses.ewm(span=period, adjust=False, min_periods=period).mean()
        if avg_losses.empty or avg_gains.empty: return np.nan
        last_avg_loss, last_avg_gain = avg_losses.iloc[-1], avg_gains.iloc[-1]
        if pd.isna(last_avg_loss) or pd.isna(last_avg_gain): return np.nan
        if last_avg_loss == 0: return 100 if last_avg_gain > 0 else 50
        rs = last_avg_gain / last_avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi if pd.notna(rsi) else np.nan
    except Exception: return np.nan

def get_yahoo_symbol(pair): return pair.replace('/', '') + '=X'

def fetch_forex_data(symbol, timeframe_key):
    try:
        yahoo_symbol = get_yahoo_symbol(symbol)
        params = {'H1': {'period': '5d', 'interval': '1h'}, 'H4': {'period': '1mo', 'interval': '4h'},
                  'D1': {'period': '3mo', 'interval': '1d'}, 'W1': {'period': '2y', 'interval': '1wk'}}
        if timeframe_key not in params: return None
        ticker = yf.Ticker(yahoo_symbol)
        data = ticker.history(period=params[timeframe_key]['period'], interval=params[timeframe_key]['interval'],
                              auto_adjust=True, prepost=False)
        if data is None or data.empty or len(data) < 15: # 15 est un seuil pour avoir assez de données pour RSI 10 + buffer
            # st.warning(f"Not enough data for {yahoo_symbol} on {timeframe_key}. Fetched {len(data) if data is not None else 0} rows.")
            return None
        return data
    except Exception as e:
        # st.error(f"Error fetching data for {symbol} ({timeframe_key}): {e}")
        return None

def format_rsi(value): return "N/A" if pd.isna(value) else f"{value:.2f}"

def get_rsi_class(value):
    if pd.isna(value): return "neutral-cell"
    elif value <= 20: return "oversold-cell"
    elif value >= 80: return "overbought-cell"
    return "neutral-cell"

st.markdown('<h1 class="screener-header">📊 Screener Analysis</h1>', unsafe_allow_html=True)
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"""<div class="update-info">🔄 Analysis updated. Last update: {current_time}</div>""", unsafe_allow_html=True)
st.markdown("""<div class="legend-container">
    <div class="legend-item"><div class="legend-dot oversold-dot"></div><span>Oversold (RSI ≤ 20)</span></div>
    <div class="legend-item"><div class="legend-dot overbought-dot"></div><span>Overbought (RSI ≥ 80)</span></div>
</div>""", unsafe_allow_html=True)

forex_pairs = ['EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD', 'EUR/JPY', 'GBP/JPY', 'EUR/GBP']
timeframes_display = ['H1', 'H4', 'Daily', 'Weekly']
timeframes_fetch_keys = ['H1', 'H4', 'D1', 'W1']
filtered_pairs = forex_pairs # Pour l'instant, toutes les paires sont analysées

progress_bar = st.progress(0)
status_text = st.empty()
results = []
total_pairs = len(filtered_pairs)

for i, pair_name in enumerate(filtered_pairs):
    status_text.text(f"Analysing: {pair_name} ({i+1}/{total_pairs})")
    row_data = {'Devises': pair_name}
    for tf_key, tf_display_name in zip(timeframes_fetch_keys, timeframes_display):
        data_ohlc = fetch_forex_data(pair_name, tf_key)
        rsi_value = calculate_rsi(data_ohlc, period=10)
        row_data[tf_display_name] = rsi_value
    results.append(row_data)
    progress_bar.progress((i + 1) / total_pairs)

progress_bar.empty(); status_text.empty()

# --- SECTION DE DÉBOGAGE (peut être commentée ou supprimée en production) ---
# st.subheader("Debug: Raw Data Check")
# st.write("Vérification des données dans la liste `results` avant la génération du tableau HTML:")
# if results:
#     st.json(results)
#     all_devises_present = True
#     for idx, item in enumerate(results):
#         if 'Devises' not in item or not item['Devises']:
#             st.error(f"Erreur: La clé 'Devises' est manquante ou vide pour l'élément {idx}: {item}")
#             all_devises_present = False
#     if all_devises_present:
#         st.success("Succès: La clé 'Devises' est présente et non vide pour tous les éléments de 'results'.")
# else:
#     st.warning("Attention: La liste `results` est vide.")
# st.write("--- FIN SECTION DE DÉBOGAGE ---")
# --- FIN SECTION DE DÉBOGAGE ---


st.markdown("### 📈 RSI Analysis Results")
html_table = '<table class="rsi-table">'
html_table += '<thead><tr><th>Devises</th>'
for tf_display_name in timeframes_display: html_table += f'<th>{tf_display_name}</th>'
html_table += '</tr></thead><tbody>'

for row_idx, row in enumerate(results):
    devises_text = str(row.get("Devises", f"DEVISE_MANQUANTE_LIGNE_{row_idx}")).strip()
    if not devises_text:
        devises_text = f"DEVISE_VIDE_LIGNE_{row_idx}"

    html_table += f'<tr><td class="devises-cell">{devises_text}</td>'

    for tf_display_name in timeframes_display:
        rsi_val = row.get(tf_display_name, np.nan)
        css_class = get_rsi_class(rsi_val)
        formatted_val = format_rsi(rsi_val)
        html_table += f'<td class="{css_class}">{formatted_val}</td>'
    html_table += '</tr>'
html_table += '</tbody></table>'
st.markdown(html_table, unsafe_allow_html=True)

st.markdown('<div class="stats-container">', unsafe_allow_html=True)
st.markdown("### 📊 Signal Statistics")
if results: # S'assurer qu'il y a des résultats avant de calculer les statistiques
    num_timeframes = len(timeframes_display)
    stat_cols = st.columns(num_timeframes)
    for i, tf_display_name in enumerate(timeframes_display):
        rsi_values_for_tf = [row.get(tf_display_name, np.nan) for row in results]
        valid_rsi_values = [val for val in rsi_values_for_tf if pd.notna(val)]
        if valid_rsi_values:
            oversold_count = sum(1 for x in valid_rsi_values if x <= 20)
            overbought_count = sum(1 for x in valid_rsi_values if x >= 80)
            total_signals_count = oversold_count + overbought_count
            with stat_cols[i]: st.metric(label=f"Signals {tf_display_name}", value=str(total_signals_count), delta=f"🔴 {oversold_count} | 🟢 {overbought_count}", delta_color="off")
        else:
            with stat_cols[i]: st.metric(label=f"Signals {tf_display_name}", value="N/A", delta="No data")
else:
    st.warning("No results to display statistics.")
st.markdown('</div>', unsafe_allow_html=True)
st.success(f"✅ Analysis complete! {len(filtered_pairs)} pairs analyzed.")

with st.expander("ℹ️ User Guide"):
    st.markdown("""
    ## RSI Configuration
    - **Period**: 10
    - **Source**: OHLC4 (average of Open, High, Low, Close prices)
    - **Thresholds**: Oversold ≤ 20 | Overbought ≥ 80
    ## Timeframes
    - **H1**: Hourly data (last 5 days)
    - **H4**: 4-hour data (last 1 month)
    - **Daily (D1)**: Daily data (last 3 months)
    - **Weekly (W1)**: Weekly data (last 2 years)
    ## How to Use
    - Analysis runs automatically when the page loads.
    - Colored cells indicate opportunities:
      - 🔴 Red: Oversold (RSI ≤ 20)
      - 🟢 Green: Overbought (RSI ≥ 80)
    ## Analyzed Pairs
    EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/JPY, GBP/JPY, EUR/GBP
    """)

st.markdown("---"); st.markdown("*Developed with Streamlit | Data from Yahoo Finance | RSI OHLC4 Period 10*")
# --- END OF FILE code rsi gem.py ---
  
