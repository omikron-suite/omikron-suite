import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE & CONNESSIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty: return d
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

# --- 3. LOGICA SATELLITI & CARTELLA FARMACI ---
odi_df = pd.DataFrame()
pmi_df = pd.DataFrame()

if search_query:
    try:
        # Cerchiamo farmaci correlati per la "Cartella" nella Sidebar
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
        
        # Carichiamo pathway per la ragnatela
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
    except: pass

# Visualizzazione Cartella Farmaci nella Sidebar (Solo se ci sono match)
if not odi_df.empty:
    st.sidebar.divider()
    st.sidebar.success(f"📂 **Cartella ODI: {len(odi_df)} Farmaci**")
    st.sidebar.caption(f"Trovate correlazioni terapeutiche per {search_query}")
    with st.sidebar.expander("Visualizza Lista Rapida"):
        for n in odi_df['Generic_Name'].unique():
            st.write(f"💊 {n}")

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
        c2.metric("SMI", f"{len(pmi_df)} Pathways")
        c3.metric("ODI", f"{len(odi_df)} Drugs")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 5. RAGNATELA DINAMICA CON LINK FISICI ---
st.subheader("🕸️ Network Interaction Map")
[Image of an interactive protein-protein interaction network showing nodes and connecting edges]

# Prepariamo i dati per la ragnatela (Target cercato + i suoi vicini)
if not df.empty:
    G = nx.Graph()
    
    if search_query and search_query in df['target_id'].values:
        # Nodo Centrale
        G.add_node(search_query, size=60, color='gold', label=f"🎯 {search_query}")
        
        # 1. Link con Target AXON (Vicinanza nel database)
        idx = df[df['target_id'] == search_query].index[0]
        neighbors = df.iloc[max(0, idx-4):min(len(df), idx+5)]
        for _, r in neighbors.iterrows():
            if r['target_id'] != search_query:
                G.add_node(r['target_id'], size=30, color='skyblue', label=r['target_id'])
                G.add_edge(search_query, r['target_id']) # LINK FISICO
        
        # 2. Link con Pathway (PMI)
        for _, pw in pmi_df.head(3).iterrows():
            p_node = pw['Canonical_Name']
            G.add_node(p_node, size=25, color='violet', label=f"🧬 {p_node}")
            G.add_edge(search_query, p_node) # LINK FISICO
    else:
        # Vista Default se non c'è ricerca
        top_hubs = df.sort_values('initial_score', ascending=False).head(10)
        for _, r in top_hubs.iterrows():
            G.add_node(r['target_id'], size=35, color='lightgray', label=r['target_id'])

    # Calcolo Layout
    pos = nx.spring_layout(G, k=1.2, seed=42)
    
    # Creazione Archi (Linee)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'))
    
    # Creazione Nodi (Cerchi)
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode='markers+text', text=[G.nodes[n].get('label', n) for n in G.nodes()],
        textposition="top center",
        marker=dict(size=[G.nodes[n].get('size', 20) for n in G.nodes()],
                    color=[G.nodes[n].get('color', 'gray') for n in G.nodes()],
                    line=dict(width=2, color='white'))
    ))

    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 6. TABELLE DATI BASSO ---
if search_query:
    st.divider()
    t_odi, t_pmi = st.columns(2)
    with t_odi:
        st.header("💊 Therapeutics (ODI)")
        if not odi_df.empty:
            st.dataframe(odi_df[['Generic_Name', 'Drug_Class', 'Targets']], use_container_width=True)
    with t_pmi:
        st.header("🧬 Pathways (PMI)")
        if not pmi_df.empty:
            st.dataframe(pmi_df[['Canonical_Name', 'Category']], use_container_width=True)

st.caption("MAESTRO Suite | Hub-Focused Build v15.2 | RUO")
