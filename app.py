import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')

# Configuration de la page Streamlit
st.set_page_config(
    page_title="RSI Forex Screener Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé amélioré
st.markdown("""
<style>
    .main > div { padding-top: 2rem; }
    .screener-header { 
        font-size: 28px; 
        font-weight: bold; 
        color: #2c3e50; 
        margin-bottom: 15px; 
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .update-info { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 20px; 
        border-radius: 10px; 
        margin-bottom: 20px; 
        font-size: 14px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .legend-container { 
        display: flex; 
        justify-content: center; 
        gap: 40px; 
        margin: 20px 0; 
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .legend-item { 
        display: flex; 
        align-items: center; 
        gap: 8px; 
        font-size: 14px; 
        font-weight: 500;
    }
    .legend-dot { 
        width: 14px; 
        height: 14px; 
        border-radius: 50%; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .oversold-dot { background: linear-gradient(135deg, #ff416c, #ff4757); }
    .overbought-dot { background: linear-gradient(135deg, #00d2ff, #3742fa); }
    .neutral-dot { background: linear-gradient(135deg, #ffa726, #ffcc02); }
    
    .rsi-table { 
        width: 100%; 
        border-collapse: collapse; 
        margin: 20px 0; 
        font-size: 13px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-radius: 10px;
        overflow: hidden;
    }
    .rsi-table th { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important; 
        padding: 15px 10px; 
        text-align: center; 
        font-weight: bold; 
        border: none;
        font-size: 14px;
    }
    .rsi-table td { 
        padding: 12px 10px; 
        text-align: center; 
        border: 1px solid #e9ecef;
        transition: all 0.3s ease;
    }
    .rsi-table tr:hover td {
        background-color: #f8f9fa;
        transform: scale(1.01);
    }
    
    .devises-cell { 
        font-weight: bold !important;
        color: #2c3e50 !important;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef) !important;
        font-size: 14px !important;
        border-left: 4px solid #667eea !important;
    }
    
    .oversold-cell { 
        background: linear-gradient(135deg, #ff416c, #ff4757) !important; 
        color: white !important; 
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    .overbought-cell { 
        background: linear-gradient(135deg, #00d2ff, #3742fa) !important; 
        color: white !important; 
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    .neutral-cell { 
        color: #495057 !important;
        background-color: #ffffff !important;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 255, 255, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }
    }
    
    .stats-container { 
        margin-top: 30px;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    .alert-success {
        background: linear-gradient(135deg, #56ab2f, #a8e6cf);
        color: white;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .data-source-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
        margin-left: 10px;
    }
    .yahoo-badge { background-color: #6f42c1; color: white; }
    .alpha-badge { background-color: #fd7e14; color: white; }
</style>
""", unsafe_allow_html=True)

# Configuration dans la sidebar
st.sidebar.title("🛠️ Configuration")

# Section API Alpha Vantage
st.sidebar.subheader("🔑 Alpha Vantage API")
alpha_vantage_key = st.sidebar.text_input(
    "Clé API Alpha Vantage",
    type="password",
    help="Obtenez votre clé gratuite sur https://www.alphavantage.co/support/#api-key"
)

use_alpha_vantage = st.sidebar.checkbox(
    "Utiliser Alpha Vantage",
    value=False,
    help="Cochez pour utiliser Alpha Vantage comme source de données principale"
)

# Configuration RSI
st.sidebar.subheader("📊 Configuration RSI")
rsi_period = st.sidebar.slider("Période RSI", min_value=5, max_value=50, value=14, step=1)
oversold_threshold = st.sidebar.slider("Seuil Survente", min_value=10, max_value=35, value=30, step=5)
overbought_threshold = st.sidebar.slider("Seuil Surachat", min_value=65, max_value=90, value=70, step=5)

# Sélection des paires
st.sidebar.subheader("💱 Sélection des Paires")
all_forex_pairs = [
    'EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD',
    'EUR/JPY', 'GBP/JPY', 'EUR/GBP', 'AUD/JPY', 'CHF/JPY', 'GBP/CHF',
    'EUR/AUD', 'EUR/CAD', 'GBP/AUD', 'USD/SEK', 'USD/NOK', 'EUR/SEK'
]

selected_pairs = st.sidebar.multiselect(
    "Choisir les paires à analyser",
    all_forex_pairs,
    default=all_forex_pairs[:10]
)

# Fonction pour récupérer les données depuis Alpha Vantage
def fetch_alpha_vantage_data(pair, api_key, timeframe='daily'):
    """Récupère les données forex depuis Alpha Vantage"""
    try:
        # Conversion du format de paire
        from_symbol, to_symbol = pair.split('/')
        
        # Mapping des timeframes
        function_map = {
            'daily': 'FX_DAILY',
            'weekly': 'FX_WEEKLY',
            'monthly': 'FX_MONTHLY'
        }
        
        url = f"https://www.alphavantage.co/query"
        params = {
            'function': function_map.get(timeframe, 'FX_DAILY'),
            'from_symbol': from_symbol,
            'to_symbol': to_symbol,
            'apikey': api_key,
            'outputsize': 'compact'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Vérification des erreurs
        if 'Error Message' in data:
            st.error(f"Erreur Alpha Vantage pour {pair}: {data['Error Message']}")
            return None
            
        if 'Note' in data:
            st.warning(f"Limite de taux Alpha Vantage atteinte pour {pair}")
            return None
        
        # Extraction des données
        time_series_key = None
        for key in data.keys():
            if 'Time Series' in key:
                time_series_key = key
                break
        
        if not time_series_key:
            return None
            
        time_series = data[time_series_key]
        
        # Conversion en DataFrame
        df_data = []
        for date, values in time_series.items():
            df_data.append({
                'Date': pd.to_datetime(date),
                'Open': float(values['1. open']),
                'High': float(values['2. high']),
                'Low': float(values['3. low']),
                'Close': float(values['4. close'])
            })
        
        df = pd.DataFrame(df_data)
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        return df
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Alpha Vantage pour {pair}: {str(e)}")
        return None

def calculate_rsi_improved(prices, period=14):
    """Calcul RSI amélioré avec gestion d'erreurs renforcée"""
    try:
        if prices is None or len(prices) < period + 1:
            return np.nan
            
        # Utilisation du prix de clôture par défaut
        if 'Close' in prices.columns:
            price_series = prices['Close']
        else:
            # Fallback sur OHLC4 si disponible
            price_series = (prices['Open'] + prices['High'] + prices['Low'] + prices['Close']) / 4
        
        delta = price_series.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        if len(gains.dropna()) < period or len(losses.dropna()) < period:
            return np.nan
            
        # Calcul de la moyenne mobile exponentielle
        avg_gains = gains.ewm(span=period, adjust=False, min_periods=period).mean()
        avg_losses = losses.ewm(span=period, adjust=False, min_periods=period).mean()
        
        if avg_losses.empty or avg_gains.empty:
            return np.nan
            
        last_avg_loss = avg_losses.iloc[-1]
        last_avg_gain = avg_gains.iloc[-1]
        
        if pd.isna(last_avg_loss) or pd.isna(last_avg_gain):
            return np.nan
            
        if last_avg_loss == 0:
            return 100 if last_avg_gain > 0 else 50
            
        rs = last_avg_gain / last_avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi if pd.notna(rsi) else np.nan
        
    except Exception as e:
        return np.nan

def get_yahoo_symbol(pair):
    """Conversion des paires pour Yahoo Finance"""
    return pair.replace('/', '') + '=X'

def fetch_forex_data(symbol, timeframe_key, use_alpha=False, api_key=None):
    """Récupère les données forex depuis Yahoo Finance ou Alpha Vantage"""
    try:
        if use_alpha and api_key:
            # Utilisation d'Alpha Vantage
            timeframe_map = {
                'H1': 'daily',  # Alpha Vantage n'a pas de données horaires gratuites
                'H4': 'daily',
                'D1': 'daily',
                'W1': 'weekly'
            }
            alpha_timeframe = timeframe_map.get(timeframe_key, 'daily')
            return fetch_alpha_vantage_data(symbol, api_key, alpha_timeframe)
        else:
            # Utilisation de Yahoo Finance (méthode existante)
            yahoo_symbol = get_yahoo_symbol(symbol)
            params = {
                'H1': {'period': '5d', 'interval': '1h'},
                'H4': {'period': '1mo', 'interval': '4h'},
                'D1': {'period': '3mo', 'interval': '1d'},
                'W1': {'period': '2y', 'interval': '1wk'}
            }
            
            if timeframe_key not in params:
                return None
                
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(
                period=params[timeframe_key]['period'],
                interval=params[timeframe_key]['interval'],
                auto_adjust=True,
                prepost=False
            )
            
            if data is None or data.empty or len(data) < 15:
                return None
                
            return data
            
    except Exception as e:
        return None

def format_rsi(value):
    """Formatage de la valeur RSI"""
    return "N/A" if pd.isna(value) else f"{value:.2f}"

def get_rsi_class(value, oversold_thresh, overbought_thresh):
    """Détermine la classe CSS en fonction de la valeur RSI"""
    if pd.isna(value):
        return "neutral-cell"
    elif value <= oversold_thresh:
        return "oversold-cell"
    elif value >= overbought_thresh:
        return "overbought-cell"
    return "neutral-cell"

def get_rsi_signal(value, oversold_thresh, overbought_thresh):
    """Détermine le signal de trading"""
    if pd.isna(value):
        return "N/A"
    elif value <= oversold_thresh:
        return "🔴 ACHAT"
    elif value >= overbought_thresh:
        return "🟢 VENTE"
    else:
        return "⚪ NEUTRE"

# Interface principale
st.markdown('<h1 class="screener-header">📊 RSI Forex Screener Pro</h1>', unsafe_allow_html=True)

# Affichage des informations de configuration
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
data_source = "Alpha Vantage" if (use_alpha_vantage and alpha_vantage_key) else "Yahoo Finance"
data_source_badge = "alpha-badge" if (use_alpha_vantage and alpha_vantage_key) else "yahoo-badge"

st.markdown(f"""
<div class="update-info">
    🔄 Analyse mise à jour - {current_time}
    <span class="data-source-badge {data_source_badge}">Source: {data_source}</span>
    <br>
    📊 Période RSI: {rsi_period} | 🔴 Survente: ≤{oversold_threshold} | 🟢 Surachat: ≥{overbought_threshold}
</div>
""", unsafe_allow_html=True)

# Légende améliorée
st.markdown(f"""
<div class="legend-container">
    <div class="legend-item">
        <div class="legend-dot oversold-dot"></div>
        <span>Survente (RSI ≤ {oversold_threshold}) - Signal d'ACHAT</span>
    </div>
    <div class="legend-item">
        <div class="legend-dot overbought-dot"></div>
        <span>Surachat (RSI ≥ {overbought_threshold}) - Signal de VENTE</span>
    </div>
    <div class="legend-item">
        <div class="legend-dot neutral-dot"></div>
        <span>Neutre - Pas de signal</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Vérification des paramètres
if not selected_pairs:
    st.warning("⚠️ Veuillez sélectionner au moins une paire de devises dans la barre latérale.")
    st.stop()

if use_alpha_vantage and not alpha_vantage_key:
    st.warning("⚠️ Veuillez entrer votre clé API Alpha Vantage dans la barre latérale.")
    st.stop()

# Analyse des données
timeframes_display = ['H1', 'H4', 'Daily', 'Weekly']
timeframes_fetch_keys = ['H1', 'H4', 'D1', 'W1']

# Barre de progression
progress_bar = st.progress(0)
status_text = st.empty()
results = []
total_pairs = len(selected_pairs)

for i, pair_name in enumerate(selected_pairs):
    status_text.text(f"🔍 Analyse en cours: {pair_name} ({i+1}/{total_pairs})")
    
    row_data = {'Devises': pair_name}
    
    for tf_key, tf_display_name in zip(timeframes_fetch_keys, timeframes_display):
        # Récupération des données
        data_ohlc = fetch_forex_data(
            pair_name, 
            tf_key, 
            use_alpha=use_alpha_vantage, 
            api_key=alpha_vantage_key
        )
        
        # Calcul du RSI
        rsi_value = calculate_rsi_improved(data_ohlc, period=rsi_period)
        row_data[tf_display_name] = rsi_value
        
        # Ajout du signal de trading
        signal = get_rsi_signal(rsi_value, oversold_threshold, overbought_threshold)
        row_data[f'{tf_display_name}_Signal'] = signal
    
    results.append(row_data)
    progress_bar.progress((i + 1) / total_pairs)
    
    # Délai pour éviter les limites de taux API
    if use_alpha_vantage and alpha_vantage_key:
        time.sleep(0.2)  # 200ms de délai pour Alpha Vantage

progress_bar.empty()
status_text.empty()

# Affichage des résultats
st.markdown("### 📈 Résultats de l'Analyse RSI")

# Génération du tableau HTML
html_table = '<table class="rsi-table">'
html_table += '<thead><tr><th>Devises</th>'
for tf_display_name in timeframes_display:
    html_table += f'<th>{tf_display_name}<br>RSI</th>'
    html_table += f'<th>{tf_display_name}<br>Signal</th>'
html_table += '</tr></thead><tbody>'

for row_idx, row in enumerate(results):
    devises_text = str(row.get("Devises", f"DEVISE_MANQUANTE_LIGNE_{row_idx}")).strip()
    if not devises_text:
        devises_text = f"DEVISE_VIDE_LIGNE_{row_idx}"
    
    html_table += f'<tr><td class="devises-cell">{devises_text}</td>'
    
    for tf_display_name in timeframes_display:
        # Colonne RSI
        rsi_val = row.get(tf_display_name, np.nan)
        css_class = get_rsi_class(rsi_val, oversold_threshold, overbought_threshold)
        formatted_val = format_rsi(rsi_val)
        html_table += f'<td class="{css_class}">{formatted_val}</td>'
        
        # Colonne Signal
        signal = row.get(f'{tf_display_name}_Signal', 'N/A')
        signal_class = "oversold-cell" if "ACHAT" in signal else "overbought-cell" if "VENTE" in signal else "neutral-cell"
        html_table += f'<td class="{signal_class}" style="font-size: 11px; font-weight: bold;">{signal}</td>'
    
    html_table += '</tr>'

html_table += '</tbody></table>'
st.markdown(html_table, unsafe_allow_html=True)

# Statistiques améliorées
st.markdown('<div class="stats-container">', unsafe_allow_html=True)
st.markdown("### 📊 Statistiques des Signaux")

num_timeframes = len(timeframes_display)
stat_cols = st.columns(num_timeframes)

for i, tf_display_name in enumerate(timeframes_display):
    rsi_values_for_tf = [row.get(tf_display_name, np.nan) for row in results]
    valid_rsi_values = [val for val in rsi_values_for_tf if pd.notna(val)]
    
    if valid_rsi_values:
        oversold_count = sum(1 for x in valid_rsi_values if x <= oversold_threshold)
        overbought_count = sum(1 for x in valid_rsi_values if x >= overbought_threshold)
        total_signals_count = oversold_count + overbought_count
        avg_rsi = np.mean(valid_rsi_values)
        
        with stat_cols[i]:
            st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label=f"Signaux {tf_display_name}",
                value=str(total_signals_count),
                delta=f"🔴 {oversold_count} | 🟢 {overbought_count}",
                delta_color="off"
            )
            st.metric(
                label="RSI Moyen",
                value=f"{avg_rsi:.1f}",
                delta=None
            )
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        with stat_cols[i]:
            st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label=f"Signaux {tf_display_name}",
                value="N/A",
                delta="Aucune donnée"
            )
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Résumé des opportunités
opportunities = []
for row in results:
    pair = row['Devises']
    for tf in timeframes_display:
        rsi_val = row.get(tf, np.nan)
        if pd.notna(rsi_val):
            if rsi_val <= oversold_threshold:
                opportunities.append(f"🔴 **{pair}** ({tf}): RSI {rsi_val:.2f} - Signal d'ACHAT")
            elif rsi_val >= overbought_threshold:
                opportunities.append(f"🟢 **{pair}** ({tf}): RSI {rsi_val:.2f} - Signal de VENTE")

if opportunities:
    st.markdown("### 🎯 Opportunités de Trading Détectées")
    for opp in opportunities[:10]:  # Limiter à 10 pour éviter l'encombrement
        st.markdown(f"<div class='alert-success'>{opp}</div>", unsafe_allow_html=True)
    
    if len(opportunities) > 10:
        st.info(f"+ {len(opportunities) - 10} autres opportunités détectées")

st.markdown(f"<div class='alert-success'>✅ Analyse terminée! {len(selected_pairs)} paires analysées avec succès.</div>", unsafe_allow_html=True)

# Guide utilisateur amélioré
with st.expander("ℹ️ Guide d'Utilisation Détaillé"):
    st.markdown(f"""
    ## 🔧 Configuration RSI
    - **Période**: {rsi_period} (personnalisable dans la barre latérale)
    - **Source de prix**: Prix de clôture (ou OHLC4 si disponible)
    - **Seuils actuels**: 
      - Survente: ≤ {oversold_threshold}
      - Surachat: ≥ {overbought_threshold}
    
    ## 📊 Timeframes Disponibles
    - **H1**: Données horaires (5 derniers jours)
    - **H4**: Données 4 heures (1 dernier mois)
    - **Daily (D1)**: Données quotidiennes (3 derniers mois)
    - **Weekly (W1)**: Données hebdomadaires (2 dernières années)
    
    ## 🎯 Interprétation des Signaux
    - **🔴 Signal d'ACHAT**: RSI en zone de survente (≤ {oversold_threshold})
      - Indique une possible opportunité d'achat
      - La devise pourrait être sous-évaluée
    - **🟢 Signal de VENTE**: RSI en zone de surachat (≥ {overbought_threshold})
      - Indique une possible opportunité de vente
      - La devise pourrait être surévaluée
    - **⚪ NEUTRE**: RSI entre {oversold_threshold + 1} et {overbought_threshold - 1}
      - Pas de signal clair, attendre confirmation
    
    ## 🔑 Sources de Données
    - **Yahoo Finance** (Gratuit): Données en temps réel, pas de clé API requise
    - **Alpha Vantage** (Gratuit avec limite): Données professionnelles, clé API requise
      - Obtenez votre clé gratuite: https://www.alphavantage.co/support/#api-key
      - Limite: 5 appels par minute, 500 par jour
    
    ## ⚠️ Avertissements
    - Le RSI est un indicateur technique, pas une garantie de performance
    - Utilisez toujours une gestion du risque appropriée
    - Confirmez les signaux avec d'autres indicateurs
    - Les performances passées ne garantissent pas les résultats futurs
    
    ## 💡 Conseils d'Utilisation
    - Analysez plusieurs timeframes pour confirmation
    - Surveillez les divergences entre les timeframes
    - Attendez la confirmation avant de prendre position
    - Considérez le contexte macroéconomique
    """)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; font-size: 12px; margin-top: 20px;'>
    <p>🚀 <strong>RSI Forex Screener Pro</strong> | Développé avec Streamlit</p>
    <p>📊 Source: {data_source} | ⏰ Dernière mise à jour: {current_time}</p>
    <p>⚡ Période RSI: {rsi_period} | 🎯 Seuils: {oversold_threshold}/{overbought_threshold}</p>
</div>
""", unsafe_allow_html=True)
