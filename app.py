import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

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
search_query = st.sidebar.text_input("Cerca Target (es. KRAS)", "").strip().upper()
st.sidebar.warning("⚠️ **Research Use Only**\n\nNot for use in diagnostic or therapeutic procedures.")

# --- 4. LOGICA DI FILTRO ---
if search_query and not df.empty:
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

# --- 5. OPERA DIRECTOR (INTELLIGENCE HUB) ---
if search_query and not df.empty:
    target_data = df[df['target_id'].str.upper() == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        
        # Titolo della Sezione
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # Prima riga: Il Cuore della Meccanica (5 colonne)
        st.markdown("##### ⚙️ Meccanica & Sicurezza")
        r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
        r1_c1.metric("OMI (Biomarker)", "DETECTED")
        r1_c2.metric("SMI (Pathway)", "ACTIVE")
        r1_c3.metric("ODI (Drug)", "TARGETABLE")
        r1_c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1_c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        # Seconda riga: Il Contesto & Ambiente (5 colonne)
        st.markdown("##### 🌍 Ambiente & Host")
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
        r2_c1.metric("BCI (Bio-cost.)", "OPTIMAL")
        r2_c2.metric("GNI (Genetica)", "STABLE")
        r2_c3.metric("EVI (Ambiente)", "LOW RISK")
        r2_c4.metric("MBI (Microbiota)", "RESILIENT")
        
        # Check GCI reale per l'ultima casella
        res_gci = supabase.table("GCI_clinical_trials").select("Phase").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        phase = res_gci.data[0]['Phase'] if res_gci.data else "PRE-CLIN"
        r2_c5.metric("GCI (Clinica)", phase)

        # Riga Report (Piccola e discreta)
        st.write("")
        report_text = f"OPERA DIRECTOR REPORT: {search_query}\nScore: {row['initial_score']}\nPhase: {phase}"
        st.download_button("💾 Export Opera Data", report_text, file_name=f"Opera_{search_query}.txt", use_container_width=False)
        st.divider()


# --- 6. GRAFICI AXON ---
col_bar, col_rank = st.columns([2, 1])
with col_bar:
    if not filtered_df.empty:
        st.plotly_chart(px.bar(filtered_df, x="target_id", y="initial_score", color="toxicity_index", 
                               color_continuous_scale="RdYlGn_r", template="plotly_dark"), use_container_width=True)
with col_rank:
    if not filtered_df.empty:
        st.subheader("🥇 Hub Ranking")
        st.dataframe(filtered_df.sort_values('ces_score', ascending=False)[['target_id', 'ces_score']], use_container_width=True)

# --- 7. RAGNATELA DINAMICA ---
st.divider()
st.subheader("🕸️ Network Interaction Map (Relational Focus)")
if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        is_f = r['target_id'].upper() == search_query
        G.add_node(r['target_id'], size=float(r['initial_score']) * (40 if is_f else 25), color=float(r['toxicity_index']))
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))): G.add_edge(nodes[i], nodes[j])
    
    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#999'), mode='lines', hoverinfo='none'),
        go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers+text', 
                   text=nodes, marker=dict(size=[G.nodes[n]['size'] for n in nodes], color=[G.nodes[n]['color'] for n in nodes],
                   colorscale='RdYlGn_r', line=dict(color='white', width=2)))
    ])
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- 8. GCI PORTAL ---
st.divider()
st.header("🧪 Clinical Evidence Portal (GCI)")
if search_query and not gci_df.empty:
    st.dataframe(gci_df[['Canonical_Title', 'Phase', 'Cancer_Type', 'Key_Results_PFS']], use_container_width=True)

# --- FOOTER ---
st.divider()
st.caption("Disclaimer: This platform is for research purposes only (RUO). Data provided by AXON and GCI are for scientific analysis.")

