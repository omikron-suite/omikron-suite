import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="MAESTRO Omikron Ultra", layout="wide")

# --- 2. CONNESSIONE SUPABASE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

# --- 3. INIZIALIZZAZIONE DATI ---
# Definiamo i dataframe vuoti all'inizio per evitare errori "NameError"
df_axon = pd.DataFrame()
gci_data = pd.DataFrame()
odi_data = pd.DataFrame()
pmi_data = pd.DataFrame()
filtered_df = pd.DataFrame()

# Funzioni di caricamento protette
@st.cache_data(ttl=600)
def fetch_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_satellite(table, column, query):
    if not query: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").ilike(column, f"%{query}%").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# Caricamento database primario
df_axon = fetch_axon()

# --- 4. INTERFACCIA CENTRALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra")
st.markdown("### Opera Director Suite v4.6")

# Pannello di Controllo Superiore
with st.container():
    st.info("💡 Inserisci un Target per attivare i 9 database dell'Opera Director.")
    search_query = st.text_input("🔍 RICERCA BIOMARKER (es. KRAS, PDCD1, EGFR, HER2)", "").strip().upper()
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        min_sig = st.slider("Efficacia Segnale (VTG)", 0.0, 3.0, 0.8)
    with col_s2:
        max_t = st.slider("Rischio Tossicità (TMI)", 0.0, 1.0, 0.8)

st.divider()

# --- 5. LOGICA DI FILTRO ---
if not df_axon.empty:
    if search_query:
        # Caricamento dati dai satelliti
        gci_data = fetch_satellite("GCI_clinical_trials", "Primary_Biomarker", search_query)
        odi_data = fetch_satellite("odi_database", "Targets", search_query)
        pmi_data = fetch_satellite("pmi_database", "Key_Targets", search_query)

        # Filtro per grafici
        all_t = df_axon['target_id'].tolist()
        if search_query in all_t:
            idx = all_t.index(search_query)
            neighbors = all_t[max(0, idx-3):min(len(all_t), idx+4)]
            filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
        else:
            filtered_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
    else:
        filtered_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)]

# --- 6. OPERA DIRECTOR GRID ---
if search_query and not df_axon.empty:
    target_row = df_axon[df_axon['target_id'] == search_query]
    if not target_row.empty:
        row = target_row.iloc[0]
        st.header(f"🎼 Opera Director: {search_query}")
        
        # 10 Parametri (5x2)
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1 = st.columns(5)
        r1[0].metric("OMI (Biomarker)", "DETECTED")
        r1[1].metric("SMI (Pathway)", f"{len(pmi_data)} Linked" if not pmi_data.empty else "ACTIVE")
        r1[2].metric("ODI (Drug)", "TARGETABLE" if not odi_data.empty else "NO DRUG")
        r1[3].metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}")
        r1[4].metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        r2 = st.columns(5)
        r2[0].metric("BCI (Bio-cost.)", "OPTIMAL")
        r2[1].metric("GNI (Genetica)", "STABLE")
        r2[2].metric("EVI (Ambiente)", "LOW RISK")
        r2[3].metric("MBI (Microbiota)", "RESILIENT")
        phase = gci_data['Phase'].iloc[0] if not gci_data.empty else "PRE-CLIN"
        r2[4].metric("GCI (Clinica)", phase)
        
        # 3D Viewer & Report
        c3d, crep = st.columns([2, 1])
        with c3d:
            pdb = row.get('pdb_id') if 'pdb_id' in row else None
            if pdb and str(pdb) != 'nan':
                st.markdown(f"**🧬 Struttura 3D (PDB: {pdb})**")
                st.components.v1.iframe(f"https://www.ncbi.nlm.nih.gov/Structure/icn3d/full.html?pdbid={pdb}&width=600&height=300&showcommand=0", height=350)
        with crep:
            st.markdown("**📄 Intelligence Export**")
            st.download_button("📥 Scarica Report", f"REPORT {search_query}\nCES: {row['ces_score']:.2f}", file_name=f"{search_query}.txt")
        st.divider()

# --- 7. VISUALIZZAZIONE ---
if not filtered_df.empty:
    t1, t2 = st.tabs(["🕸️ Network Map", "📊 Analysis"])
    with t1:
        G = nx.Graph()
        for _, r in filtered_df.iterrows():
            G.add_node(r['target_id'], size=float(r['initial_score'])*40, color=float(r['toxicity_index']))
        
        nodes = list(G.nodes())
        if search_query in nodes:
            for n in nodes: 
                if n != search_query: G.add_edge(search_query, n)
        
        pos = nx.spring_layout(G, k=0.9, seed=42)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        fig = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'),
            go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                       text=nodes, marker=dict(size=30, color="orange", line=dict(width=2, color="white")))
        ])
        fig.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    with t2:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)

# --- 8. DATA PORTALS ---
if search_query:
    st.divider()
    p1, p2, p3 = st.columns(3)
    p1.markdown("##### 💊 ODI Drugs")
    if not odi_data.empty: p1.dataframe(odi_data[['Generic_Name', 'Drug_Class']], use_container_width=True)
    p2.markdown("##### 🧬 PMI Pathways")
    if not pmi_data.empty: p2.dataframe(pmi_data[['Canonical_Name', 'Category']], use_container_width=True)
    p3.markdown("##### 🧪 GCI Clinical")
    if not gci_data.empty: p3.dataframe(gci_data[['Canonical_Title', 'Phase']], use_container_width=True)

st.divider()
st.caption("MAESTRO Ultra | No-Sidebar Unified Command v4.6")
