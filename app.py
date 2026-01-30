import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite v19.2", layout="wide")

# --- 2. CONNESSIONE ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty: return d
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0).clip(0.0, 1.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("Versione 19.2.1 | Stable")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Cerca Target", placeholder="es. KRAS").strip().upper()

# --- 4. LOGICA DATI ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if search_query and not df.empty:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except: pass

# --- 5. UI PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

# Badge di Classe (Indicatori Database)
if search_query:
    b1, b2, b3, b4 = st.columns([1,1,1,2])
    b1.markdown(f"""<div style="background:#b8860b;padding:10px;border-radius:10px;text-align:center;">
                <span style="font-size:0.8rem;color:white;">💊 ODI DRUGS</span><br>
                <span style="font-size:1.5rem;font-weight:bold;color:white;">{len(odi_df)}</span></div>""", unsafe_allow_html=True)
    b2.markdown(f"""<div style="background:#4b0082;padding:10px;border-radius:10px;text-align:center;">
                <span style="font-size:0.8rem;color:white;">🧬 PMI PATHS</span><br>
                <span style="font-size:1.5rem;font-weight:bold;color:white;">{len(pmi_df)}</span></div>""", unsafe_allow_html=True)
    b3.markdown(f"""<div style="background:#2e8b57;padding:10px;border-radius:10px;text-align:center;">
                <span style="font-size:0.8rem;color:white;">🧪 GCI TRIALS</span><br>
                <span style="font-size:1.5rem;font-weight:bold;color:white;">{len(gci_df)}</span></div>""", unsafe_allow_html=True)

# Opera Director Metrics
if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("OMI", "DETECTED", help="Segnale Biomarcatore AXON")
        m2.metric("SMI", f"{len(pmi_df)}", help="Connessioni Pathway PMI")
        m3.metric("ODI", f"{len(odi_df)}", help="Farmaci disponibili ODI")
        m4.metric("TMI", f"{row['toxicity_index']:.2f}", help="Indice Tossicità")
        m5.metric("CES", f"{row['ces_score']:.2f}", help="Combined Efficiency Score")
        
        # Download Report
        report_txt = f"MAESTRO REPORT - {search_query}\nScore: {row['ces_score']}\nDrugs: {len(odi_df)}"
        st.download_button("📥 TXT Report", report_txt, file_name=f"{search_query}_report.txt")
        st.divider()

# --- 6. GRAFICI ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("🕸️ Network Interaction Map")
    # Filtro per ragnatela
    filtered_df = df[df["target_id"].str.contains(search_query, na=False)] if search_query else df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]
    
    if not filtered_df.empty:
        G = nx.Graph()
        for _, r in filtered_df.iterrows():
            tid = r["target_id"]
            G.add_node(tid, size=float(r["initial_score"]) * (50 if tid == search_query else 30), color=float(r["toxicity_index"]))
        nodes = list(G.nodes())
        if search_query in nodes:
            for n in nodes:
                if n != search_query: G.add_edge(search_query, n)
        
        pos = nx.spring_layout(G, k=1.2, seed=42)
        edge_x, edge_y = [], []
        for a, b in G.edges():
            x0, y0 = pos[a]; x1, y1 = pos[b]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color='#444', width=1), hoverinfo="none"))
        fig_net.add_trace(go.Scatter(
            x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
            mode="markers+text", text=nodes, textposition="top center",
            textfont=dict(size=9, color="white"),
            marker=dict(size=[G.nodes[n]["size"] for n in nodes], color=[G.nodes[n]["color"] for n in nodes],
                        colorscale="RdYlGn_r", showscale=True, line=dict(width=1, color='white'))
        ))
        fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
        st.plotly_chart(fig_net, use_container_width=True)

with c2:
    st.subheader("📊 Hub Signal Ranking")
    if not filtered_df.empty:
        # Il menu a barre degli Hub ripristinato
        fig_bar = px.bar(filtered_df.sort_values("initial_score", ascending=True).tail(15), 
                         x="initial_score", y="target_id", orientation='h',
                         color="toxicity_index", color_continuous_scale="RdYlGn_r",
                         labels={"initial_score": "Segnale VTG", "target_id": "Hub"},
                         template="plotly_dark")
        fig_bar.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

# --- 7. HUB INTELLIGENCE ---
if search_query:
    st.divider()
    st.subheader(f"📂 Hub Intelligence: {search_query}")
    i1, i2, i3 = st.columns(3)
    with i1:
        st.markdown("### 🧬 Pathways (PMI)")
        for _, r in pmi_df.iterrows():
            with st.expander(f"**{r.get('Canonical_Name', 'N/D')}**"):
                st.write(r.get('Description_L0', 'Descrizione non disponibile.'))
    with i2:
        st.markdown("### 💊 Therapeutics (ODI)")
        for _, r in odi_df.iterrows():
            with st.expander(f"**{r.get('Generic_Name', 'N/D')}**"):
                st.write(r.get('Description_L0', 'Descrizione non disponibile.'))
    with i3:
        st.markdown("### 🧪 Trials (GCI)")
        for _, r in gci_df.iterrows():
            with st.expander(f"Phase {r.get('Phase', 'N/D')} - {r.get('NCT_Number', 'Trial')}"):
                st.write(r.get('Canonical_Title', 'N/D'))

# --- 8. FOOTER ---
st.divider()
st.caption("MAESTRO Omikron Suite v19.2.1 | © 2026 Omikron Orchestra Project | Research Use Only")
