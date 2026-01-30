import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. SETUP ---
st.set_page_config(page_title="MAESTRO Suite", layout="wide")

# Connessione
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=300)
def load_data():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].str.strip().upper()
            if 'initial_score' in d.columns and 'toxicity_index' in d.columns:
                d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except:
        return pd.DataFrame()

df = load_data()

# --- 2. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")
st.sidebar.warning("⚠️ RESEARCH USE ONLY")

# Filtri
st.sidebar.subheader("🎚️ Soglie Globale")
min_sig = st.sidebar.slider("Segnale Minimo (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Tossicità Massima (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.subheader("🔍 Ricerca Target")
search_query = st.sidebar.text_input("Inserisci Biomarker (es. KRAS)", "").strip().upper()

# --- 3. LOGICA FILTRO ---
if search_query and not df.empty:
    # Mostriamo il target cercato + i suoi vicini nel DB
    all_t = df['target_id'].tolist()
    if search_query in all_t:
        idx = all_t.index(search_query)
        neighbors = all_t[max(0, idx-2):min(len(all_t), idx+3)]
        filtered_df = df[df['target_id'].isin(neighbors)]
    else:
        filtered_df = df[df['target_id'].str.contains(search_query, na=False)]
else:
    if not df.empty:
        filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)]
    else:
        filtered_df = pd.DataFrame()

# --- 4. LAYOUT PRINCIPALE ---
st.title("🛡️ Omikron Orchestra: MAESTRO Suite")

if search_query:
    st.divider()
    t_data = df[df['target_id'] == search_query]
    
    col_info, col_3d = st.columns([1, 1.2])
    
    with col_info:
        st.header(f"Hub: {search_query}")
        if not t_data.empty:
            row = t_data.iloc[0]
            c1, c2 = st.columns(2)
            c1.metric("Score VTG", row.get('initial_score', 'N/D'))
            c2.metric("Rischio TMI", "ALTO" if row.get('toxicity_index', 0) > 0.7 else "OK")
            
            # GCI Quick Look
            try:
                gci_q = supabase.table("GCI_clinical_trials").select("Phase").ilike("Primary_Biomarker", f"%{search_query}%").execute()
                phase = gci_q.data[0]['Phase'] if gci_q.data else "Pre-Clinico"
                st.metric("Clinical Phase", phase)
            except:
                st.metric("Clinical Phase", "Database Error")
        else:
            st.error("Target non trovato in AXON Knowledge.")

    with col_3d:
        # PDB ID check
        pdb = t_data['pdb_id'].values[0] if not t_data.empty and 'pdb_id' in t_data.columns else None
        if pdb and str(pdb) != 'nan':
            st.subheader(f"Struttura 3D (PDB: {pdb})")
            # iCn3D è il più stabile per Streamlit
            url_3d = f"https://www.ncbi.nlm.nih.gov/Structure/icn3d/full.html?pdbid={pdb}&width=500&height=400&showcommand=0"
            st.components.v1.iframe(url_3d, height=450)
        else:
            st.info("🧬 Dati strutturali 3D non mappati per questo target.")

# --- 5. VISUALIZZAZIONI ---
st.divider()
tab1, tab2 = st.tabs(["📊 Analisi Quantitativa", "🕸️ Network Map"])

with tab1:
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
    else:
        st.write("Nessun dato per i filtri selezionati.")

with tab2:
    if not filtered_df.empty:
        # Ragnatela Robusta
        G = nx.Graph()
        for t in filtered_df['target_id']: G.add_node(t)
        nodes = list(G.nodes())
        if len(nodes) > 1:
            for i in range(len(nodes)-1): G.add_edge(nodes[i], nodes[i+1])
        pos = nx.spring_layout(G, seed=42)
        
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
            
        fig_net = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'),
            go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], 
                       mode='markers+text', text=nodes, textposition="top center",
                       marker=dict(size=20, color="gold", line=dict(width=2, color="white")))
        ])
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), 
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                              yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_net, use_container_width=True)

# --- 6. GCI PORTAL ---
st.divider()
st.subheader("🧪 Evidence Cliniche (GCI)")
if search_query:
    try:
        g_res = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        if g_res.data:
            st.dataframe(pd.DataFrame(g_res.data)[['Canonical_Title', 'Phase', 'Year', 'Key_Results_PFS']], use_container_width=True)
        else:
            st.info("Nessun trial clinico trovato per questo biomarker.")
    except:
        st.error("Errore di connessione al database GCI.")
else:
    st.info("💡 Cerca un target per vedere i trial clinici.")
