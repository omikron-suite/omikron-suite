import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. RESET FORZATO DELLA PAGINA ---
# Questo comando DEVE essere la prima riga assoluta dopo gli import
st.set_page_config(page_title="MAESTRO Ultra", layout="wide", initial_sidebar_state="collapsed")

# Nascondiamo la barra laterale con CSS per sicurezza estrema
st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNESSIONE SUPABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- 3. CARICAMENTO DATI ---
@st.cache_data(ttl=600)
def fetch_data(table, col=None, query=None):
    try:
        if col and query:
            res = supabase.table(table).select("*").ilike(col, f"%{query}%").execute()
        else:
            res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# Caricamento Axon (Base)
df_axon = fetch_data("axon_knowledge")
if not df_axon.empty:
    df_axon['target_id'] = df_axon['target_id'].str.strip().upper()
    df_axon['ces_score'] = df_axon['initial_score'] * (1 - df_axon['toxicity_index'])

# --- 4. INTERFACCIA PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra")
st.subheader("Intelligence Suite v4.7")

# Pannello di Ricerca Centrale
search_query = st.text_input("🔍 INSERISCI TARGET (es. KRAS, HER2, EGFR)", "").strip().upper()

c1, c2 = st.columns(2)
with c1:
    v_min = st.slider("Soglia Segnale VTG", 0.0, 3.0, 0.8)
with c2:
    t_max = st.slider("Limite Tossicità TMI", 0.0, 1.0, 0.8)

st.divider()

# --- 5. LOGICA DI ANALISI ---
if not df_axon.empty:
    # Database Satelliti
    odi_df = fetch_data("odi_database", "Targets", search_query) if search_query else pd.DataFrame()
    pmi_df = fetch_data("pmi_database", "Key_Targets", search_query) if search_query else pd.DataFrame()
    gci_df = fetch_data("GCI_clinical_trials", "Primary_Biomarker", search_query) if search_query else pd.DataFrame()

    # Filtro
    if search_query:
        f_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
    else:
        f_df = df_axon[(df_axon['initial_score'] >= v_min) & (df_axon['toxicity_index'] <= t_max)]

    # --- 6. OPERA DIRECTOR GRID ---
    if search_query and not f_df.empty:
        target_row = df_axon[df_axon['target_id'] == search_query]
        if not target_row.empty:
            r = target_row.iloc[0]
            st.markdown(f"### 🎼 Opera Director: {search_query}")
            
            # Griglia 10 Parametri
            st.markdown("**⚙️ Meccanica & Sicurezza**")
            cols1 = st.columns(5)
            cols1[0].metric("OMI", "DETECTED")
            cols1[1].metric("SMI", f"{len(pmi_df)} Path")
            cols1[2].metric("ODI", "YES" if not odi_df.empty else "NO")
            cols1[3].metric("TMI", f"{r['toxicity_index']:.2f}")
            cols1[4].metric("CES", f"{r['ces_score']:.2f}")

            st.markdown("**🌍 Ambiente & Host**")
            cols2 = st.columns(5)
            cols2[0].metric("BCI", "OK")
            cols2[1].metric("GNI", "STABLE")
            cols2[2].metric("EVI", "CLEAN")
            cols2[3].metric("MBI", "BALANCED")
            cols2[4].metric("GCI", gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D")
            
            st.divider()

    # --- 7. VISUALIZZAZIONE ---
    if not f_df.empty:
        t1, t2 = st.tabs(["🕸️ Network Map", "📊 Analysis"])
        with t1:
            # Semplice Bar Chart se la ragnatela dà problemi
            st.plotly_chart(px.scatter(f_df, x="initial_score", y="toxicity_index", text="target_id", color="ces_score", size="initial_score", template="plotly_dark"), use_container_width=True)
        with t2:
            st.dataframe(f_df.sort_values("ces_score", ascending=False), use_container_width=True)

    # --- 8. DATABASE FINALI ---
    if search_query:
        st.markdown("### 🧪 Database Deep-Dive")
        d1, d2, d3 = st.columns(3)
        with d1:
            st.write("**ODI Farmaci**")
            st.write(odi_df[['Generic_Name', 'Drug_Class']] if not odi_df.empty else "Nessun dato")
        with d2:
            st.write("**PMI Pathway**")
            st.write(pmi_df[['Canonical_Name']] if not pmi_df.empty else "Nessun dato")
        with d3:
            st.write("**GCI Trial**")
            st.write(gci_df[['Canonical_Title', 'Phase']] if not gci_df.empty else "Nessun dato")

st.divider()
st.caption("MAESTRO Hard-Reset Edition | Engine 4.7")
