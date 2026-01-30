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

df_axon = load_data("axon_knowledge")
df_odi_all = load_data("odi_database")

if not df_axon.empty:
    df_axon['target_id'] = df_axon['target_id'].astype(str).str.strip().upper()
    df_axon['ces_score'] = df_axon['initial_score'] * (1 - df_axon['toxicity_index'])

# --- 3. SIDEBAR: COMANDI (NUOVO ORDINE) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Opera Control Center")

# A. HUB FOCUS (SOPRA)
st.sidebar.markdown("### 🔍 Hub Focus")
target_input = st.sidebar.text_input("Cerca Target (es. KRAS, PDCD1)", "").strip().upper()

# B. RICERCA FARMACO (SOTTO)
st.sidebar.markdown("### 💊 Ricerca Farmaco (Fuzzy)")
drug_input = st.sidebar.text_input("Es: pembro, nivo, trastu", "").strip().lower()

search_query = target_input
found_drug_name = ""

# Se viene inserito un farmaco e il campo target è vuoto, il farmaco comanda il target
if drug_input and not df_odi_all.empty:
    matches = df_odi_all[
        df_odi_all['Generic_Name'].str.contains(drug_input, case=False, na=False) | 
        df_odi_all['Brand_Names'].str.contains(drug_input, case=False, na=False)
    ]
    if not matches.empty:
        drug_row = matches.iloc[0]
        found_drug_name = drug_row['Generic_Name']
        # Estraiamo il target dal farmaco solo se non abbiamo inserito un target manuale
        if not target_input:
            search_query = str(drug_row['Targets']).split('(')[0].split(';')[0].split('/')[0].strip().upper()
            st.sidebar.success(f"Farmaco: {found_drug_name} ➔ Target: {search_query}")
        else:
            st.sidebar.info(f"Farmaco trovato: {found_drug_name}")
    else:
        st.sidebar.error("Nessun farmaco trovato.")

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

# --- 4. LOGICA DI FILTRO & QUERY ---
gci_df, pmi_df, filtered_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query:
    try:
        # Caricamento satelliti
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
    except: pass

    # Popolamento filtered_df per ragnatela
    if not df_axon.empty:
        all_ids = df_axon['target_id'].tolist()
        if search_query in all_ids:
            idx = all_ids.index(search_query)
            # Prende il target e i vicini per creare il contesto
            neighbors = all_ids[max(0, idx-3):min(len(all_ids), idx+4)]
            filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
        else:
            filtered_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
            # Se ancora vuoto, aggiungiamo forzatamente almeno il target se esiste
            if filtered_df.empty and search_query in df_axon['target_id'].values:
                filtered_df = df_axon[df_axon['target_id'] == search_query]
else:
    if not df_axon.empty:
        filtered_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)]

# --- 5. OPERA DIRECTOR GRID ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df_axon.empty:
    target_data = df_axon[df_axon['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked" if not pmi_df.empty else "ACTIVE")
        
        # Check ODI dinamico
        has_drug = not df_odi_all[df_odi_all['Targets'].str.contains(search_query, case=False, na=False)].empty if not df_odi_all.empty else False
        c3.metric("ODI (Drug)", "TARGETABLE" if has_drug else "NO DRUG")
        
        c4.metric("TMI (Tox)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 6. RAGNATELA DINAMICA (SOLE-HUB) ---
if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = str(r['target_id'])
        is_f = tid == search_query
        G.add_node(tid, size=float(r['initial_score']) * (60 if is_f else 30), color=float(r['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    elif len(nodes) > 1:
        # Se il target non è nei nodi, connettiamo i nodi tra loro per visibilità
        for i in range(len(nodes)-1): G.add_edge(nodes[i], nodes[i+1])
    
    pos = nx.spring_layout(G, k=1.0, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        if e[0] in pos and e[1] in pos:
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#777'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. DEEP DIVE TABS ---
st.divider()
t1, t2, t3 = st.tabs(["💊 Farmaci (ODI)", "🧬 Pathways (SMI)", "🧪 Clinica (GCI)"])

with t1:
    if search_query and not df_odi_all.empty:
        target_drugs = df_odi_all[df_odi_all['Targets'].str.contains(search_query, case=False, na=False)]
        st.dataframe(target_drugs[['Generic_Name', 'Brand_Names', 'Drug_Class']] if not target_drugs.empty else pd.DataFrame(), use_container_width=True)
with t2:
    if not pmi_df.empty:
        for _, p in pmi_df.iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"):
                st.write(f"**Descrizione:** {p['Description_L0']}")
                st.caption(f"Priority: {p['Evidence_Priority']} | Readouts: {p['Key_Readouts']}")
with t3:
    if not gci_df.empty:
        st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)

st.caption("MAESTRO Suite v6.1 | RUO")
