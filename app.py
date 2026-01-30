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

@st.cache_data(ttl=600)
def load_odi_master():
    try:
        res = supabase.table("odi_database").select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

df = load_axon()
df_odi_master = load_odi_master()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Omni-Search (Target o Farmaco)")
user_input = st.sidebar.text_input("Cerca Target o Farmaco", placeholder="es. KRAS o pembro").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. LOGICA DI MAPPATURA INTELLIGENTE ---
search_query = user_input
found_drug_name = ""

if user_input and not df_odi_master.empty:
    # Controlla se l'input è parte di un nome di farmaco (Fuzzy Search)
    drug_match = df_odi_master[
        df_odi_master['Generic_Name'].str.contains(user_input, case=False, na=False) | 
        df_odi_master['Brand_Names'].str.contains(user_input, case=False, na=False)
    ]
    if not drug_match.empty:
        drug_row = drug_match.iloc[0]
        found_drug_name = drug_row['Generic_Name']
        # Mappa il farmaco sul suo Target principale (pulisce stringhe tipo "PDCD1 (PD-1)")
        search_query = str(drug_row['Targets']).split('(')[0].split(';')[0].strip().upper()
        st.sidebar.success(f"Farmaco: {found_drug_name} ➔ Hub: {search_query}")

# --- 5. CARICAMENTO DATI SATELLITI ---
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
        all_targets = df['target_id'].tolist()
        if search_query in all_targets:
            idx = all_targets.index(search_query)
            neighbor_indices = range(max(0, idx-3), min(len(all_targets), idx+4))
            neighbors = [all_targets[i] for i in neighbor_indices]
            filtered_df = df[df['target_id'].isin(neighbors)]
        else:
            filtered_df = df[df['target_id'].str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df[(df['initial_score'] >= min_sig) & (df['toxicity_index'] <= max_t)] if not df.empty else df

# --- 6. OPERA DIRECTOR (GRIGLIA CHIRURGICA) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
        r1c1.metric("OMI", "DETECTED")
        r1c2.metric("SMI", f"{len(pmi_df)} Linked")
        r1c3.metric("ODI", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        r1c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1c5.metric("CES", f"{row['ces_score']:.2f}")

        st.markdown("##### 🌍 Ambiente & Host")
        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI", "OPTIMAL"); r2c2.metric("GNI", "STABLE"); r2c3.metric("EVI", "LOW RISK"); r2c4.metric("MBI", "RESILIENT")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        r2c5.metric("GCI (Clinica)", phase)
        st.divider()

# --- 7. RAGNATELA DINAMICA CON LINK ---
st.subheader("🕸️ Network Interaction Map")
if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = str(r['target_id'])
        is_f = tid == search_query
        G.add_node(tid, size=float(r['initial_score']) * (60 if is_f else 30), color=float(r['toxicity_index']))
    
    nodes = list(G.nodes())
    if search_query in nodes:
        # Crea i link forzati dal Sole (Search Query) a tutti i satelliti
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    elif len(nodes) > 1:
        # Se non c'è una ricerca specifica, connette i nodi in catena per visibilità
        for i in range(len(nodes)-1): G.add_edge(nodes[i], nodes[i+1])

    pos = nx.spring_layout(G, k=1.0, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        if e[0] in pos and e[1] in pos:
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#888'), mode='lines', hoverinfo='none')
    
    node_x, node_y, node_color, node_size = [], [], [], []
    for n in G.nodes():
        x, y = pos[n]; node_x.append(x); node_y.append(y)
        node_color.append(G.nodes[n]['color']); node_size.append(G.nodes[n]['size'])

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=list(G.nodes()), textposition="top center",
                            marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size, line=dict(color='white', width=2)))

    fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'))
    st.plotly_chart(fig, use_container_width=True)

# --- 8. DATABASE FINALI ---
st.divider()
c_odi, c_pmi, c_gci = st.columns(3)
with c_odi:
    st.markdown("##### 💊 ODI Therapeutics")
    if not odi_df.empty: st.dataframe(odi_df[['Generic_Name', 'Brand_Names', 'Drug_Class']], use_container_width=True)
with c_pmi:
    st.markdown("##### 🧬 PMI Pathways")
    if not pmi_df.empty:
        for _, p in pmi_df.iterrows():
            with st.expander(f"Pathway: {p['Canonical_Name']}"):
                st.write(p.get('Description_L0', 'Dettagli non disponibili'))
with c_gci:
    st.markdown("##### 🧪 GCI Clinical")
    if not gci_df.empty: st.dataframe(gci_df[['Canonical_Title', 'Phase']], use_container_width=True)

st.divider()
st.caption("MAESTRO Suite | Engine v10.0 | RUO")
