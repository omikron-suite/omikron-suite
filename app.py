import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE & CONNESSIONE ---
st.set_page_config(page_title="MAESTRO SUITE", layout="wide")

URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_core_data():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].astype(str).str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

df_axon = load_core_data()

# --- 2. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

# Ricerca Unificata
st.sidebar.subheader("🔍 Omni-Search")
user_query = st.sidebar.text_input("Target o Farmaco (es. KRAS, pembro)", "").strip().upper()

# Tasto Correlazione (Lego)
st.sidebar.divider()
show_intel = st.sidebar.toggle("🔗 Intelligence Linker", help="Attiva analisi incrociata")

st.sidebar.divider()
st.sidebar.error("⚠️ **RESEARCH USE ONLY**")

# --- 3. LOGICA DI IDENTIFICAZIONE ---
target_id = user_query
drug_info = None

if user_query and show_intel:
    try:
        # Cerchiamo il farmaco nel database ODI
        res_odi = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{user_query}%").execute()
        if res_odi.data:
            drug_info = res_odi.data[0]
            # Estrazione Target: Pembro -> PDCD1
            target_id = str(drug_info['Targets']).split('(')[0].split(';')[0].strip().upper()
            st.sidebar.success(f"Farmaco: {drug_info['Generic_Name']} ➔ Hub: {target_id}")
    except: pass

# --- 4. DASHBOARD HEADER ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if target_id:
    st.markdown(f"# 🎯 TARGET ID: `{target_id}`")
    if drug_info:
        st.info(f"💊 **Correlazione Terapeutica:** {drug_info['Generic_Name']} ({drug_info['Brand_Names']})")
    
    # --- 5. OPERA DIRECTOR (GRIGLIA 10 PARAMETRI) ---
    if not df_axon.empty and target_id in df_axon['target_id'].values:
        row = df_axon[df_axon['target_id'] == target_id].iloc[0]
        
        st.subheader("🎼 Opera Director Status")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Target)", "DETECTED")
        c2.metric("SMI (Pathway)", "ACTIVE")
        c3.metric("ODI (Drug)", "LINKED" if drug_info else "READY")
        c4.metric("TMI (Tox)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES (Score)", f"{row['ces_score']:.2f}")

        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI", "OPTIMAL"); c7.metric("GNI", "STABLE")
        c8.metric("EVI", "HIGH"); c9.metric("MBI", "BALANCED"); c10.metric("GCI", "PHASE II/III")
        st.divider()

    # --- 6. RAGNATELA (NETWORK MAP - FORZATA) ---
    st.subheader("🕸️ Network Interaction Map")
    
    
    if not df_axon.empty:
        G = nx.Graph()
        # Centro (Il Target Cercato)
        G.add_node(target_id, size=60, color='#FFD700') # Oro
        
        # Satelliti (Top Hubs dal database)
        satellites = df_axon[df_axon['target_id'] != target_id].sort_values('initial_score', ascending=False).head(8)
        for _, s_row in satellites.iterrows():
            sid = s_row['target_id']
            G.add_node(sid, size=30, color='#87CEEB') # Sky Blue
            G.add_edge(target_id, sid) # Disegna la linea della ragnatela!

        pos = nx.spring_layout(G, k=0.8, seed=42)
        
        # Tracciamento Linee
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#888'), mode='lines', hoverinfo='none'))
        
        # Tracciamento Nodi
        fig_net.add_trace(go.Scatter(
            x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
            mode='markers+text', text=list(G.nodes()), textposition="top center",
            marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()], line_width=2)
        ))

        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_net, use_container_width=True)

else:
    st.info("👋 Inserisci un Target o un Farmaco nella barra laterale per attivare l'orchestra.")

st.caption("MAESTRO Suite v12.0 | Stabilized Build | RUO")
