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
def load_odi_full():
    try:
        # Carichiamo l'intero database ODI per la ricerca flessibile in locale
        res = supabase.table("odi_database").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df_axon = load_axon()
df_odi_all = load_odi_full()

# --- 3. SIDEBAR (CONTROLLI UNIFICATI) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

# A. RICERCA FARMACO (Flessibile)
st.sidebar.subheader("💊 Ricerca Farmaco (Fuzzy)")
drug_input = st.sidebar.text_input("Es: pembro, nivo, trastu", key="drug_search").strip().lower()

# B. LOGICA DI MAPPATURA FARMACO -> TARGET
search_query = ""
found_drug_info = None

if drug_input and not df_odi_all.empty:
    # Cerchiamo nel nome generico o nel brand
    match = df_odi_all[
        df_odi_all['Generic_Name'].str.contains(drug_input, case=False, na=False) | 
        df_odi_all['Brand_Names'].str.contains(drug_input, case=False, na=False)
    ]
    if not match.empty:
        found_drug_info = match.iloc[0]
        st.sidebar.success(f"Trovato: {found_drug_info['Generic_Name']}")
        # Estraiamo il target (es. 'PDCD1 (PD-1)' -> 'PDCD1')
        raw_target = str(found_drug_info['Targets'])
        search_query = raw_target.split('(')[0].split(',')[0].strip().upper()
    else:
        st.sidebar.error("Nessun farmaco trovato.")

# C. RICERCA TARGET DIRETTA (Se non è già stato impostato dal farmaco)
st.sidebar.divider()
st.sidebar.subheader("🔍 Hub Target Focus")
if not search_query:
    search_query = st.sidebar.text_input("Es: KRAS, EGFR, BRCA1", key="target_search").strip().upper()
else:
    st.sidebar.info(f"Target mappato: **{search_query}**")
    if st.sidebar.button("Pulisci ricerca"):
        st.rerun()

min_sig = st.sidebar.slider("Soglia VTG", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite TMI", 0.0, 1.0, 0.8)

# --- 4. LOGICA DI INTELLIGENCE (SATELLITI) ---
gci_df, pmi_df, target_drugs = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if search_query:
    try:
        # Carichiamo Clinica, Pathways e Farmaci per il target specifico
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
        
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        target_drugs = pd.DataFrame(res_odi.data)
    except: pass

    # Filtro Ragnatela
    if not df_axon.empty:
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

# --- 5. DASHBOARD: OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Ultra Suite")

if search_query and not df_axon.empty:
    target_row = df_axon[df_axon['target_id'] == search_query]
    if not target_row.empty:
        row = target_row.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # Grid 10 Campi
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Biomarker)", "DETECTED")
        c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked" if not pmi_df.empty else "ACTIVE")
        c3.metric("ODI (Drug)", "TARGETABLE" if not target_drugs.empty else "NO DRUG")
        c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI (Bio-cost.)", "OPTIMAL")
        c7.metric("GNI (Genetica)", "STABLE")
        c8.metric("EVI (Ambiente)", "LOW RISK")
        c9.metric("MBI (Microbiota)", "RESILIENT")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        c10.metric("GCI (Clinica)", phase)
        st.divider()

# --- 6. RAGNATELA DINAMICA (SOLE-HUB) ---
if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = r['target_id']
        is_f = tid == search_query
        G.add_node(tid, size=float(r['initial_score']) * (60 if is_f else 30), color=float(r['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    
    pos = nx.spring_layout(G, k=1.1, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.2, color='#555'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

# --- 7. DEEP DIVE PORTALS ---
st.divider()
t1, t2, t3 = st.tabs(["💊 Farmaci (ODI)", "🧬 Pathways (PMI)", "🧪 Clinica (GCI)"])

with t1:
    if not target_drugs.empty:
        st.dataframe(target_drugs[['Generic_Name', 'Brand_Names', 'Drug_Class', 'Regulatory_Status_US']], use_container_width=True)
    else: st.info("Nessun farmaco specifico mappato per questo target.")

with t2:
    if not pmi_df.empty:
        for _, p in pmi_df.iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"):
                st.write(f"**Descrizione:** {p['Description_L0']}")
                st.write(f"**Readouts:** {p['Key_Readouts']}")
    else: st.info("Nessun pathway mappato.")

with t3:
    if not gci_df.empty:
        st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)
    else: st.info("Nessun trial clinico trovato.")
