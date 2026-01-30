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
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data)
        if not d.empty:
            d['target_id'] = d['target_id'].astype(str).str.strip().upper()
            d['ces_score'] = d['initial_score'] * (1 - d['toxicity_index'])
        return d
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_odi_all():
    try:
        res = supabase.table("odi_database").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df_axon = load_axon()
df_odi = load_odi_all()

# --- 3. SIDEBAR: RICERCHE PARCELLIZZATE ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("MAESTRO Control")

st.sidebar.markdown("### 🧬 1. Hub Focus (Target)")
t_search = st.sidebar.text_input("Inserisci Gene/Hub (es. KRAS)", "").strip().upper()

st.sidebar.markdown("### 💊 2. Drug Focus (Farmaco)")
d_search = st.sidebar.text_input("Inserisci Farmaco (es. pembro)", "").strip().lower()

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia Segnale VTG", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità TMI", 0.0, 1.0, 0.8)

# --- 4. LOGICA INDIPENDENTE ---
# A. Dati Target
gci_df, pmi_df, filtered_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if t_search:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{t_search}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{t_search}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
    except: pass
    
    if not df_axon.empty:
        all_ids = df_axon['target_id'].tolist()
        if t_search in all_ids:
            idx = all_ids.index(t_search)
            neighbors = all_ids[max(0, idx-3):min(len(all_ids), idx+4)]
            filtered_df = df_axon[df_axon['target_id'].isin(neighbors)]
        else:
            filtered_df = df_axon[df_axon['target_id'].str.contains(t_search, na=False)]

# B. Dati Farmaco
selected_drug = pd.DataFrame()
if d_search and not df_odi.empty:
    selected_drug = df_odi[df_odi['Generic_Name'].str.contains(d_search, case=False, na=False) | 
                           df_odi['Brand_Names'].str.contains(d_search, case=False, na=False)]

# --- 5. DASHBOARD: OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if t_search and not df_axon.empty:
    t_row = df_axon[df_axon['target_id'] == t_search]
    if not t_row.empty:
        r = t_row.iloc[0]
        st.header(f"🎼 Opera Director: {t_search}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Path")
        c3.metric("ODI", "TARGETABLE" if not df_odi[df_odi['Targets'].str.contains(t_search, na=False)].empty else "NO DRUG")
        c4.metric("TMI", f"{r['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{r['ces_score']:.2f}")
        st.divider()

# --- 6. 🪟 FINESTRA HUB-FARMACO (CORRELAZIONE) ---
st.subheader("🔗 Hub-Drug Correlation Linker")
if t_search and not selected_drug.empty:
    drug_r = selected_drug.iloc[0]
    drug_targets = str(drug_r['Targets']).upper()
    
    col_link1, col_link2 = st.columns([1, 2])
    if t_search in drug_targets:
        col_link1.success("✅ CORRELAZIONE RILEVATA")
        col_link2.info(f"Il farmaco **{drug_r['Generic_Name']}** agisce direttamente su **{t_search}**.\n\n**Meccanismo:** {drug_r.get('Mechanism_Short', 'N/D')}")
    else:
        col_link1.warning("⚠️ NESSUNA CORRELAZIONE DIRETTA")
        col_link2.write(f"Il farmaco **{drug_r['Generic_Name']}** colpisce: `{drug_r['Targets']}`. Non ci sono evidenze dirette per **{t_search}** in questo database.")
elif t_search or not selected_drug.empty:
    st.info("Inserisci sia un Target che un Farmaco per analizzare la correlazione.")
st.divider()

# --- 7. RAGNATELA DINAMICA (SOLE-HUB) ---
if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        tid = row['target_id']
        is_f = tid == t_search
        G.add_node(tid, size=float(row['initial_score']) * (60 if is_f else 30), color=float(row['toxicity_index']))
    
    nodes = list(G.nodes())
    if t_search in nodes:
        for n in nodes:
            if n != t_search: G.add_edge(t_search, n)
    
    pos = nx.spring_layout(G, k=1.0, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
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

# --- 8. DATABASE DEEP DIVE ---
st.divider()
tab1, tab2, tab3 = st.tabs(["💊 Scheda Farmaco (ODI)", "🧬 Pathways (SMI)", "🧪 Clinica (GCI)"])
with tab1:
    if not selected_drug.empty: st.dataframe(selected_drug, use_container_width=True)
with tab2:
    if not pmi_df.empty: st.dataframe(pmi_df[['Canonical_Name', 'Category', 'Description_L0']], use_container_width=True)
with tab3:
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)

st.caption("MAESTRO Suite v7.0 | Modular Intelligence")
