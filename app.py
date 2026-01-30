import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite v19.7", layout="wide")

# --- 2. CONNESSIONE ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty: return d
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("Versione 19.7.1 - Intelligence L0")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS").strip().upper()

# --- 4. DATA PORTALS & COUNTS ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600)
def get_global_counts():
    try:
        c_odi = supabase.table("odi_database").select("id", count="exact").execute().count
        c_pmi = supabase.table("pmi_database").select("id", count="exact").execute().count
        c_gci = supabase.table("GCI_clinical_trials").select("id", count="exact").execute().count
        return c_odi, c_pmi, c_gci
    except: return 0, 0, 0

total_odi, total_pmi, total_gci = get_global_counts()

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

if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # PARAMETRI PIÙ PICCOLI (CSS INLINE)
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 10px;">
            <div style="background: #111; padding: 10px; border-radius: 5px; border-left: 3px solid #007bff;">
                <span style="font-size: 0.7rem; color: #888;">OMI</span><br>
                <span style="font-size: 1.1rem; font-weight: bold; color: #fff;">DETECTED</span>
            </div>
            <div style="background: #111; padding: 10px; border-radius: 5px; border-left: 3px solid #6f42c1;">
                <span style="font-size: 0.7rem; color: #888;">SMI</span><br>
                <span style="font-size: 1.1rem; font-weight: bold; color: #fff;">{len(pmi_df)} Linked</span>
            </div>
            <div style="background: #111; padding: 10px; border-radius: 5px; border-left: 3px solid #ffc107;">
                <span style="font-size: 0.7rem; color: #888;">ODI</span><br>
                <span style="font-size: 1.1rem; font-weight: bold; color: #fff;">{len(odi_df)} Items</span>
            </div>
            <div style="background: #111; padding: 10px; border-radius: 5px; border-left: 3px solid #dc3545;">
                <span style="font-size: 0.7rem; color: #888;">TMI</span><br>
                <span style="font-size: 1.1rem; font-weight: bold; color: #fff;">{row['toxicity_index']:.2f}</span>
            </div>
            <div style="background: #111; padding: 10px; border-radius: 5px; border-left: 3px solid #28a745;">
                <span style="font-size: 0.7rem; color: #888;">CES</span><br>
                <span style="font-size: 1.1rem; font-weight: bold; color: #fff;">{row['ces_score']:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # AGGIUNTA INFO L0
        descr_l0 = row.get("description_l0", "Analisi funzionale del target in corso: nodo critico per la segnalazione cellulare e potenziale hotspot oncogenico.")
        st.info(f"**Intelligence L0 Summary:** {descr_l0}")
        st.divider()

# --- 6. RAGNATELA (NON TOCCATA) ---
filtered_df = df[df["target_id"].str.contains(search_query, na=False)] if search_query else df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_f = (tid == search_query)
        G.add_node(tid, size=float(r["initial_score"]) * (50 if is_f else 30), color=float(r["toxicity_index"]))

    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query: G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes) - 1): G.add_edge(nodes[i], nodes[i + 1])

    pos = nx.spring_layout(G, k=1.2, seed=42)
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]; x1, y1 = pos[b]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color='#444', width=0.8), hoverinfo="none"))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
        mode="markers+text", text=nodes, textposition="top center",
        textfont=dict(size=10, color="white"),
        marker=dict(size=[G.nodes[n]["size"] for n in nodes], color=[G.nodes[n]["color"] for n in nodes],
                    colorscale="RdYlGn_r", showscale=True, line=dict(width=1, color='white'))
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
    st.plotly_chart(fig_net, use_container_width=True)

    # RANKING
    st.subheader("📊 Hub Signal Ranking")
    fig_bar = px.bar(filtered_df.sort_values("initial_score", ascending=True).tail(15), 
                     x="initial_score", y="target_id", orientation='h',
                     color="toxicity_index", color_continuous_scale="RdYlGn_r",
                     template="plotly_dark")
    fig_bar.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)

# --- 7. BADGE DINAMICI (PRIMA DEL DISCLAIMER) ---
st.divider()
if search_query:
    # Versione "Incasellata" e piccola (Match specifici)
    st.caption("🔍 Local Items Match:")
    bc1, bc2, bc3 = st.columns(3)
    bc1.markdown(f'<div style="background:#b8860b77; padding:10px; border-radius:5px; text-align:center;">💊 ODI: {len(odi_df)}</div>', unsafe_allow_html=True)
    bc2.markdown(f'<div style="background:#4b008277; padding:10px; border-radius:5px; text-align:center;">🧬 PMI: {len(pmi_df)}</div>', unsafe_allow_html=True)
    bc3.markdown(f'<div style="background:#2e8b5777; padding:10px; border-radius:5px; text-align:center;">🧪 GCI: {len(gci_df)}</div>', unsafe_allow_html=True)
else:
    # Versione "Grande" (Totali Globali) come da immagine
    st.caption("🌐 Global Database Inventory:")
    bg1, bg2, bg3 = st.columns(3)
    bg1.markdown(f'<div style="background:#b8860b; padding:15px; border-radius:10px; text-align:center; font-weight:bold; color:white;">💊 ODI ITEMS: {total_odi}</div>', unsafe_allow_html=True)
    bg2.markdown(f'<div style="background:#4b0082; padding:15px; border-radius:10px; text-align:center; font-weight:bold; color:white;">🧬 PMI ITEMS: {total_pmi}</div>', unsafe_allow_html=True)
    bg3.markdown(f'<div style="background:#2e8b57; padding:15px; border-radius:10px; text-align:center; font-weight:bold; color:white;">🧪 GCI ITEMS: {total_gci}</div>', unsafe_allow_html=True)

# --- 8. HUB INTELLIGENCE (DATABASE DETTAGLIATI) ---
if search_query:
    st.divider()
    cp, cd, ct = st.columns(3)
    with cp:
        st.markdown("### 🧬 Pathways (PMI)")
        for _, r in pmi_df.iterrows():
            with st.expander(f"**{r.get('Canonical_Name', 'N/D')}**"):
                st.write(r.get('Description_L0', 'N/A'))
    with cd:
        st.markdown("### 💊 Therapeutics (ODI)")
        for _, r in odi_df.iterrows():
            with st.expander(f"**{r.get('Generic_Name', 'N/D')}**"):
                st.write(r.get('Description_L0', 'N/A'))
    with ct:
        st.markdown("### 🧪 Trials (GCI)")
        for _, r in gci_df.iterrows():
            with st.expander(f"Phase {r.get('Phase', 'N/D')} - {r.get('NCT_Number', 'Trial')}"):
                st.write(f"**Title:** {r.get('Canonical_Title', 'N/D')}")

# --- 9. DISCLAIMER ---
st.divider()
st.markdown("""
<div style="background-color: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333;">
    <p style="font-size: 0.8rem; color: #888; text-align: justify;">
        <b>DISCLAIMER:</b> MAESTRO Omikron Suite è uno strumento destinato esclusivamente ad uso di ricerca (Research Use Only - RUO). 
        I dati sono estratti dai database proprietari Omikron (AXON, ODI, PMI, GCI).
    </p>
    <p style="font-size: 0.8rem; color: #555; text-align: center;">
        v19.7.1 | © 2026 Omikron Orchestra Project
    </p>
</div>
""", unsafe_allow_html=True)
