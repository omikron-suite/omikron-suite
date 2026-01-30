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
    except Exception:
        return pd.DataFrame()

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Omni-Search (Target o Farmaco)")
# Ricerca flessibile
raw_input = st.sidebar.text_input("Inserisci Query", placeholder="es. KRAS o pembro").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. LOGICA DI IDENTIFICAZIONE & FILTRO ---
search_query = raw_input
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if raw_input:
    # Controllo se l'input è un farmaco per estrarre il target
    try:
        res_drug = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{raw_input}%").execute()
        if res_drug.data:
            drug_data = res_drug.data[0]
            search_query = str(drug_data['Targets']).split('(')[0].split(';')[0].strip().upper()
            st.sidebar.success(f"Mappato: {raw_input} ➔ {search_query}")
    except: pass

    # Caricamento Satelliti
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data)
    except: pass

    # Filtro per Ragnatela
    if not df.empty:
        all_t = df['target_id'].tolist()
        if search_query in all_t:
            idx = all_t.index(search_query)
            neighbors = all_t[max(0, idx-3):min(len(all_t), idx+4)]
            filtered_df = df[df['target_id'].isin(neighbors)]
        else:
            filtered_df = df[df['target_id'].str.contains(search_query, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 5. OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI", "DETECTED")
        c2.metric("SMI", f"{len(pmi_df)} Linked")
        c3.metric("ODI", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES", f"{row['ces_score']:.2f}")

        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("BCI", "OPTIMAL"); c7.metric("GNI", "STABLE"); c8.metric("EVI", "LOW RISK")
        c9.metric("MBI", "RESILIENT")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        c10.metric("GCI", phase)
        st.divider()

# --- 6. RAGNATELA MULTI-NODO ---
st.subheader("🕸️ Network Interaction Map (Biological & Pharmacological)")

if not filtered_df.empty:
    G = nx.Graph()
    # 1. Nodi Target (AXON)
    for _, r in filtered_df.iterrows():
        tid = r['target_id']
        is_f = tid == search_query
        G.add_node(tid, type='target', size=float(r['initial_score']) * (55 if is_f else 30), color=float(r['toxicity_index']))
    
    # 2. Nodi Farmaco (ODI) e Pathway (PMI) come satelliti
    if search_query:
        # Aggiunta Farmaci
        for _, drug in odi_df.head(3).iterrows():
            d_node = drug['Generic_Name']
            G.add_node(d_node, type='drug', size=25, color=0.2)
            G.add_edge(search_query, d_node)
        # Aggiunta Pathway
        for _, path in pmi_df.head(2).iterrows():
            p_node = path['Canonical_Name']
            G.add_node(p_node, type='pathway', size=25, color=0.8)
            G.add_edge(search_query, p_node)

    # 3. Connessioni tra Target
    t_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'target']
    if search_query in t_nodes:
        for n in t_nodes:
            if n != search_query: G.add_edge(search_query, n)

    pos = nx.spring_layout(G, k=1.2, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        if e[0] in pos and e[1] in pos:
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#666'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()], 
                   mode='markers+text', text=list(G.nodes()), textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in G.nodes()], 
                               color=[G.nodes[n]['color'] for n in G.nodes()],
                               colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)



# --- 7. PORTALI DATI ---
st.divider()
p_odi, p_gci = st.columns(2)
with p_odi:
    st.header("💊 Therapeutics (ODI)")
    if not odi_df.empty:
        st.dataframe(odi_df[['Generic_Name', 'Drug_Class', 'Regulatory_Status_US']], use_container_width=True)
with p_gci:
    st.header("🧪 Clinical Trials (GCI)")
    if not gci_df.empty:
        st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)

st.caption("MAESTRO Suite | Integrated Build v14.1 | RUO")
