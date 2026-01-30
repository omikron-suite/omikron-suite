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
def load_axon_core():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].astype(str).str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

df_axon = load_axon_core()

# --- 2. SIDEBAR (LOGICA SEPARATA) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

st.sidebar.subheader("🧬 Sezione Target")
target_input = st.sidebar.text_input("Hub Target (es. KRAS)", "").strip().upper()

st.sidebar.divider()
st.sidebar.subheader("💊 Sezione Farmaco")
drug_input = st.sidebar.text_input("Cerca Farmaco (es. pembro)", "").strip().lower()

st.sidebar.divider()
st.sidebar.caption("RUO - Research Use Only")

# --- 3. MODULO 1: RAGNATELA (BIOLOGIA) ---
st.title("🛡️ MAESTRO: Omikron Orchestra")

# Header dinamico
if target_input:
    st.header(f"🕸️ Network Analysis: {target_input}")
else:
    st.header("🕸️ Global Network Explorer")

if not df_axon.empty:
    G = nx.Graph()
    # Definizione centro e satelliti
    if target_input and target_input in df_axon['target_id'].values:
        center = target_input
        # Prendiamo i top 8 hub per affollare la ragnatela
        satellites = df_axon[df_axon['target_id'] != target_input].sort_values('initial_score', ascending=False).head(8)
    else:
        # Vista di default
        top_hubs = df_axon.sort_values('initial_score', ascending=False).head(9)
        center = top_hubs.iloc[0]['target_id']
        satellites = top_hubs.iloc[1:]

    # Costruzione fisica dei link
    G.add_node(center, size=60, color='#FFD700') # Centro Oro
    for _, s in satellites.iterrows():
        sid = s['target_id']
        G.add_node(sid, size=30, color='#87CEEB') # Satelliti Sky Blue
        G.add_edge(center, sid)

    pos = nx.spring_layout(G, k=1.0, seed=42)
    
    # Rendering Plotly
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#888'), mode='lines', hoverinfo='none'))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=list(G.nodes()), textposition="top center",
        marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()], line_width=2)
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=False, zeroline=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 4. MODULO 2: OPERA DIRECTOR (SCORE TARGET) ---
if target_input and target_input in df_axon['target_id'].values:
    st.divider()
    row = df_axon[df_axon['target_id'] == target_input].iloc[0]
    st.subheader(f"🎼 Opera Director Status: {target_input}")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OMI", "DETECTED")
    c2.metric("SMI", "ACTIVE")
    c3.metric("ODI", "READY")
    c4.metric("TMI", f"{row['toxicity_index']:.2f}")
    c5.metric("CES", f"{row['ces_score']:.2f}")

# --- 5. MODULO 3: HUB FARMACO (INDIPENDENTE) ---
st.divider()
st.subheader("💊 Hub Farmaco")

if drug_input:
    try:
        # Ricerca farmaco indipendente
        res_odi = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{drug_input}%").execute()
        if res_odi.data:
            drug = res_odi.data[0]
            st.success(f"**Identificato:** {drug['Generic_Name']} ({drug['Brand_Names']})")
            
            # --- FINESTRA DI CORRELAZIONE ---
            if target_input:
                drug_targets = str(drug['Targets']).upper()
                if target_input in drug_targets:
                    st.info(f"🎯 **MATCH RILEVATO**: Il farmaco `{drug['Generic_Name']}` è correlato a `{target_input}`.")
                else:
                    st.warning(f"⚠️ **NESSUN MATCH**: `{drug['Generic_Name']}` agisce su `{drug['Targets']}`.")
            
            # Dettagli Farmaco
            st.markdown(f"**Classe:** {drug['Drug_Class']} | **Status:** {drug['Regulatory_Status_US']}")
            st.write(f"**Targets ODI:** {drug['Targets']}")
        else:
            st.error("Nessun farmaco trovato.")
    except:
        st.error("Errore di caricamento database ODI.")
else:
    st.info("Utilizza la sidebar per cercare un farmaco e analizzare la correlazione.")

st.caption("MAESTRO Suite v13.1 | Modular LEGO Architecture")
