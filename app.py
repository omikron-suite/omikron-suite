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
def load_gci(target_query):
    try:
        res = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{target_query}%").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_odi(target_query):
    try:
        # Interroga la nuova tabella odi_database su Supabase
        res = supabase.table("odi_database").select("*").ilike("Targets", f"%{target_query}%").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

# Caricamento database AXON iniziale
df = load_axon()

# --- 4. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

st.sidebar.markdown("### 🎚️ Soglie Analisi")
min_sig = st.sidebar.slider("Soglia Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Opera Focus")
search_query = st.sidebar.text_input("Cerca Target (es. PDCD1, HER2, EGFR)", "").strip().upper()
st.sidebar.warning("⚠️ **RESEARCH USE ONLY**\n\nNot for diagnostic use.")

# --- 5. LOGICA DI FILTRO E INTERCONNESSIONE ---
gci_df = pd.DataFrame()
target_drugs = pd.DataFrame()

if search_query and not df.empty:
    # Interconnessione Database
    gci_df = load_gci(search_query)
    target_drugs = load_odi(search_query)

    # Filtro per Visualizzazione (Target + Vicini)
    all_targets = df['target_id'].tolist()
    if search_query in all_targets:
        idx = all_targets.index(search_query)
        neighbors = all_targets[max(0, idx-2):min(len(all_targets), idx+3)]
        filtered_df = df[df['target_id'].isin(neighbors)]
    else:
        filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 6. OPERA DIRECTOR (INTELLIGENCE MISSION CONTROL) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_info = df[df['target_id'].str.upper() == search_query]
    if not target_info.empty:
        row = target_info.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # --- RIGA 1: MECCANICA & SICUREZZA ---
        st.markdown("##### ⚙️ Meccanica & Sicurezza (Il Motore)")
        r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
        r1_c1.metric("OMI (Biomarker)", "DETECTED" if not target_info.empty else "N/D")
        r1_c2.metric("SMI (Pathway)", "ACTIVE" if row['initial_score'] > 1.5 else "STABLE")
        
        # ODI DINAMICO da Supabase
        odi_status = "TARGETABLE" if not target_drugs.empty else "NO DRUG"
        r1_c3.metric("ODI (Drug)", odi_status)
        
        r1_c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1_c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        # --- RIGA 2: AMBIENTE & HOST ---
        st.markdown("##### 🌍 Ambiente & Host (Il Terreno)")
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
        r2_c1.metric("BCI (Bio-cost.)", "OPTIMAL")
        r2_c2.metric("GNI (Genetica)", "STABLE")
        r2_c3.metric("EVI (Ambiente)", "LOW RISK")
        r2_c4.metric("MBI (Microbiota)", "RESILIENT")
        
        # GCI DINAMICO da Supabase
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "PRE-CLIN"
        r2_c5.metric("GCI (Clinica)", phase)
        
        # Export Report Quick Button
        st.write("")
        report_data = f"TARGET: {search_query}\nCES Score: {row['ces_score']}\nDrugs Found: {len(target_drugs)}\nPhase: {phase}"
        st.download_button("💾 Export Intelligence Data", report_data, file_name=f"MAESTRO_{search_query}.txt")
        st.divider()

# --- 7. ANALISI QUANTITATIVA & RANKING ---
col_bar, col_rank = st.columns([2, 1])
with col_bar:
    st.subheader("Visualizzazione Efficacia vs Tossicità")
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with col_rank:
    st.subheader("🥇 Hub Ranking")
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 8. NETWORK INTERACTION MAP ---
st.divider()
st.subheader("🕸️ Network Interaction Map (Relational Focus)")
if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        is_f = r['target_id'].upper() == search_query
        G.add_node(r['target_id'], size=float(r['initial_score']) * (45 if is_f else 25), color=float(r['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))): G.add_edge(nodes[i], nodes[j])
    
    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#999'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=False))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 9. PORTALI DATI (ODI & GCI) ---
col_odi, col_gci = st.columns(2)

with col_odi:
    st.header("💊 Therapeutics (ODI)")
    if not target_drugs.empty:
        st.dataframe(target_drugs[['Generic_Name', 'Brand_Names', 'Drug_Class', 'Mechanism_Short']], use_container_width=True)
    elif search_query:
        st.info("Nessun farmaco in ODI database.")

with col_gci:
    st.header("🧪 Clinical Trials (GCI)")
    if not gci_df.empty:
        st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)
    elif search_query:
        st.info("Nessun trial in GCI database.")

# --- FOOTER ---
st.divider()
st.caption("MAESTRO Suite | Integration of AXON, GCI, and ODI Databases | RUO - Research Use Only")
