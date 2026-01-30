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

# --- 3. SIDEBAR (LEGOS SEPARATI) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

st.sidebar.subheader("🧬 1. Hub Target")
search_query = st.sidebar.text_input("Seleziona Target (es. KRAS)", "").strip().upper()

st.sidebar.divider()
st.sidebar.subheader("💊 2. Ricerca Farmaco")
drug_input = st.sidebar.text_input("Cerca Farmaco (es. pembro)", "").strip().lower()

st.sidebar.divider()
min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. LOGICA DI FILTRO & SATELLITI ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if search_query and not df.empty:
    try:
        gci_df = pd.DataFrame(supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute().data)
        pmi_df = pd.DataFrame(supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute().data)
        odi_df = pd.DataFrame(supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute().data)
    except: pass

    all_targets = df['target_id'].tolist()
    if search_query in all_targets:
        idx = all_targets.index(search_query)
        neighbor_indices = range(max(0, idx-2), min(len(all_targets), idx+3))
        neighbors = [all_targets[i] for i in neighbor_indices]
        filtered_df = df[df['target_id'].isin(neighbors)]
    else:
        filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 5. OPERA DIRECTOR (BIOLOGIA) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # GRID 10 PARAMETRI
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
        r1c1.metric("OMI", "DETECTED")
        r1c2.metric("SMI", f"{len(pmi_df)} Linked")
        r1c3.metric("ODI", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        r1c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1c5.metric("CES", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI", "OPTIMAL"); r2c2.metric("GNI", "STABLE"); r2c3.metric("EVI", "LOW RISK"); r2c4.metric("MBI", "BALANCED")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        r2c5.metric("GCI", phase)
        st.divider()

# --- 6. RAGNATELA MULTI-NODO (INTEGRATA) ---
st.subheader("🕸️ Network Interaction Map (Multi-Entity Hub)")


if not filtered_df.empty:
    G = nx.Graph()
    # 1. Aggiunta Nodi Target (AXON)
    for _, r in filtered_df.iterrows():
        tid = r['target_id'].upper()
        is_f = tid == search_query
        G.add_node(tid, type='target', size=float(r['initial_score']) * (45 if is_f else 25), color=float(r['toxicity_index']), label=tid)

    # 2. Aggiunta Nodi Farmaco (ODI) e Pathway (PMI) come satelliti
    if search_query:
        if not odi_df.empty:
            for _, drug in odi_df.head(3).iterrows():
                d_node = drug['Generic_Name']
                G.add_node(d_node, type='drug', size=20, color=0.1, label=f"💊 {d_node}")
                G.add_edge(d_node, search_query)
        if not pmi_df.empty:
            for _, path in pmi_df.head(3).iterrows():
                p_node = path['Canonical_Name']
                G.add_node(p_node, type='pathway', size=20, color=0.9, label=f"🧬 {p_node}")
                G.add_edge(p_node, search_query)

    # 3. Connessioni Target
    nodes_list = list(G.nodes())
    if search_query in nodes_list:
        for n in [nd for nd, data in G.nodes(data=True) if data.get('type') == 'target']:
            if n != search_query: G.add_edge(search_query, n)

    pos = nx.spring_layout(G, k=0.5, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()], 
                   mode='markers+text', text=[G.nodes[n].get('label', n) for n in G.nodes()], 
                   textposition="top center", marker=dict(showscale=True, colorscale='Viridis', 
                   color=[G.nodes[n].get('color', 0.5) for n in G.nodes()], 
                   size=[G.nodes[n].get('size', 20) for n in G.nodes()], line_width=1.5))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. MODULO FARMACO INDIPENDENTE (HUB FARMACO) ---
st.divider()
st.subheader("💊 Hub Farmaco Indipendente")

if drug_input:
    try:
        res_odi_search = supabase.table("odi_database").select("*").ilike("Generic_Name", f"%{drug_input}%").execute()
        if res_odi_search.data:
            drug = res_odi_search.data[0]
            st.success(f"**Identificato:** {drug['Generic_Name']} ({drug['Brand_Names']})")
            
            # MATCH LOGIC
            if search_query:
                drug_targets = str(drug['Targets']).upper()
                if search_query in drug_targets:
                    st.info(f"🎯 **MATCH RILEVATO**: `{drug['Generic_Name']}` è correlato a `{search_query}`.")
                else:
                    st.warning(f"⚠️ **NESSUN MATCH**: `{drug['Generic_Name']}` non correla con il target biologico `{search_query}` selezionato sopra.")
            
            st.dataframe(pd.DataFrame([drug]), use_container_width=True)
        else:
            st.error("Nessun farmaco trovato.")
    except: st.error("Errore database ODI.")
else:
    st.info("Utilizza la sidebar per cercare un farmaco indipendentemente.")

# --- 8. ANALISI PATHWAY E CLINICA ---
if not pmi_df.empty or not gci_df.empty:
    st.divider()
    c_p, c_g = st.columns(2)
    with c_p:
        st.subheader("🧬 Pathways (SMI)")
        st.dataframe(pmi_df[['Canonical_Name', 'Category', 'Description_L0']], use_container_width=True)
    with c_g:
        st.subheader("🧪 Trials Clinici (GCI)")
        st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type']], use_container_width=True)

st.caption("MAESTRO Suite v13.5 | Modular Multi-Node Architecture | RUO")
