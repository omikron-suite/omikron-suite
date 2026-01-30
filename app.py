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

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            # Calcolo efficacia pesata
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except Exception:
        return pd.DataFrame()

df = load_axon()

# --- 3. SIDEBAR (Pannello di Controllo) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

# Disclaimer Obbligatorio
st.sidebar.warning("⚠️ **RESEARCH USE ONLY**\n\nNot for diagnostic or therapeutic use.")

st.sidebar.markdown("### 🎚️ Parametri VTG Gate")
min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Smart Search & Hub Focus")
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS").strip().upper()

# --- 4. LOGICA DI FILTRO (Hub + Vicini) ---
if search_query and not df.empty:
    all_targets = df['target_id'].str.upper().tolist()
    if search_query in all_targets:
        idx = all_targets.index(search_query)
        # Mostriamo il target e i suoi "vicini" nel database
        neighbor_indices = range(max(0, idx-2), min(len(all_targets), idx+3))
        neighbors = [df.iloc[i]['target_id'] for i in neighbor_indices]
        filtered_df = df[df['target_id'].isin(neighbors)]
    else:
        filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]

# --- TITOLO ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

# --- 5. TARGET SUMMARY CARD + 3D PROTEIN VIEW ---
if search_query:
    st.divider()
    axon_target = df[df['target_id'].str.upper() == search_query]
    
    col_info, col_3d = st.columns([1, 1])
    
    with col_info:
        st.subheader(f"Target Intelligence: {search_query}")
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        
        with m1:
            score = axon_target['initial_score'].values[0] if not axon_target.empty else "N/D"
            st.metric("Efficacia VTG", f"{score}")
        with m2:
            tox = axon_target['toxicity_index'].values[0] if not axon_target.empty else 0.5
            status = "SICURO" if tox < 0.4 else "MODERATO" if tox < 0.7 else "ALTO RISCHIO"
            st.metric("Profilo Rischio", status)
        
        # Recupero rapido fase clinica
        res_gci = supabase.table("GCI_clinical_trials").select("Phase").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        with m3:
            phase = res_gci.data[0]['Phase'] if res_gci.data else "Pre-Clinico"
            st.metric("Max Clinical Phase", phase)
        with m4:
            st.metric("Data Source", "AXON/GCI Hub")

    with col_3d:
        # Visualizzatore Proteina PDB
        pdb_code = axon_target['pdb_id'].values[0] if not axon_target.empty and 'pdb_id' in axon_target.columns else None
        if pdb_code:
            st.subheader(f"Struttura 3D (PDB: {pdb_code})")
            # Integrazione Mol* viewer ufficiale
            components_url = f"https://www.rcsb.org/3d-view/{pdb_code}?preset=cartoons"
            st.components.v1.iframe(components_url, height=400)
        else:
            st.info("🧬 Nessuna struttura 3D mappata per questo target.")

# --- 6. ANALISI AXON ---
st.divider()
c1, c2 = st.columns([2, 1])
with c1:
    st.subheader("Potenza Segnale vs Tossicità")
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with c2:
    st.subheader("🥇 Top Efficiency")
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 7. RAGNATELA DINAMICA ---
st.divider()
st.subheader("🕸️ Network Interaction Map (Relational Focus)")
if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        is_focus = row['target_id'].upper() == search_query
        G.add_node(row['target_id'], size=float(row['initial_score']) * (45 if is_focus else 25), color=float(row['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        for node in nodes:
            if node != search_query: G.add_edge(search_query, node)
    elif len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))): G.add_edge(nodes[i], nodes[j])

    pos = nx.spring_layout(G, k=0.6, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#888'), mode='lines', hoverinfo='none')
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]; node_x.append(x); node_y.append(y); node_text.append(node)
        node_color.append(G.nodes[node]['color']); node_size.append(G.nodes[node]['size'])

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="top center",
                            marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size, 
                            line=dict(color='white', width=2)))

    st.plotly_chart(go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')), use_container_width=True)

# --- 8. GCI PORTAL ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if search_query:
    res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
    gci_df = pd.DataFrame(res_gci.data)
    if not gci_df.empty:
        st.success(f"Trovate {len(gci_df)} evidenze per '{search_query}'")
        cols = ['Canonical_Title', 'Phase', 'Year', 'Cancer_Type', 'Practice_Changing', 'Key_Results_PFS', 'Main_Toxicities']
        st.dataframe(gci_df[[c for c in cols if c in gci_df.columns]], use_container_width=True)

# --- 9. FOOTER ---
st.divider()
st.caption("Disclaimer: This platform is for research purposes only (RUO). Data provided by AXON and GCI are for scientific analysis.")
