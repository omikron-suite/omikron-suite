import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.graph_objects as go
import io

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Platinum v2.6.5", layout="wide")

# Typography Styling
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #00d4ff !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONE (Testata e Funzionante) ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_full_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            # Pulizia e standardizzazione
            df['target_id'] = df['target_id'].astype(str).str.upper().str.strip()
            df['initial_score'] = pd.to_numeric(df['initial_score'], errors='coerce').fillna(0.8)
            df['toxicity_index'] = pd.to_numeric(df['toxicity_index'], errors='coerce').fillna(0.1)
            df['ces_score'] = df['initial_score'] * (1 - df['toxicity_index'])
        return df
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return pd.DataFrame()

# Caricamento Dati
df_axon = load_full_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")
st.sidebar.success(f"📡 Database Online: {len(df_axon)} record")

search_query = st.sidebar.text_input("🔍 Search Gene/Target", placeholder="es. METTL3").strip().upper()

st.sidebar.divider()
st.sidebar.caption("v2.6.5 | Platinum Edition")

# --- 4. MAIN INTERFACE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if df_axon.empty:
    st.error("Il database è connesso ma non restituisce righe. Controlla i permessi RLS su Supabase.")
else:
    if search_query:
        # Filtro per il Target cercato
        result = df_axon[df_axon['target_id'] == search_query]
        
        if result.empty:
            st.info(f"Nessun match trovato per: **{search_query}**. Prova con METTL3, KRAS o EGFR.")
            st.write("Target disponibili (anteprima):", ", ".join(df_axon['target_id'].unique()[:15]))
        else:
            data = result.iloc[0]
            
            # Griglia Metriche
            m1, m2, m3 = st.columns(3)
            m1.metric("VTG Score", f"{data['initial_score']:.2f}")
            m2.metric("TMI Toxicity", f"{data['toxicity_index']:.2f}")
            m3.metric("CES Final", f"{data['ces_score']:.2f}")
            
            st.divider()
            
            # Informazioni Biologiche
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🧬 Biological Context")
                st.write(data.get('description_l0', "Analysis in progress for this cluster."))
                
                if data.get('pdb_id'):
                    st.info(f"**Protein Data Bank ID:** {data['pdb_id']}")
            
            with c2:
                st.subheader("📊 Hierarchy")
                st.code(f"ID: {data['id']}\nSource: {data['source_id']}\nAction: {data['action_verb']}")

            # --- EXPORT ---
            st.divider()
            st.subheader("📥 Intelligence Export")
            csv_buffer = io.StringIO()
            result.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download Research Dossier (CSV)",
                data=csv_buffer.getvalue(),
                file_name=f"MAESTRO_{search_query}_Report.csv",
                mime="text/csv"
            )
    else:
        st.info("👋 Benvenuto. Inserisci un Target nella sidebar per avviare l'analisi molecolare.")
        # Mostra una piccola tabella di anteprima
        st.write("### Ultimi aggiornamenti AXON")
        st.dataframe(df_axon[['target_id', 'initial_score', 'ces_score']].head(10))
