import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Omikron Orchestra Suite", layout="wide")

# --- 2. PASSWORD ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("Inserisci la chiave d'accesso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.error("😕 Accesso negato")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    res = supabase.table("axon_knowledge").select("*").execute()
    df = pd.DataFrame(res.data)
    df['ces_score'] = df['initial_score'] * (1 - df['toxicity_index'])
    return df

df = load_axon()

# --- 4. INTERFACCIA ---
st.title("🛡️ Omikron Orchestra Suite")

st.sidebar.header("Filtri AXON")
min_sig = st.sidebar.slider("Soglia Segnale", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità", 0.0, 1.0, 0.8)
search_query = st.sidebar.text_input("🔍 Cerca Biomarker (es. HER2)", "").strip()

if search_query:
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]

# --- 5. VISUALIZZAZIONE AXON ---
c1, c2 = st.columns([2, 1])
with c1:
    st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with c2:
    st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 6. INTEGRAZIONE CLINICA (GCI) ---
st.markdown("---")
st.subheader("🧪 Clinical Evidence Portal (GCI Database)")

if not search_query:
    st.info("💡 Digita un biomarker (es. HER2) nella barra laterale per caricare i trial clinici dal database GCI.")
else:
    try:
        # Cerchiamo i dati nella tabella clinical_trials
        # Usiamo una ricerca più ampia (ilike) per beccare anche HER2-Low o variazioni
        res_gci = supabase.table("clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)

        if not gci_df.empty:
            st.success(f"Trovate {len(gci_df)} evidenze cliniche per '{search_query}'")
            
            # Metriche Rapide
            m1, m2, m3 = st.columns(3)
            m1.metric("Studi Totali", len(gci_df))
            m2.metric("Fase Prevalente", gci_df['Phase'].mode()[0] if 'Phase' in gci_df.columns else "N/A")
            if 'Practice_Changing' in gci_df.columns:
                pc = len(gci_df[gci_df['Practice_Changing'].astype(str).str.contains('Yes', case=False, na=False)])
                m2.metric("Practice Changing", pc)

            # Tabella Dettagli
            cols = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Key_Results_PFS', 'Main_Toxicities']
            st.dataframe(gci_df[[c for c in cols if c in gci_df.columns]], use_container_width=True)
        else:
            st.warning(f"Nessun dato clinico trovato per '{search_query}'.")
    except Exception as e:
        st.error(f"Errore di connessione al Database GCI: {e}")
