import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- CONFIGURAZIONE DASHBOARD ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")
st.title("🛡️ MAESTRO: Omikron Intelligence Suite")

# --- CONNESSIONE DATABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- RECUPERO DATI ---
@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("axon_knowledge").select("*").execute()
    df = pd.DataFrame(response.data)
    # Calcolo Clinical Efficiency Score
    df['ces_score'] = df['initial_score'] * (1 - df['toxicity_index'])
    return df

df = load_data()

# --- SIDEBAR DI CONTROLLO ---
st.sidebar.header("Parametri VTG Gate")
min_signal = st.sidebar.slider("Soglia Minima Segnale", 0.0, 3.0, 0.8)
max_tox = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

# Filtro dinamico
filtered_df = df[(df['initial_score'] >= min_signal) & (df['toxicity_index'] <= max_tox)]

# --- LAYOUT PRINCIPALE ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Analisi Efficacia vs Tossicità")
    fig = px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index",
                 color_continuous_scale="RdYlGn_r", template="plotly_dark",
                 labels={'initial_score': 'Potenza d\'Urto', 'toxicity_index': 'Rischio TMI'})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🥇 Top Target (Efficiency Score)")
    top_5 = filtered_df.sort_values('ces_score', ascending=False).head(5)
    st.dataframe(top_5[['target_id', 'initial_score', 'toxicity_index', 'ces_score']], use_container_width=True)

# --- NETWORK GRAPH (SOTTO) ---
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")
# Qui il codice per la ragnatela che abbiamo testato su Colab
# ... (lo caricheremo nel file completo su GitHub)