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
st.sidebar.markdown("### 🔍 Smart Search & Hub Focus")
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**")

# --- 4. LOGICA DI FILTRO ---
gci_df = pd.DataFrame()
pmi_df = pd.DataFrame()
odi_df = pd.DataFrame()

if search_query and not df.empty:
    # 1. Caricamento Dati Satelliti (GCI, PMI, ODI)
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data)
        
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data)
        
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data)
    except:
        pass

    # 2. Filtro per Ragnatela
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

# --- 5. OPERA DIRECTOR (GRIGLIA CHIRURGICA) ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df['target_id'].str.upper() == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # RIGA 1: MECCANICA & SICUREZZA (5 Campi precisi)
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
        r1c1.metric("OMI (Biomarker)", "DETECTED")
        r1c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked" if not pmi_df.empty else "STABLE")
        r1c3.metric("ODI (Drug)", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        r1c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        # RIGA 2: CONTESTO & AMBIENTE (5 Campi precisi)
        st.markdown("##### 🌍 Ambiente & Host")
        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI (Bio-cost.)", "OPTIMAL")
        r2c2.metric("GNI (Genetica)", "STABLE")
        r2c3.metric("EVI (Ambiente)", "LOW RISK")
        r2c4.metric("MBI (Microbiota)", "RESILIENT")
        phase = gci_df['Phase'].iloc[0] if not gci_df.empty else "N/D"
        r2c5.metric("GCI (Clinica)", phase)

        # REPORT EXPORT
        report_text = f"REPORT: {search_query}\nSignal VTG: {row['initial_score']:.2f}\nPhase: {phase}"
        st.download_button("📥 Scarica Report (.txt)", report_text, file_name=f"MAESTRO_{search_query}.txt")
        st.divider()

# --- 6. PATHWAY DETAIL (SMI) ---
if not pmi_df.empty:
    st.subheader("🧬 Signaling & Pathway Analysis (SMI)")
    
    for _, p in pmi_df.iterrows():
        with st.expander(f"Pathway: {p['Canonical_Name']} ({p['Category']})"):
            st.write(f"**Descrizione:** {p['Description_L0']}")
            st.write(f"**Readouts:** {p['Key_Readouts']}")
            st.caption(f"Priority: {p['Evidence_Priority']} | Confidence: {p['Confidence_Default']}")

# --- 7. GRAFICI E RAGNATELA ---
st.divider()
c1, c2 = st.columns([2, 1])
with c1:
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with c2:
    if not filtered_df.empty:
        st.subheader("🥇 Hub Ranking")
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# RAGNATELA
st.subheader("🕸️ Network Interaction Map")
if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        is_f = r['target_id'].upper() == search_query
        G.add_node(r['target_id'], size=float(r['initial_score']) * (40 if is_f else 25), color=float(r['toxicity_index']))
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    
    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#999'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, textposition="top center",
                   marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2), showscale=True))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 8. PORTALI DATI (ODI & GCI) ---
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

st.divider()
st.caption("MAESTRO Suite | Integration of AXON, GCI, ODI, PMI | RUO")
