import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Suite", layout="wide")

# --- 2. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=300)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.warning("⚠️ **RESEARCH USE ONLY**")
st.sidebar.title("Control Panel")

min_sig = st.sidebar.slider("Soglia Segnale", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità", 0.0, 1.0, 0.8)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Cerca Target (es. KRAS)", "").strip().upper()

# Logica Filtro
if search_query and not df.empty:
    filtered_df = df[df['target_id'].str.upper().contains(search_query, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]

# --- 4. DASHBOARD ---
st.title("🛡️ MAESTRO Suite")

if search_query:
    st.divider()
    # Recupero info specifica per il target cercato
    target_data = df[df['target_id'].str.upper() == search_query]
    
    col_stat, col_3d = st.columns([1, 1.2])
    
    with col_stat:
        st.subheader(f"Target Intelligence: {search_query}")
        if not target_data.empty:
            row = target_data.iloc[0]
            m1, m2 = st.columns(2)
            m1.metric("Score VTG", row['initial_score'])
            m2.metric("Rischio TMI", "ALTO" if row['toxicity_index'] > 0.7 else "OK")
            
            # Info GCI
            gci_res = supabase.table("GCI_clinical_trials").select("Phase").ilike("Primary_Biomarker", f"%{search_query}%").execute()
            phase = gci_res.data[0]['Phase'] if gci_res.data else "N/D"
            st.metric("Clinical Phase", phase)
        else:
            st.error(f"Target '{search_query}' non trovato nel database AXON.")

    with col_3d:
        # VISUALIZZATORE 3D (iCn3D - Più leggero)
        pdb_code = target_data['pdb_id'].values[0] if not target_data.empty and 'pdb_id' in target_data.columns else None
        
        if pdb_code and str(pdb_code) != 'nan':
            st.subheader(f"Struttura Proteica (PDB: {pdb_code})")
            # iCn3D viewer URL
            view_url = f"https://www.ncbi.nlm.nih.gov/Structure/icn3d/full.html?pdbid={pdb_code}&width=500&height=400&showcommand=0&shownote=0"
            st.components.v1.iframe(view_url, height=450)
        else:
            st.info("🧬 Inserisci un PDB ID in Supabase per vedere la struttura 3D.")

# --- 5. GRAFICI ---
st.divider()
c1, c2 = st.columns([2, 1])
with c1:
    st.subheader("Visualizzazione Globale")
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)

with c2:
    st.subheader("Hub Network")
    if not filtered_df.empty:
        # Ragnatela semplificata per performance
        G = nx.Graph()
        for t in filtered_df['target_id']: G.add_node(t)
        nodes = list(G.nodes())
        if len(nodes) > 1:
            for i in range(len(nodes)-1): G.add_edge(nodes[i], nodes[i+1])
        pos = nx.spring_layout(G)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        fig_net = go.Figure(data=[go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines'),
                                  go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', text=nodes, marker=dict(size=15, color="orange"))])
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_net, use_container_width=True)

# --- 6. GCI TABLE ---
st.divider()
st.subheader("🧪 Clinical Portal")
if search_query:
    gci_data = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
    if gci_data.data:
        st.dataframe(pd.DataFrame(gci_data.data)[['Canonical_Title', 'Phase', 'Year', 'Key_Results_PFS']], use_container_width=True)
