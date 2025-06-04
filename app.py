# --- START OF FILE app.py ---

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
    /* Styles généraux */
    .main > div { padding-top: 2rem; }
    .stApp {
        /* Appliquer un fond sombre à toute l'application si ce n'est pas déjà le thème par défaut */
        /* background-color: #0E1117; */ /* Décommentez si vous voulez forcer un fond sombre */
        /* color: #FAFAFA; */ /* Couleur de texte par défaut pour le thème sombre */
    }
    .screener-header { 
        font-size: 28px; /* Taille un peu augmentée */
        font-weight: bold; 
        color: #FAFAFA; /* Couleur claire pour le titre principal */
        margin-bottom: 15px; 
        text-align: center; /* Centrer le titre */
    }
    .update-info { 
        background-color: #262730; /* Fond un peu plus clair que le fond principal */
        padding: 8px 15px; 
        border-radius: 5px; 
        margin-bottom: 20px; 
        font-size: 14px; 
        color: #A9A9A9; /* Gris clair pour le texte d'info */
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
        background-color: #1A1C22; /* Fond léger pour la légende */
    }
    .legend-item { 
        display: flex; 
        align-items: center; 
        gap: 8px; 
        font-size: 14px; 
        color: #D3D3D3; /* Couleur claire pour le texte de la légende */
    }
    .legend-dot { 
        width: 12px; 
        height: 12px; 
        border-radius: 50%; 
    }
    .oversold-dot { background-color: #FF4B4B; } /* Rouge plus vif */
    .overbought-dot { background-color: #3D9970; } /* Vert plus adapté au thème sombre */
    
    h3 { /* Style pour "RSI Analysis Results" et "Signal Statistics" */
        color: #EAEAEA;
        text-align: center;
        margin-top: 30px;
        margin-bottom: 15px;
    }

    /* Styles du tableau RSI */
    .rsi-table { 
        width: 100%; 
        border-collapse: collapse; 
        margin: 20px 0; 
        font-size: 13px; /* Taille de base pour le tableau */
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1); /* Ombre légère pour le tableau */
    }
    .rsi-table th { 
        background-color: #333A49; /* Bleu/Gris foncé pour les en-têtes */
        color: #EAEAEA !important; /* Texte clair pour les en-têtes */
        padding: 14px 10px; /* Padding un peu augmenté */
        text-align: center; 
        font-weight: bold; 
        font-size: 15px; /* Taille de police pour les en-têtes */
        border: 1px solid #262730; 
    }
    .rsi-table td { 
        padding: 12px 10px; /* Padding un peu augmenté */
        text-align: center; 
        border: 1px solid #262730; 
        font-size: 14px; /* Taille de police pour les cellules de données */
    }
    
    .devises-cell { 
        font-weight: bold !important;
        color: #E0E0E0 !important; /* Gris très clair, presque blanc */
        font-size: 15px !important; /* Un peu plus grand */
        text-align: left !important; /* Aligner les devises à gauche pour lisibilité */
        padding-left: 15px !important;
    }
    
    .oversold-cell { 
        background-color: #FF4B4B !important; /* Rouge plus vif */
        color: white !important; 
        font-weight: bold; 
    }
    .overbought-cell { 
        background-color: #3D9970 !important; /* Vert plus adapté au thème sombre */
        color: white !important; 
        font-weight: bold; 
    }
    
    .neutral-cell { 
        color: #C0C0C0 !important; /* Gris argenté, bien visible sur fond sombre */
        background-color: #161A1D; /* Fond très sombre pour les cellules neutres */
    }

    .stats-container { margin-top: 30px; }
    .stMetric { /* Styles pour les st.metric */
        background-color: #1A1C22;
        border: 1px solid #333A49;
        border-radius: 5px;
        padding: 15px;
    }
    .stMetric > label { /* Étiquette de la métrique */
        color: #A9A9A9 !important;
    }
    .stMetric > div:nth-child(2) > div { /* Valeur de la métrique */
        color: #EAEAEA !important;
        font-size: 1.75rem !important;
    }
    .stMetric > div:nth-child(3) > div { /* Delta de la métrique */
        color: #A9A9A9 !important; /* Couleur du texte delta */
    }

    /* Style pour le expander "User Guide" */
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
        background-color: #0E1117; /* Fond du contenu de l'expander */
        color: #D3D3D3;
        padding: 15px;
        border: 1px solid #333A49;
        border-top: none; /* Pas de bordure en haut car déjà sur le summary */
        border-radius: 0 0 5px 5px;
    }
    .stExpanderDetails h2, .stExpanderDetails h3 { color: #EAEAEA; }
    .stExpanderDetails li { margin-bottom: 5px; }

    /* Footer */
    .footer {
        text-align: center;
        font-size: 12px;
        color: #A9A9A9;
        margin-top: 40px;
        padding-bottom: 20px;
    }

</style>
""", unsafe_allow_html=True)

def calculate_rsi(prices, period=10):
    try:
        if prices is None or len(prices) < period + 1: return np.nan
        # Utiliser 'Adj Close' si disponible, sinon 'Close'
        close_col = 'Adj Close' if 'Adj Close' in prices.columns else 'Close'
        # OHLC4 calculation
        o = prices['Open']
        h = prices['High']
        l = prices['Low']
        c = prices[close_col] # Utilisation de la colonne close déterminée
        ohlc4 = (o + h + l + c) / 4

        delta = ohlc4.diff()
        gains = delta.where(delta > 0, 0.0) # Important d'initialiser avec 0.0 pour éviter les types mixtes
        losses = -delta.where(delta < 0, 0.0) # Important d'initialiser avec 0.0

        # S'assurer qu'il y a assez de données après avoir droppé les NaN du diff()
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
    except Exception as e:
        # st.warning(f"Erreur dans calculate_rsi: {e}") # Pour débogage si besoin
        return np.nan

def get_yahoo_symbol(pair): return pair.replace('/', '') + '=X'

def fetch_forex_data(symbol, timeframe_key):
    try:
        yahoo_symbol = get_yahoo_symbol(symbol)
        params = {
            'H1': {'period': '5d', 'interval': '1h'},
            'H4': {'period': '20d', 'interval': '4h'}, # Augmenté '1mo' à '20d' pour plus de barres
            'D1': {'period': '60d', 'interval': '1d'}, # Augmenté '3mo' à '60d'
            'W1': {'period': '1y', 'interval': '1wk'}  # Réduit '2y' à '1y' pour rapidité, ajuster si besoin
        }
        if timeframe_key not in params: return None
        
        # Essayer de télécharger avec auto_adjust=False en premier
        # puis avec auto_adjust=True si le premier échoue ou ne renvoie pas Open, High, Low, Close
        ticker = yf.Ticker(yahoo_symbol)
        data = ticker.history(
            period=params[timeframe_key]['period'], 
            interval=params[timeframe_key]['interval'],
            auto_adjust=False, # Pour obtenir Open, High, Low, Close séparément
            prepost=False,
            actions=False # On n'a pas besoin des dividendes/splits ici
        )

        if data is None or data.empty or not all(col in data.columns for col in ['Open', 'High', 'Low', 'Close']):
             # Essayer avec auto_adjust=True si les colonnes O H L C ne sont pas là
            data = ticker.history(
                period=params[timeframe_key]['period'], 
                interval=params[timeframe_key]['interval'],
                auto_adjust=True, 
                prepost=False,
                actions=False
            )
            # Si auto_adjust=True, 'Close' est souvent le seul prix ajusté.
            # Pour OHLC4, nous avons besoin de O, H, L. On peut les reconstruire si nécessaire
            # ou accepter une légère imprécision. Pour l'instant, on suppose que yfinance les fournit.
            # Si ce n'est pas le cas, il faudrait une logique plus complexe ou utiliser 'Close' pour RSI.

        # Vérifier à nouveau après le second essai potentiel
        if data is None or data.empty or len(data) < 15 or not all(col in data.columns for col in ['Open', 'High', 'Low', 'Close']):
            # st.warning(f"Données insuffisantes ou colonnes manquantes pour {yahoo_symbol} en {timeframe_key}. Lignes: {len(data) if data is not None else 0}")
            return None
        return data
    except Exception as e:
        # st.error(f"Erreur lors du téléchargement pour {symbol} ({timeframe_key}): {e}") # Pour débogage si besoin
        return None

def format_rsi(value): return "N/A" if pd.isna(value) else f"{value:.2f}"

def get_rsi_class(value):
    if pd.isna(value): return "neutral-cell"
    elif value <= 20: return "oversold-cell"
    elif value >= 80: return "overbought-cell"
    return "neutral-cell"

st.markdown('<h1 class="screener-header">📊 Screener Analysis</h1>', unsafe_allow_html=True)
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC") # Ajout de UTC pour clarté
st.markdown(f"""<div class="update-info">🔄 Analysis updated. Last update: {current_time}</div>""", unsafe_allow_html=True)

st.markdown("""<div class="legend-container">
    <div class="legend-item"><div class="legend-dot oversold-dot"></div><span>Oversold (RSI ≤ 20)</span></div>
    <div class="legend-item"><div class="legend-dot overbought-dot"></div><span>Overbought (RSI ≥ 80)</span></div>
</div>""", unsafe_allow_html=True)

# Liste étendue de paires Forex
forex_pairs = [
    'EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD', 
    'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'NZD/JPY', 'CAD/JPY', 'CHF/JPY',
    'EUR/GBP', 'EUR/AUD', 'EUR/CAD', 'EUR/NZD', 'EUR/CHF',
    'GBP/AUD', 'GBP/CAD', 'GBP/CHF', 'GBP/NZD',
    'AUD/CAD', 'AUD/CHF', 'AUD/NZD',
    'CAD/CHF',
    'NZD/CAD', 'NZD/CHF'
]
timeframes_display = ['H1', 'H4', 'Daily', 'Weekly']
timeframes_fetch_keys = ['H1', 'H4', 'D1', 'W1']

# Option pour sélectionner les paires (pourrait être un multiselect plus tard)
# Pour l'instant, on utilise toutes les paires.
filtered_pairs = forex_pairs 

if not filtered_pairs:
    st.warning("Please select at least one Forex pair to analyze.")
else:
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    total_pairs = len(filtered_pairs)

    for i, pair_name in enumerate(filtered_pairs):
        status_text.text(f"Analysing: {pair_name} ({i+1}/{total_pairs})")
        row_data = {'Devises': pair_name}
        for tf_key, tf_display_name in zip(timeframes_fetch_keys, timeframes_display):
            data_ohlc = fetch_forex_data(pair_name, tf_key)
            rsi_value = calculate_rsi(data_ohlc, period=10) # RSI période 10
            row_data[tf_display_name] = rsi_value
        results.append(row_data)
        progress_bar.progress((i + 1) / total_pairs)

    progress_bar.empty(); status_text.empty()

    st.markdown("### 📈 RSI Analysis Results")
    html_table = '<table class="rsi-table">'
    html_table += '<thead><tr><th>Devises</th>'
    for tf_display_name in timeframes_display: html_table += f'<th>{tf_display_name}</th>'
    html_table += '</tr></thead><tbody>'

    for row_idx, row in enumerate(results):
        devises_text = str(row.get("Devises", f"N/A_ROW_{row_idx}")).strip()
        if not devises_text:
            devises_text = f"EMPTY_ROW_{row_idx}"

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
    if results:
        num_timeframes = len(timeframes_display)
        stat_cols = st.columns(num_timeframes)
        for i, tf_display_name in enumerate(timeframes_display):
            rsi_values_for_tf = [row.get(tf_display_name, np.nan) for row in results]
            valid_rsi_values = [val for val in rsi_values_for_tf if pd.notna(val)]
            if valid_rsi_values:
                oversold_count = sum(1 for x in valid_rsi_values if x <= 20)
                overbought_count = sum(1 for x in valid_rsi_values if x >= 80)
                total_signals_count = oversold_count + overbought_count
                with stat_cols[i]: st.metric(
                    label=f"Signals {tf_display_name}",
                    value=str(total_signals_count),
                    # Utiliser des icônes unicode pour les flèches si désiré
                    delta=f"🔴 {oversold_count} S | 🟢 {overbought_count} B", 
                    delta_color="off" # La couleur est gérée par les icônes/texte
                )
            else:
                with stat_cols[i]: st.metric(label=f"Signals {tf_display_name}", value="N/A", delta="No data")
    else:
        st.warning("No results to display statistics.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.success(f"✅ Analysis complete! {len(filtered_pairs)} pairs analyzed.")

with st.expander("ℹ️ User Guide & Configuration", expanded=False): # expanded=False par défaut
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
    - The analysis runs automatically when the page loads.
    - Colored cells indicate potential opportunities:
      - <span style="color:#FF4B4B; font-weight:bold;">🔴 Red</span>: Oversold (RSI ≤ 20) - Potential Buy Signal
      - <span style="color:#3D9970; font-weight:bold;">🟢 Green</span>: Overbought (RSI ≥ 80) - Potential Sell Signal
    - *This tool is for informational purposes only and not financial advice.*
    ## Analyzed Pairs
    The screener analyzes a comprehensive list of major and minor Forex pairs.
    """, unsafe_allow_html=True)

st.markdown("<div class='footer'>*Developed with Streamlit | RSI OHLC4 Period 10*</div>", unsafe_allow_html=True)

# --- END OF FILE app.py ---
