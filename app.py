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

# --- 2. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

st.sidebar.subheader("🧬 1. Selezione Target")
target_input = st.sidebar.text_input("Inserisci Hub (es. KRAS, PDCD1)", "").strip().upper()

st.sidebar.divider()
st.sidebar.subheader("💊 2. Ricerca Farmaco")
drug_input = st.sidebar.text_input("Inserisci Farmaco (es. pembro)", "").strip().lower()

st.sidebar.divider()
st.sidebar.warning("⚠️ RUO - Research Use Only")

# --- 3. PARTE SUPERIORE: RAGNATELA (Focalizzata sul Target) ---
st.title("🛡️ MAESTRO: Omikron Orchestra")

if target_input:
    st.subheader(f"🕸️ Network Map: {target_input}")
else:
    st.subheader("🕸️ Global Hub Network")



if not df_axon.empty:
    G = nx.Graph()
    # Selezioniamo il centro e i satelliti
    if target_input and target_input in df_axon['target_id'].values:
        center = target_input
        satellites = df_axon[df_axon['target_id'] != target_input].sort_values('initial_score', ascending=False).head(8)
    else:
        center = df_axon.sort_values('initial_score', ascending=False).iloc[0]['target_id']
        satellites = df_axon.sort_values('initial_score', ascending=False).iloc[1:9]

    G.add_node(center, size=60, color='#FFD700')
    for _, s in satellites.iterrows():
        G.add_node(s['target_id'], size=30, color='#87CEEB')
        G.add_edge(center, s['target_id'])

    pos = nx.spring_layout(G, k=1.0, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#777'), mode='lines', hoverinfo='none'))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=list(G.nodes()), textposition="top center",
        marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()], line_width=2)
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 4. OPERA DIRECTOR (Solo se il target è selezionato) ---
if target_input and target_input in df_axon['target_id'].values:
    st.divider()
    st.subheader(f"🎼 Opera Director Status: {target_input}")
    row = df_axon[df_axon['target_id'] == target_input].iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OMI", "DETECTED")
    c2.metric("SMI", "ACTIVE")
    c3.metric("ODI", "READY")
    c4.metric("TMI", f"{row['toxicity_index']:.2f}")
    c5.metric("CES", f"{row['ces_score']:.2f}")
    
    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("BCI", "OK"); c7.metric("GNI", "STABLE"); c8.metric("EVI", "HIGH"); c9.metric("MBI", "NEUTRAL"); c10.metric("GCI", "TRIAL")

# --- 5. PARTE INFERIORE: MODULO FARMACO INDIPENDENTE ---
st.divider()
st.subheader("💊 Independent Drug Analysis")

if drug_input:
    try:
        res_odi = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{drug_input}%").execute()
        if res_odi.data:
            drug = res_odi.data[0]
            st.success(f"**Farmaco Trovato:** {drug['Generic_Name']} ({drug['Brand_Names']})")
            
            # LOGICA DI MATCH (Se è selezionato anche un target)
            if target_input:
                drug_targets = str(drug['Targets']).upper()
                if target_input in drug_targets:
                    st.balloons()
                    st.info(f"🎯 **MATCH RILEVATO:** {drug['Generic_Name']} è validato per agire su {target_input}.")
                else:
                    st.warning(f"⚠️ **NESSUN MATCH:** {drug['Generic_Name']} agisce su `{drug['Targets']}`, non su {target_input}.")
            
            st.json(drug) # Mostra tutti i dettagli del farmaco in modo pulito
        else:
            st.error("Nessun farmaco trovato con questo nome.")
    except:
        st.error("Errore di connessione al database farmaci.")
else:
    st.info("Digita un farmaco nella sidebar per analizzarlo indipendentemente.")

st.caption("MAESTRO Suite v13.0 | Split Logic Build | RUO")
