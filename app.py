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

@st.cache_data(ttl=600)
def load_data():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control")
st.sidebar.warning("⚠️ **RESEARCH USE ONLY**")

st.sidebar.markdown("### 🎚️ Soglie VTG Gate")
min_sig = st.sidebar.slider("Segnale Minimo", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Tossicità Massima", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Ricerca Target")
search_query = st.sidebar.text_input("Cerca Biomarker (es. KRAS)", "").strip().upper()

# Logica di Filtro
if search_query and not df.empty:
    filtered_df = df[df['target_id'].str.upper().str.contains(search_query, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 4. DASHBOARD ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Analisi Efficacia vs Tossicità (AXON)")
    if not filtered_df.empty:
        fig = px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                     color_continuous_scale="RdYlGn_r", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato corrispondente ai filtri.")

with col2:
    st.subheader("🥇 Top Targets")
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values('initial_score', ascending=False)[['target_id', 'initial_score']], use_container_width=True)

# --- 5. RAGNATELA (NETWORK MAP) ---
st.divider()
st.subheader("🕸️ Network Interaction Map")
if not filtered_df.empty:
    G = nx.Graph()
    for t in filtered_df['target_id']:
        G.add_node(t)
    nodes = list(G.nodes())
    if len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))):
                G.add_edge(nodes[i], nodes[j])
    
    pos = nx.spring_layout(G, k=0.5, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center", marker=dict(size=20, color="gold"))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_net, use_container_width=True)

# --- 6. GCI PORTAL ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if search_query:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        if not gci_df.empty:
            st.success(f"Trovate {len(gci_df)} evidenze per '{search_query}'")
            cols = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Key_Results_PFS']
            st.dataframe(gci_df[[c for c in cols if c in gci_df.columns]], use_container_width=True)
        else:
            st.warning("Nessun trial clinico trovato per questo biomarker.")
    except:
        st.error("Errore di connessione al database GCI.")
else:
    st.info("💡 Inserisci un biomarker per vedere i dati clinici.")
