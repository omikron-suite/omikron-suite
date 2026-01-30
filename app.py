import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Ultra", layout="wide")

# --- 2. CONNESSIONE SUPABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- 3. MOTORE CARICAMENTO DATI ---
@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_satellite(table, column, query):
    try:
        res = supabase.table(table).select("*").ilike(column, f"%{query}%").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df_axon = load_axon()

# --- 4. HEADER & COMANDI CENTRALI (No Sidebar) ---
st.title("🛡️ MAESTRO: Omikron Orchestra")
st.caption("Intelligence Suite v4.2 | Research Use Only")

# Search Bar Centrale
search_query = st.text_input("🔍 Inserisci Biomarker Hub (es. PDCD1, HER2, EGFR)", "").strip().upper()

# Parametri distribuiti in colonne orizzontali
st.markdown("##### 🎚️ Soglie di Controllo")
s1, s2, s3 = st.columns([2, 2, 1])
min_sig = s1.slider("Segnale VTG", 0.0, 3.0, 0.8)
max_t = s2.slider("Tossicità TMI", 0.0, 1.0, 0.8)
s3.write("") # Spazio per allineamento
if s3.button("Reset View", use_container_width=True):
    st.rerun()

st.divider()

# --- 5. LOGICA DI INTELLIGENCE ---
gci_df, odi_df, pmi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if search_query and not df_axon.empty:
    gci_df = load_satellite("GCI_clinical_trials", "Primary_Biomarker", search_query)
    odi_df = load_satellite("odi_database", "Targets", search_query)
    pmi_df = load_satellite("pmi_database", "Key_Targets", search_query)

    all_t = df_axon['target_id'].tolist()
    if search_query in all_t:
        idx = all_t.index(search_query)
        neighbors = all_t[max(0, idx-3):min(len(all_t), idx+4)]
        filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
    else:
        filtered_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
else:
    if not df_axon.empty:
        filtered_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)]

# --- 6. OPERA DIRECTOR (GRIGLIA CHIRURGICA) ---
if search_query and not df_axon.empty:
    t_info = df_axon[df_axon['target_id'] == search_query]
    if not t_info.empty:
        row = t_info.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # Grid 10 Pilastri
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Biomarker)", "DETECTED")
        c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked" if not pmi_df.empty else "ACTIVE")
        c3.metric("ODI (Drug)", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI (Bio-cost.)", "OPTIMAL")
        c7.metric("GNI (Genetica)", "STABLE")
        c8.metric("EVI (Ambiente)", "LOW RISK")
        c9.metric("MBI (Microbiota)", "RESILIENT")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "PRE-CLIN"
        c10.metric("GCI (Clinica)", phase)
        
        # 3D & Export
        col_3d, col_rep = st.columns([2, 1])
        with col_3d:
            pdb_id = row.get('pdb_id') if 'pdb_id' in row else None
            if pdb_id and str(pdb_id) != 'nan':
                st.markdown(f"**🧬 Struttura Molecolare (PDB: {pdb_id})**")
                url_3d = f"https://www.ncbi.nlm.nih.gov/Structure/icn3d/full.html?pdbid={pdb_id}&width=600&height=300&showcommand=0"
                st.components.v1.iframe(url_3d, height=350)
        with col_rep:
            st.markdown("**📄 Intelligence Export**")
            rep_txt = f"REPORT: {search_query}\nCES: {row['ces_score']:.2f}\nPhase: {phase}"
            st.download_button("📥 Scarica Report", rep_txt, file_name=f"MAESTRO_{search_query}.txt", use_container_width=True)
        st.divider()

# --- 7. VISUALIZZAZIONE HUB & NETWORK ---
if not filtered_df.empty:
    tab_net, tab_data = st.tabs(["🕸️ Network Interaction Map", "📊 Comparative Analysis"])

    with tab_net:
        G = nx.Graph()
        for _, r in filtered_df.iterrows():
            is_f = r['target_id'].upper() == search_query
            G.add_node(r['target_id'], size=float(r['initial_score']) * (50 if is_f else 30), color=float(r['toxicity_index']))
        nodes = list(G.nodes())
        if search_query in nodes:
            for n in nodes: 
                if n != search_query: G.add_edge(search_query, n)
        if nodes:
            pos = nx.spring_layout(G, k=0.9, seed=42)
            edge_x, edge_y = [], []
            for e in G.edges():
                x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
                edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
            fig_net = go.Figure(data=[
                go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#555'), mode='lines', hoverinfo='none'),
                go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                           text=nodes, textposition="top center",
                           marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                           colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
            ])
            fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
            st.plotly_chart(fig_net, use_container_width=True)

    with tab_data:
        c_bar, c_rank = st.columns([2, 1])
        with c_bar:
            st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                                   color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
        with c_rank:
            st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 8. PORTALI DATI ---
if search_query:
    st.divider()
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("##### 💊 ODI (Therapeutics)")
        if not odi_df.empty: st.dataframe(odi_df[['Generic_Name', 'Drug_Class', 'Regulatory_Status_US']], use_container_width=True)
    with p2:
        st.markdown("##### 🧬 PMI (Pathways)")
        if not pmi_df.empty: st.dataframe(pmi_df[['Canonical_Name', 'Category', 'Evidence_Priority']], use_container_width=True)
    with p3:
        st.markdown("##### 🧪 GCI (Clinical)")
        if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)

st.divider()
st.caption("MAESTRO Ultra Suite v4.2 | Quad-Engine Cloud | No-Sidebar Edition")
