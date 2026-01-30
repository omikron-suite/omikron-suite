import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- 2. CONNESSIONE ---
URL = "https://zwpahhbxcugldxchiunv.supabase.co"
KEY = "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# Carichiamo i motori principali
df_axon = load_data("axon_knowledge")
df_odi = load_data("odi_database")

if not df_axon.empty:
    df_axon['target_id'] = df_axon['target_id'].str.strip().upper()
    df_axon['ces_score'] = df_axon['initial_score'] * (1 - df_axon['toxicity_index'])

# --- 3. SIDEBAR: COMANDI UNIFICATI ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Opera Control Center")

# A. RICERCA FARMACO FLESSIBILE
st.sidebar.markdown("### 💊 Ricerca Farmaco (Fuzzy)")
drug_input = st.sidebar.text_input("Es: pembro, nivo, trastu", "").strip().lower()

search_query = ""
found_drug = None

if drug_input and not df_odi.empty:
    # Cerca nel nome o brand
    matches = df_odi[df_odi['Generic_Name'].str.contains(drug_input, case=False, na=False) | 
                    df_odi['Brand_Names'].str.contains(drug_input, case=False, na=False)]
    if not matches.empty:
        found_drug = matches.iloc[0]
        st.sidebar.success(f"Farmaco: {found_drug['Generic_Name']}")
        # Estraiamo il target pulito (es. PDCD1 da "PDCD1 (PD-1)")
        search_query = str(found_drug['Targets']).split('(')[0].split(';')[0].split('/')[0].strip().upper()
    else:
        st.sidebar.error("Farmaco non trovato")

# B. RICERCA TARGET (Se non impostato dal farmaco)
st.sidebar.divider()
st.sidebar.markdown("### 🔍 Hub Target")
manual_target = st.sidebar.text_input("Es: KRAS, EGFR", "").strip().upper()

if manual_target:
    search_query = manual_target

if search_query:
    st.sidebar.info(f"Focus Attivo: **{search_query}**")

min_sig = st.sidebar.slider("Soglia VTG", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite TMI", 0.0, 1.0, 0.8)

# --- 4. LOGICA DI SINCRONIZZAZIONE (AXON, GCI, PMI) ---
gci_df, pmi_df, filtered_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query:
    # 1. Caricamento satelliti in tempo reale
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
    except: pass

    # 2. Filtro Hub e Vicinato per Ragnatela
    if not df_axon.empty:
        all_ids = df_axon['target_id'].tolist()
        if search_query in all_ids:
            idx = all_ids.index(search_query)
            neighbors = all_ids[max(0, idx-3):min(len(all_ids), idx+4)]
            filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
        else:
            filtered_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
else:
    if not df_axon.empty:
        filtered_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)]

# --- 5. OPERA DIRECTOR (GRIGLIA CHIRURGICA) ---
st.title("🛡️ MAESTRO: Omikron Orchestra")

if search_query and not df_axon.empty:
    target_row = df_axon[df_axon['target_id'] == search_query]
    if not target_row.empty:
        r = target_row.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # Grid 10 Campi
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Biomarker)", "DETECTED")
        c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked" if not pmi_df.empty else "ACTIVE")
        c3.metric("ODI (Drug)", "TARGETABLE" if found_drug is not None or not df_odi[df_odi['Targets'].str.contains(search_query, na=False)].empty else "NO DRUG")
        c4.metric("TMI (Tossicità)", f"{r['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES (Efficiency)", f"{r['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI (Bio-cost.)", "OPTIMAL")
        c7.metric("GNI (Genetica)", "STABLE")
        c8.metric("EVI (Ambiente)", "LOW RISK")
        c9.metric("MBI (Microbiota)", "RESILIENT")
        c10.metric("GCI (Clinica)", gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D")
        st.divider()

# --- 6. RAGNATELA DINAMICA (SOLE-HUB) ---
if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        tid = row['target_id']
        is_f = tid == search_query
        G.add_node(tid, size=float(row['initial_score']) * (55 if is_f else 30), color=float(row['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    
    pos = nx.spring_layout(G, k=1.0, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#666'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

# --- 7. DEEP DIVE TABS ---
st.divider()
t1, t2, t3 = st.tabs(["💊 Farmaci (ODI)", "🧬 Pathways (SMI)", "🧪 Clinica (GCI)"])
with t1:
    # Mostra i farmaci che colpiscono questo target
    target_drugs = df_odi[df_odi['Targets'].str.contains(search_query, case=False, na=False)] if search_query else pd.DataFrame()
    if not target_drugs.empty: st.dataframe(target_drugs[['Generic_Name', 'Brand_Names', 'Drug_Class']], use_container_width=True)
    else: st.info("Seleziona un target o un farmaco per visualizzare le terapie.")
with t2:
    if not pmi_df.empty:
        for _, p in pmi_df.iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"):
                st.write(f"**Descrizione:** {p['Description_L0']}")
                st.caption(f"Priority: {p['Evidence_Priority']}")
    else: st.info("Nessun pathway mappato.")
with t3:
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)
    else: st.info("Nessun trial trovato.")
