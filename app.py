import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 2. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- 3. FUNZIONI DI CARICAMENTO ---
@st.cache_data(ttl=600)
def load_axon():
    res = supabase.table("axon_knowledge").select("*").execute()
    d = pd.DataFrame(res.data)
    if not d.empty: d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
    return d

@st.cache_data(ttl=600)
def load_odi(query):
    res = supabase.table("odi_database").select("*").ilike("Targets", f"%{query}%").execute()
    return pd.DataFrame(res.data)

@st.cache_data(ttl=600)
def load_pmi(query):
    # Interroga il database dei Pathways (SMI)
    res = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{query}%").execute()
    return pd.DataFrame(res.data)

@st.cache_data(ttl=600)
def load_gci(query):
    res = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
    return pd.DataFrame(res.data)

df = load_axon()

# --- 4. SIDEBAR ---
st.sidebar.title("Omikron Control Center")
search_query = st.sidebar.text_input("Cerca Target (es. KRAS, BRCA1)", "").strip().upper()

# --- 5. LOGICA DI FILTRO ---
gci_df, target_drugs, pmi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query and not df.empty:
    target_drugs = load_odi(search_query)
    pmi_df = load_pmi(search_query)
    # ... filtro neighbors ... (omesso per brevità, resta lo stesso)
    filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df

# --- 6. OPERA DIRECTOR ---
st.title("🛡️ MAESTRO Suite")

if search_query and not df.empty:
    target_info = df[df['target_id'] == search_query]
    if not target_info.empty:
        row = target_info.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # RIGA 1: MECCANICA (OMI, SMI, ODI)
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Biomarker)", "DETECTED")
        
        # SMI (Pathway) ora è DINAMICO
        smi_status = f"{len(pmi_df)} Pathways" if not pmi_df.empty else "STABLE"
        c2.metric("SMI (Pathway)", smi_status)
        
        c3.metric("ODI (Drug)", "TARGETABLE" if not target_drugs.empty else "NO DRUG")
        c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}")
        c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")
        st.divider()

# --- 7. ANALISI PATHWAY (SMI) ---
if not pmi_df.empty:
    st.header("🕸️ Signaling & Pathway Analysis (SMI)")
    for _, p in pmi_df.iterrows():
        with st.expander(f"Pathway: {p['Canonical_Name']} ({p['Category']})"):
            col_a, col_b = st.columns([2, 1])
            col_a.write(f"**Descrizione:** {p['Description_L0']}")
            col_a.write(f"**Readouts:** {p['Key_Readouts']}")
            col_b.info(f"**Priority:** {p['Evidence_Priority']}\n\n**Confidence:** {p['Confidence_Default']}")

# --- 8. RESTO DELLA DASHBOARD (Ragnatela, Portali ODI/GCI) ---
# ... (il codice esistente per Grafici, Network Map e Tabelle ODI/GCI)
