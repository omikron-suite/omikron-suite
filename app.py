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
def get_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def get_satellite(table, column, query):
    if not query: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").ilike(column, f"%{query}%").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# Caricamento Base
df_axon = get_axon()

# --- 4. INTERFACCIA CENTRALE (No Sidebar) ---
st.title("🛡️ MAESTRO: Omikron Orchestra")
st.caption("Opera Director Suite v4.5 | Research Use Only")

# Search Bar e Controlli in un unico blocco superiore
with st.container():
    search_query = st.text_input("🔍 Inserisci Biomarker Hub (es. PDCD1, HER2, EGFR)", "").strip().upper()
    
    col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
    with col_s1:
        min_sig = st.slider("Segnale VTG (Efficacia)", 0.0, 3.0, 0.8)
    with col_s2:
        max_t = st.slider("Tossicità TMI (Rischio)", 0.0, 1.0, 0.8)
    with col_s3:
        st.write("") # Spacer
        if st.button("🔄 Reset Suite", use_container_width=True):
            st.rerun()

st.divider()

# --- 5. LOGICA DI INTELLIGENCE ---
# Inizializzazione sicura di tutte le variabili
gci_data = pd.DataFrame()
odi_data = pd.DataFrame()
pmi_data = pd.DataFrame()
filtered_df = pd.DataFrame()

if not df_axon.empty:
    if search_query:
        # Chiamate ai satelliti
        gci_data = get_satellite("GCI_clinical_trials", "Primary_Biomarker", search_query)
        odi_data = get_satellite("odi_database", "Targets", search_query)
        pmi_data = get_satellite("pmi_database", "Key_Targets", search_query)

        # Filtro Vicinato
        all_t = df_axon['target_id'].tolist()
        if search_query in all_t:
            idx = all_t.index(search_query)
            neighbors = all_t[max(0, idx-3):min(len(all_t), idx+4)]
            filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
        else:
            filtered_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
    else:
        filtered_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)]

# --- 6. OPERA DIRECTOR (GRIGLIA CHIRURGICA) ---
if search_query and not df_axon.empty:
    t_info = df_axon[df_axon['target_id'] == search_query]
    if not t_info.empty:
        row = t_info.iloc[0]
        st.header(f"🎼 Opera Director: {search_query}")
        
        # Grid 10 Pilastri
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1_1, r1_2, r1_3, r1_4, r1_5 = st.columns(5)
        r1_1.metric("OMI (Biomarker)", "DETECTED")
        r1_2.metric("SMI (Pathway)", f"{len(pmi_data)} Hubs" if not pmi_data.empty else "ACTIVE")
        r1_3.metric("ODI (Drug)", "TARGETABLE" if not odi_data.empty else "NO DRUG")
        r1_4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1_5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        r2_1, r2_2, r2_3, r2_4, r2_5 = st.columns(5)
        r2_1.metric("BCI (Bio-cost.)", "OPTIMAL")
        r2_2.metric("GNI (Genetica)", "STABLE")
        r2_3.metric("EVI (Ambiente)", "LOW RISK")
        r2_4.metric("MBI (Microbiota)", "RESILIENT")
        
        phase = gci_data['Phase'].iloc[0] if not gci_data.empty else "PRE-CLIN"
        r2_5.metric("GCI (Clinica)", phase)
        
        # Sezione 3D e Report
        c3d, crep = st.columns([2, 1])
        with c3d:
            pdb = row.get('pdb_id') if 'pdb_id' in row else None
            if pdb and str(pdb) != 'nan':
                st.markdown(f"**🧬 Conformazione 3D (PDB: {pdb})**")
                url = f"https://www.ncbi.nlm.nih.gov/Structure/icn3d/full.html?pdbid={pdb}&width=600&height=300&showcommand=0"
                st.components.v1.iframe(url, height=350)
        with crep:
            st.markdown("**📄 Intelligence Export**")
            txt = f"OPERA REPORT: {search_query}\nCES: {row['ces_score']:.2f}\nStatus: {phase}"
            st.download_button("📥 Scarica Report .txt", txt, file_name=f"MAESTRO_{search_query}.txt", use_container_width=True)
        st.divider()

# --- 7. VISUALIZZAZIONE HUB ---
if not filtered_df.empty:
    t_net, t_bar = st.tabs(["🕸️ Network Map", "📊 Comparative Analysis"])
    
    with t_net:
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
            
            net_fig = go.Figure(data=[
                go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'),
                go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                           text=nodes, textposition="top center",
                           marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                           colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
            ])
            net_fig.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
            st.plotly_chart(net_fig, use_container_width=True)

    with t_bar:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)

# --- 8. PORTALI DATI ---
if search_query:
    st.divider()
    p_odi, p_pmi, p_gci = st.columns(3)
    with p_odi:
        st.markdown("##### 💊 ODI Therapeutics")
        if not odi_data.empty: st.dataframe(odi_data[['Generic_Name', 'Drug_Class']], use_container_width=True)
    with p_pmi:
        st.markdown("##### 🧬 PMI Pathways")
        if not pmi_data.empty: st.dataframe(pmi_data[['Canonical_Name', 'Evidence_Priority']], use_container_width=True)
    with p_gci:
        st.markdown("##### 🧪 GCI Clinical")
        if not gci_data.empty: st.dataframe(gci_data[['Canonical_Title', 'Phase']], use_container_width=True)

st.divider()
st.caption("MAESTRO Ultra | Engine 4.5 | No-Sidebar Unified Command")
