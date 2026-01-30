import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- CONNESSIONE ---
# Usa i valori di default se i secrets mancano (per test locale)
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_data():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            # Pulizia e normalizzazione
            df['target_id'] = df['target_id'].astype(str).str.upper().str.strip()
            df['source_id'] = df['source_id'].astype(str).str.upper().str.strip()
            df['initial_score'] = pd.to_numeric(df['initial_score'], errors='coerce').fillna(0.8)
            df['toxicity_index'] = pd.to_numeric(df['toxicity_index'], errors='coerce').fillna(0.1)
            df['ces_score'] = df['initial_score'] * (1 - df['toxicity_index'])
        return df
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return pd.DataFrame()

# --- CARICAMENTO ---
df_axon = load_data()

# --- SIDEBAR ---
st.sidebar.title("🛡️ MAESTRO v2.6")
target_search = st.sidebar.text_input("Hub Target Search", placeholder="es. METTL3").upper()

vtg_min = st.sidebar.slider("VTG Threshold", 0.0, 3.0, 0.5)
tmi_max = st.sidebar.slider("TMI Max Limit", 0.0, 1.0, 0.9)

# --- MAIN UI ---
st.title("🛡️ Omikron Orchestra Suite")

if df_axon.empty:
    st.warning("⚠️ Database vuoto o non connesso. Verifica Supabase.")
else:
    if target_search:
        # Filtro Hub
        hub_data = df_axon[df_axon['target_id'] == target_search]
        
        if hub_data.empty:
            st.info(f"Nessun dato trovato per {target_search}")
        else:
            res = hub_data.iloc[0]
            
            # Dashboard Metriche
            col1, col2, col3 = st.columns(3)
            col1.metric("VTG Score", f"{res['initial_score']:.2f}")
            col2.metric("TMI Index", f"{res['toxicity_index']:.2f}")
            col3.metric("CES Final", f"{res['ces_score']:.2f}")
            
            st.markdown(f"### 🧬 Biological Context")
            st.write(res.get('description_l0', 'No description available.'))
            
            if res.get('pdb_id'):
                st.info(f"💎 PDB Identifier: {res['pdb_id']}")

            # --- EXPORT ---
            st.divider()
            csv_buffer = io.StringIO()
            hub_data.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Download Intelligence Dossier",
                data=csv_buffer.getvalue(),
                file_name=f"MAESTRO_{target_search}.csv",
                mime="text/csv"
            )
    else:
        st.write("Inserisci un Target nella sidebar per iniziare l'analisi.")
