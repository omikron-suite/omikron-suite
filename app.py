import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE & CONNESSIONE (Anti-Errore) ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# Prova a prendere da Secrets, altrimenti usa le stringhe dirette
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"

try:
    supabase = create_client(URL, KEY)
except:
    st.error("Errore di connessione al Database. Verifica le credenziali.")

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data or [])
        if not d.empty:
            d["target_id"] = d["target_id"].astype(str).str.strip().upper()
            d["initial_score"] = pd.to_numeric(d["initial_score"], errors="coerce").fillna(0.0)
            d["toxicity_index"] = pd.to_numeric(d["toxicity_index"], errors="coerce").fillna(0.0)
            d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except: return pd.DataFrame()

df = load_axon()

# --- 2. SIDEBAR & RICERCA HUB ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control")

st.sidebar.markdown("### 🔍 Hub Focus")
search_query = st.sidebar.text_input("Inserisci Target ID", placeholder="es. KRAS").strip().upper()

# --- 3. LOGICA SATELLITI & CARTELLA FARMACI (SIDEBAR) ---
odi_df = pd.DataFrame()
if search_query:
    try:
        # Cerchiamo farmaci correlati per la "Cartella" nella Sidebar
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except: pass

# Visualizzazione Cartella Farmaci (Solo se ci sono match)
if not odi_df.empty:
    st.sidebar.divider()
    st.sidebar.success(f"📂 **Cartella ODI: {len(odi_df)} Farmaci**")
    with st.sidebar.expander("Apri Cartella"):
        for n in odi_df['Generic_Name'].unique():
            st.write(f"💊 {n}")
else:
    if search_query:
        st.sidebar.info("📂 Cartella Vuota: Nessun farmaco ODI")

st.sidebar.divider()
st.sidebar.warning("⚠️ RUO - Research Use Only")

# --- 4. DASHBOARD & OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_match = df[df["target_id"] == search_query]
    if not target_match.empty:
        row = target_match.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", "ACTIVE")
        c3.metric("ODI", f"{len(odi_df)} Drugs")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 5. RAGNATELA CON LINK FISICI (Sempre generata) ---
st.subheader("🕸️ Network Interaction Map")


if not df.empty:
    G = nx.Graph()
    
    # Se c'è un target cercato, diventa il centro
    if search_query and search_query in df['target_id'].values:
        center_node = search_query
        G.add_node(center_node, size=60, color='gold', label=f"🎯 {center_node}")
        
        # Creiamo i link verso i vicini
        idx = df[df['target_id'] == search_query].index[0]
        neighbors = df.iloc[max(0, idx-5):min(len(df), idx+6)]
        for _, r in neighbors.iterrows():
            if r['target_id'] != center_node:
                G.add_node(r['target_id'], size=30, color='skyblue', label=r['target_id'])
                G.add_edge(center_node, r['target_id']) # CREAZIONE LINK FISICO
    else:
        # Se non c'è ricerca, mostriamo gli Hub principali
        top_hubs = df.sort_values('initial_score', ascending=False).head(10)
        for _, r in top_hubs.iterrows():
            G.add_node(r['target_id'], size=35, color='lightgray', label=r['target_id'])

    # Calcolo Layout a ragnatela
    pos = nx.spring_layout(G, k=1.0, seed=42)
    
    # Disegno Linee
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'))
    
    # Disegno Nodi
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=[G.nodes[n].get('label', n) for n in G.nodes()],
        textposition="top center",
        marker=dict(size=[G.nodes[n].get('size', 25) for n in G.nodes()],
                    color=[G.nodes[n].get('color', 'gray') for n in G.nodes()],
                    line=dict(width=2, color='white'))
    ))

    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 6. TABELLE DATI BASSO ---
if search_query and not odi_df.empty:
    st.divider()
    st.header("💊 Therapeutics (ODI) - Dettaglio")
    st.dataframe(odi_df[['Generic_Name', 'Drug_Class', 'Targets', 'Regulatory_Status_US']], use_container_width=True)

st.caption("MAESTRO Suite | v15.3 Stable | RUO")
