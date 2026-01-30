import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 2. CONNESSIONE SUPABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- 3. FUNZIONI DI CARICAMENTO DATI ---
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
def load_gci(query):
    try:
        res = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{query}%").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_odi(query):
    try:
        res = supabase.table("odi_database").select("*").ilike("Targets", f"%{query}%").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_pmi(query):
    try:
        # SMI - Signaling/Pathway database
        res = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{query}%").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

# --- 4. CARICAMENTO INIZIALE ---
df = load_axon()

# --- 5. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

st.sidebar.markdown("### 🎚️ Soglie Analisi")
min_sig = st.sidebar.slider("Soglia Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Opera Focus")
search_query = st.sidebar.text_input("Cerca Target (es. PDCD1, HER2, EGFR)", "").strip().upper()
st.sidebar.warning("⚠️ **RESEARCH USE ONLY**")

# --- 6. LOGICA DI FILTRO E INTERCONNETTIVITÀ ---
gci_df = pd.DataFrame()
target_drugs = pd.DataFrame()
pmi_df = pd.DataFrame()

if search_query and not df.empty:
    # Chiamate ai 3 database satelliti
    gci_df = load_gci(search_query)
    target_drugs = load_odi(search_query)
    pmi_df = load_pmi(search_query)

    # Filtro vicinato per grafici
    all_targets = df['target_id'].tolist()
    if search_query in all_targets:
        idx = all_targets.index(search_query)
        neighbors = all_targets[max(0, idx-2):min(len(all_targets), idx+3)]
        filtered_df = df[df['target_id'].isin(neighbors)]
    else:
        filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 7. OPERA DIRECTOR (INTELLIGENCE HUB) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_info = df[df['target_id'].str.upper() == search_query]
    if not target_info.empty:
        row = target_info.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # --- RIGA 1: MECCANICA & SICUREZZA ---
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
        r1_c1.metric("OMI (Biomarker)", "DETECTED")
        
        # SMI Dinamico dal database PMI
        smi_val = f"{len(pmi_df)} Pathways" if not pmi_df.empty else "STABLE"
        r1_c2.metric("SMI (Pathway)", smi_val)
        
        r1_c3.metric("ODI (Drug)", "TARGETABLE" if not target_drugs.empty else "NO DRUG")
        r1_c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1_c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        # --- RIGA 2: AMBIENTE & HOST ---
        st.markdown("##### 🌍 Ambiente & Host")
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
        r2_c1.metric("BCI (Bio-cost.)", "OPTIMAL")
        r2_c2.metric("GNI (Genetica)", "STABLE")
        r2_c3.metric("EVI (Ambiente)", "LOW RISK")
        r2_c4.metric("MBI (Microbiota)", "RESILIENT")
        
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "PRE-CLIN"
        r2_c5.metric("GCI (Clinica)", phase)
        
        st.divider()

# --- 8. ANALISI PATHWAY (SMI) ---
if not pmi_df.empty:
    st.subheader("🧬 Signaling & Pathway Detail (SMI)")
    for _, p in pmi_df.iterrows():
        with st.expander(f"Pathway: {p['Canonical_Name']} [{p['Category']}]"):
            st.write(f"**Descrizione:** {p['Description_L0']}")
            st.write(f"**Key Readouts:** {p['Key_Readouts']}")
            st.caption(f"Priority: {p['Evidence_Priority']} | Confidence: {p['Confidence_Default']}")

# --- 9. GRAFICI & RAGNATELA ---
st.divider()
col_bar, col_rank = st.columns([2, 1])
with col_bar:
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)

with col_rank:
    st.subheader("🥇 Hub Ranking")
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# Ragnatela
st.subheader("🕸️ Network Interaction Map")
if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        is_f = r['target_id'].upper() == search_query
        G.add_node(r['target_id'], size=float(r['initial_score']) * (45 if is_f else 25), color=float(r['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    
    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#888'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=False))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 10. PORTALI DATI ---
st.divider()
c_odi, c_gci = st.columns(2)
with c_odi:
    st.header("💊 Therapeutics (ODI)")
    if not target_drugs.empty:
        st.dataframe(target_drugs[['Generic_Name', 'Brand_Names', 'Drug_Class', 'Mechanism_Short']], use_container_width=True)

with c_gci:
    st.header("🧪 Clinical Trials (GCI)")
    if not gci_df.empty:
        st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)

# --- FOOTER ---
st.divider()
st.caption("MAESTRO Suite | Powered by Omikron Engine (AXON, GCI, ODI, PMI) | RUO")
