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

df = load_axon()
df_odi_full = load_odi_all()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Omni-Search (Target o Farmaco)")
user_input = st.sidebar.text_input("Es: pembro o KRAS", "").strip().upper()

# --- 4. LOGICA DI MAPPATURA (Pembro -> PDCD1) ---
search_query = user_input
if user_input and not df_odi_full.empty:
    matches = df_odi_full[df_odi_full['Generic_Name'].str.contains(user_input, case=False, na=False) | 
                         df_odi_full['Brand_Names'].str.contains(user_input, case=False, na=False)]
    if not matches.empty:
        drug_row = matches.iloc[0]
        # Estrae il primo target utile pulito
        search_query = str(drug_row['Targets']).split('(')[0].split(';')[0].strip().upper()
        st.sidebar.success(f"Farmaco: {drug_row['Generic_Name']} ➔ Hub: {search_query}")

# --- 5. QUERY SATELLITI ---
gci_df, pmi_df, odi_df, filtered_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data)
    except: pass

    if not df.empty:
        all_t = df['target_id'].tolist()
        if search_query in all_t:
            idx = all_targets = all_t.index(search_query)
            neighbors = all_t[max(0, idx-3):min(len(all_t), idx+4)]
            filtered_df = df[df['target_id'].isin(neighbors)]
        else:
            filtered_df = df[df['target_id'].str.contains(search_query, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 6. OPERA DIRECTOR (GRIGLIA 10 CAMPI) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # RIGA 1
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
        r1c1.metric("OMI", "DETECTED")
        r1c2.metric("SMI", f"{len(pmi_df)} Path")
        r1c3.metric("ODI", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        r1c4.metric("TMI (Tox)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1c5.metric("CES", f"{row['ces_score']:.2f}")

        # RIGA 2
        st.markdown("##### 🌍 Ambiente & Host")
        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI", "OPTIMAL"); r2c2.metric("GNI", "STABLE"); r2c3.metric("EVI", "LOW RISK"); r2c4.metric("MBI", "RESILIENT")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        r2c5.metric("GCI", phase)
        st.divider()

# --- 7. RAGNATELA CON LINK (FIXED) ---
st.subheader("🕸️ Network Interaction Map")

if not filtered_df.empty:
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
        for i in range(len(nodes)-1): G.add_edge(nodes[i], nodes[i+1])

    pos = nx.spring_layout(G, k=1.0, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#777'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()], 
                   mode='markers+text', text=list(G.nodes()), textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], color=[G.nodes[n]['color'] for n in G.nodes()],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

# --- 8. DATABASE FINALI ---
st.divider()
p_odi, p_pmi, p_gci = st.columns(3)
with p_odi:
    st.markdown("##### 💊 ODI Therapeutics")
    if not odi_df.empty: st.dataframe(odi_df[['Generic_Name', 'Drug_Class']], use_container_width=True)
with p_pmi:
    st.markdown("##### 🧬 PMI Pathways")
    if not pmi_df.empty: st.dataframe(pmi_df[['Canonical_Name', 'Category']], use_container_width=True)
with p_gci:
    st.markdown("##### 🧪 GCI Clinical")
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase']], use_container_width=True)

st.caption("MAESTRO Suite | Omni-Engine | RUO")
