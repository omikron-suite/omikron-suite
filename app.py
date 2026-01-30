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
def load_base_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

df_axon = load_base_data("axon_knowledge")
df_odi = load_base_data("odi_database") # Carichiamo ODI per la ricerca flessibile

# Pulizia minima
if not df_axon.empty:
    df_axon['target_id'] = df_axon['target_id'].str.strip().upper()
    df_axon['ces_score'] = df_axon['initial_score'] * (1 - df_axon['toxicity_index'])

# --- 3. SIDEBAR: RICERCA DOPPIA ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

# --- RICERCA FARMACI FLESSIBILE ---
st.sidebar.markdown("### 💊 Ricerca Farmaco (Fuzzy)")
drug_input = st.sidebar.text_input("Inserisci Farmaco (es. pembro, nivo)", "").strip().lower()

selected_drug_row = pd.DataFrame()
search_query = ""

if drug_input and not df_odi.empty:
    # Filtro flessibile: cerca se l'input è contenuto nel nome generico o nei brand
    match_odi = df_odi[
        df_odi['Generic_Name'].str.contains(drug_input, case=False, na=False) | 
        df_odi['Brand_Names'].str.contains(drug_input, case=False, na=False)
    ]
    
    if not match_odi.empty:
        # Se ci sono più match, prendiamo il primo o mostriamo una selezione
        selected_drug_row = match_odi.iloc[0]
        st.sidebar.success(f"Trovato: {selected_drug_row['Generic_Name']}")
        # Estraiamo il target principale dal farmaco per mappare la ragnatela
        search_query = str(selected_drug_row['Targets']).split('(')[0].strip().upper()
    else:
        st.sidebar.error("Nessun farmaco trovato.")

st.sidebar.divider()

# --- RICERCA TARGET DIRETTA ---
st.sidebar.markdown("### 🔍 Hub Focus")
if not search_query: # Se non abbiamo cercato un farmaco, usiamo il box target
    search_query = st.sidebar.text_input("Cerca Target (es. KRAS)", "").strip().upper()
else:
    st.sidebar.info(f"Target mappato: {search_query}")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

# --- 4. LOGICA DI INTELLIGENCE ---
gci_df, pmi_df = pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if search_query and not df_axon.empty:
    # Caricamento satelliti basato sul target (derivato o diretto)
    res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
    gci_df = pd.DataFrame(res_gci.data)
    
    res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
    pmi_df = pd.DataFrame(res_pmi.data)

    # Filtro ragnatela
    all_targets = df_axon['target_id'].tolist()
    if search_query in all_targets:
        idx = all_targets.index(search_query)
        neighbor_indices = range(max(0, idx-2), min(len(all_targets), idx+3))
        neighbors = [all_targets[i] for i in neighbor_indices]
        filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
    else:
        filtered_df = df_axon[df_axon['target_id'].str.contains(search_query, na=False)]
else:
    filtered_df = df_axon[(df_axon['initial_score'] >= min_sig) & (df_axon['toxicity_index'] <= max_t)] if not df_axon.empty else pd.DataFrame()

# --- 5. DASHBOARD HEADER ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if not selected_drug_row.empty:
    st.info(f"🧬 **Focus Farmaco:** {selected_drug_row['Generic_Name']} ({selected_drug_row['Brand_Names']}) | **Classe:** {selected_drug_row['Drug_Class']}")

# --- 6. OPERA DIRECTOR GRID ---
if search_query and not df_axon.empty:
    target_data = df_axon[df_axon['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"### 🎼 Opera Director: {search_query}")
        
        c_r1 = st.columns(5)
        c_r1[0].metric("OMI", "DETECTED")
        c_r1[1].metric("SMI", f"{len(pmi_df)} Path")
        c_r1[2].metric("ODI", "YES" if not selected_drug_row.empty else "NO")
        c_r1[3].metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c_r1[4].metric("CES", f"{row['ces_score']:.2f}")
        st.divider()

# --- 7. RAGNATELA DINAMICA ---
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
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#666'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

# --- 8. PORTALI DATI ---
st.divider()
p1, p2 = st.columns(2)
with p1:
    st.header("🧪 Clinical Trials (GCI)")
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)
with p2:
    st.header("🧬 Pathways (SMI)")
    if not pmi_df.empty: st.dataframe(pmi_df[['Canonical_Name', 'Category', 'Evidence_Priority']], use_container_width=True)

st.caption("MAESTRO Suite v4.9 | Powered by Omikron Logic")
