import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO SUITE", layout="wide")

# --- 2. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_data():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].astype(str).str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

df_axon = load_data()

# --- 3. SIDEBAR: OMNI-SEARCH ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")
user_query = st.sidebar.text_input("🔍 Cerca Target o Farmaco", "").strip().upper()

st.sidebar.divider()
st.sidebar.error("⚠️ **RESEARCH USE ONLY**")

# --- 4. LOGICA DI IDENTIFICAZIONE ---
target_id = user_query
drug_info = None

if user_query:
    try:
        # Check se è un farmaco (ODI)
        res_odi = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{user_query}%").execute()
        if res_odi.data:
            drug_info = res_odi.data[0]
            target_id = str(drug_info['Targets']).split('(')[0].split(';')[0].strip().upper()
            st.sidebar.success(f"Farmaco: {drug_info['Generic_Name']} ➔ Hub: {target_id}")
    except: pass

# --- 5. DASHBOARD HEADER ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

# Visualizzazione ID Target (Sempre visibile se cercato)
if target_id:
    st.markdown(f"# 🎯 TARGET ID: `{target_id}`")
    if drug_info:
        st.info(f"💊 **Correlazione Terapeutica:** {drug_info['Generic_Name']} ({drug_info['Brand_Names']})")
else:
    st.markdown("# 🌐 Global Network View")

# --- 6. RAGNATELA (NETWORK MAP) - IL CUORE DEL SISTEMA ---
st.subheader("🕸️ Network Interaction Map")


if not df_axon.empty:
    G = nx.Graph()
    
    # Selezione nodi: se c'è un target lo mettiamo al centro, altrimenti prendiamo i top hub
    if target_id and target_id in df_axon['target_id'].values:
        center_node = target_id
        satellites = df_axon[df_axon['target_id'] != target_id].sort_values('initial_score', ascending=False).head(10)
    else:
        center_node = df_axon.sort_values('initial_score', ascending=False).iloc[0]['target_id']
        satellites = df_axon.sort_values('initial_score', ascending=False).iloc[1:11]

    # Creazione della ragnatela
    G.add_node(center_node, size=65, color='#FFD700') # Centro Oro
    for _, s_row in satellites.iterrows():
        sid = s_row['target_id']
        G.add_node(sid, size=35, color='#87CEEB') # Satelliti Sky Blue
        G.add_edge(center_node, sid) # Questo crea la linea (la tela)

    pos = nx.spring_layout(G, k=1.0, seed=42)
    
    # Linee della ragnatela
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=2, color='#555'), mode='lines', hoverinfo='none'))
    
    # Nodi (Hub)
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=list(G.nodes()), textposition="top center",
        marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], 
                    color=[G.nodes[n]['color'] for n in G.nodes()], 
                    line=dict(color='white', width=2))
    ))

    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), 
                          yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. OPERA DIRECTOR (GRIGLIA 10 PARAMETRI) ---
if target_id and not df_axon.empty and target_id in df_axon['target_id'].values:
    st.divider()
    st.subheader("🎼 Opera Director Status")
    row = df_axon[df_axon['target_id'] == target_id].iloc[0]
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OMI (Target)", "DETECTED")
    c2.metric("SMI (Pathway)", "ACTIVE")
    c3.metric("ODI (Drug)", "LINKED" if drug_info else "READY")
    c4.metric("TMI (Tox)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
    c5.metric("CES (Score)", f"{row['ces_score']:.2f}")

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("BCI", "OPTIMAL"); c7.metric("GNI", "STABLE")
    c8.metric("EVI", "HIGH"); mphase = "PHASE II/III" if row['ces_score'] > 0.5 else "PRE-CLIN"
    c9.metric("MBI", "BALANCED"); c10.metric("GCI", mphase)

st.divider()
st.caption("MAESTRO Suite v12.1 | Network-Centric Build | RUO")
