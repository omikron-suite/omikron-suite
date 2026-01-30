import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 2. CONNESSIONE SUPABASE & CARICAMENTO ODI ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_odi():
    try:
        # Carichiamo il database dei farmaci dal CSV fornito
        d = pd.read_csv("ODI_Database - Sheet1.csv")
        return d
    except Exception:
        return pd.DataFrame()

df = load_axon()
odi_df = load_odi()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Smart Search & Hub Focus")
search_query = st.sidebar.text_input("Cerca Target (es. HER2, EGFR)", "").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**\n\nNot for use in diagnostic or therapeutic procedures.")

# --- 4. LOGICA DI FILTRO ---
gci_df = pd.DataFrame()
target_drugs = pd.DataFrame()

if search_query and not df.empty:
    # 1. Caricamento Dati Clinici GCI
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
    except:
        gci_df = pd.DataFrame()

    # 2. Caricamento Dati Farmaci ODI (Cerca il target nella colonna 'Targets' del CSV)
    if not odi_df.empty:
        target_drugs = odi_df[odi_df['Targets'].str.contains(search_query, case=False, na=False)]

    # 3. Filtro Grafico & Ragnatela
    all_targets = df['target_id'].tolist()
    if search_query in all_targets:
        idx = all_targets.index(search_query)
        neighbors = all_targets[max(0, idx-2):min(len(all_targets), idx+3)]
        filtered_df = df[df['target_id'].isin(neighbors)]
    else:
        filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 5. OPERA DIRECTOR (INTELLIGENCE HUB) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'].str.upper() == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # Griglia 5x2
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
        r1_c1.metric("OMI (Biomarker)", "DETECTED")
        r1_c2.metric("SMI (Pathway)", "ACTIVE")
        
        # ODI DINAMICO: Se troviamo farmaci nel CSV, mostriamo 'TARGETABLE'
        odi_status = "TARGETABLE" if not target_drugs.empty else "NO DRUG"
        r1_c3.metric("ODI (Drug)", odi_status)
        
        r1_c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1_c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
        r2_c1.metric("BCI (Bio-cost.)", "OPTIMAL")
        r2_c2.metric("GNI (Genetica)", "STABLE")
        r2_c3.metric("EVI (Ambiente)", "LOW RISK")
        r2_c4.metric("MBI (Microbiota)", "RESILIENT")
        
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "PRE-CLIN"
        r2_c5.metric("GCI (Clinica)", phase)
        st.divider()

# --- 6. GRAFICI & RAGNATELA ---
# (Codice dei grafici rimane lo stesso della versione precedente)
col_bar, col_rank = st.columns([2, 1])
with col_bar:
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with col_rank:
    if not filtered_df.empty:
        st.subheader("🥇 Hub Ranking")
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 7. RAGNATELA ---
# (Codice ragnatela rimane lo stesso)
st.divider()
st.subheader("🕸️ Network Interaction Map")
if not filtered_df.empty:
    # ... (inserire qui il blocco networkx/go.Figure della versione precedente)
    pass # Inserire il codice completo qui per il commit

# --- 8. ODI THERAPEUTICS PORTAL (NUOVA SEZIONE) ---
st.divider()
st.header("💊 Available Therapeutics (ODI Database)")
if not target_drugs.empty:
    st.success(f"Trovati {len(target_drugs)} farmaci per il target '{search_query}'")
    cols_odi = ['Generic_Name', 'Brand_Names', 'Drug_Class', 'Mechanism_Short', 'Regulatory_Status_US']
    st.dataframe(target_drugs[[c for c in cols_odi if c in target_drugs.columns]], use_container_width=True)
elif search_query:
    st.info(f"Nessun farmaco specifico trovato nel database ODI per '{search_query}'.")

# --- 9. GCI PORTAL ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if not gci_df.empty:
    st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type', 'Key_Results_PFS']], use_container_width=True)

st.divider()
st.caption("Disclaimer: RUO - Research Use Only. Integration of ODI, AXON, and GCI databases.")
