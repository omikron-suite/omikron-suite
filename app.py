import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. LANGUAGE DICTIONARY ---
LANG = {
    "English": {
        "title": "🛡️ MAESTRO: Omikron Orchestra Suite",
        "sidebar_title": "Control Center",
        "vtg_label": "Minimum VTG Threshold",
        "tmi_label": "TMI Toxicity Limit",
        "search_label": "🔍 Search Hub Target",
        "neighbors_label": "Number of Neighbors (K)",
        "ruo_warning": "Research Use Only (RUO). Data does not constitute medical advice.",
        "detected": "DETECTED",
        "linked": "Linked",
        "items": "Items",
        "desc_l0": "Functional target analysis in progress: critical signaling hub detected.",
        "neighbors_header": "### 🔗 First Neighbors (Hub Context)",
        "network_header": "🕸️ Network Interaction Map",
        "ranking_header": "📊 Hub Signal Ranking",
        "intel_desk": "📂 Hub Intelligence Desk",
        "therapeutics": "💊 Therapeutics (ODI)",
        "trials": "🧪 Clinical Trials (GCI)",
        "pathways": "🧬 Pathways (PMI)",
        "disclaimer_title": "⚠️ SCIENTIFIC AND LEGAL DISCLAIMER",
        "disclaimer_text": "MAESTRO Omikron Suite is intended exclusively for Research Use Only (RUO). Generated analyses do not replace medical advice.",
    },
    "Italiano": {
        "title": "🛡️ MAESTRO: Omikron Orchestra Suite",
        "sidebar_title": "Centro di Controllo",
        "vtg_label": "Soglia Minima VTG",
        "tmi_label": "Limite Tossicità TMI",
        "search_label": "🔍 Ricerca Hub Target",
        "neighbors_label": "Numero primi vicini (K)",
        "ruo_warning": "Uso esclusivo di ricerca (RUO). I dati non costituiscono parere clinico.",
        "detected": "RILEVATO",
        "linked": "Collegati",
        "items": "Elementi",
        "desc_l0": "Analisi funzionale del target in corso: rilevato nodo critico per la segnalazione cellulare.",
        "neighbors_header": "### 🔗 Primi vicini (contesto dell’hub)",
        "network_header": "🕸️ Mappa di Interazione Network",
        "ranking_header": "📊 Ranking Segnale Hub",
        "intel_desk": "📂 Hub Intelligence Desk",
        "therapeutics": "💊 Terapie (ODI)",
        "trials": "🧪 Trial Clinici (GCI)",
        "pathways": "🧬 Pathway (PMI)",
        "disclaimer_title": "⚠️ DISCLAIMER SCIENTIFICO E LEGALE",
        "disclaimer_text": "MAESTRO Omikron Suite è destinato esclusivamente ad uso di ricerca (RUO). Le analisi generate non sostituiscono pareri medici.",
    }
}

# --- 2. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v20.7", layout="wide")

# --- 3. LANGUAGE SELECTOR ---
sel_lang = st.sidebar.selectbox("🌐 Language / Lingua", ["English", "Italiano"])
L = LANG[sel_lang]

# --- 4. CONNECTION ---
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
    except Exception as e: return pd.DataFrame({"error": [str(e)]})

def get_first_neighbors(df_all, hub, k, min_sig, max_t):
    if df_all.empty or not hub: return pd.DataFrame()
    cand = df_all[(df_all["target_id"] != hub) & (df_all["initial_score"] >= min_sig) & (df_all["toxicity_index"] <= max_t)].copy()
    if cand.empty: return cand
    return cand.sort_values(["ces_score", "initial_score"], ascending=False).head(int(k))

df = load_axon()

# --- 5. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title(L["sidebar_title"])
min_sig = st.sidebar.slider(L["vtg_label"], 0.0, 3.0, 0.8)
max_t = st.sidebar.slider(L["tmi_label"], 0.0, 1.0, 0.8)
st.sidebar.divider()
search_query = st.sidebar.text_input(L["search_label"], placeholder="e.g. KRAS").strip().upper()
top_k = st.sidebar.slider(L["neighbors_label"], 3, 30, 10)

st.sidebar.markdown(f"""
<div style="background-color: #1a1a1a; padding: 12px; border-radius: 8px; border-left: 4px solid #ff4b4b; margin-top: 10px;">
    <p style="font-size: 0.75rem; color: #ff4b4b; font-weight: bold; margin-bottom: 5px;">⚠️ RUO STATUS</p>
    <p style="font-size: 0.7rem; color: #aaa; text-align: justify; line-height: 1.2;">{L['ruo_warning']}</p>
</div>
""", unsafe_allow_html=True)

# --- 6. DATA PORTALS ---
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

# --- 7. UI: OPERA DIRECTOR ---
st.title(L["title"])

if not df.empty and search_query:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 15px;">
            <div style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #007bff; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">OMI</span><br><span style="font-size: 1.1rem; font-weight: bold;">{L['detected']}</span>
            </div>
            <div style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #6f42c1; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">SMI</span><br><span style="font-size: 1.1rem; font-weight: bold;">{len(pmi_df)} {L['linked']}</span>
            </div>
            <div style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #ffc107; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">ODI</span><br><span style="font-size: 1.1rem; font-weight: bold;">{len(odi_df)} {L['items']}</span>
            </div>
            <div style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #dc3545; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">TMI</span><br><span style="font-size: 1.1rem; font-weight: bold;">{row['toxicity_index']:.2f}</span>
            </div>
            <div style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #28a745; text-align: center;">
                <span style="font-size: 0.7rem; color: #aaa;">CES</span><br><span style="font-size: 1.1rem; font-weight: bold;">{row['ces_score']:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.warning(f"**🧬 L0:** {L['desc_l0']}")

# --- 8. GRAPHICS (NETWORK & RANKING) ---
st.divider()
neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
filtered_df = pd.concat([df[df["target_id"] == search_query], neighbors_df], ignore_index=True) if search_query else df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
    st.subheader(L["network_header"])
    
    
    
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]; is_hub = (tid == search_query)
        G.add_node(tid, size=float(r["initial_score"]) * (70 if is_hub else 35), color=float(r["toxicity_index"]))
        if search_query and tid != search_query: G.add_edge(search_query, tid)
    
    pos = nx.spring_layout(G, k=1.1, seed=42)
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]; x1, y1 = pos[b]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
    
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color='#444', width=0.8), hoverinfo="none"))
    fig_net.add_trace(go.Scatter(x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()], mode="markers+text", text=list(G.nodes()), 
                                 marker=dict(size=[G.nodes[n]["size"] for n in G.nodes()], color=[G.nodes[n]["color"] for n in G.nodes()], colorscale="RdYlGn_r", showscale=True, line=dict(width=1, color='white'))))
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
    st.plotly_chart(fig_net, use_container_width=True)

    st.subheader(L["ranking_header"])
    
    
    
    fig_bar = px.bar(filtered_df.sort_values("initial_score", ascending=True).tail(15), x="initial_score", y="target_id", orientation='h', color="toxicity_index", color_continuous_scale="RdYlGn_r", template="plotly_dark")
    st.plotly_chart(fig_bar, use_container_width=True)

# --- 9. HUB INTELLIGENCE DESK ---
if search_query:
    st.divider()
    st.subheader(f"{L['intel_desk']}: {search_query}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"### {L['therapeutics']}")
        for _, r in odi_df.iterrows():
            with st.expander(f"**{r.get('Generic_Name', 'N/A')}**"): st.write(r.get('Description_L0', 'N/A'))
    with c2:
        st.markdown(f"### {L['trials']}")
        for _, r in gci_df.iterrows():
            with st.expander(f"Phase {r.get('Phase', 'N/A')}"): st.write(r.get('Canonical_Title', 'N/A'))
    with c3:
        st.markdown(f"### {L['pathways']}")
        for _, r in pmi_df.iterrows():
            with st.expander(f"**{r.get('Canonical_Name', 'N/A')}**"): st.write(r.get('Description_L0', 'N/A'))

# --- 10. DISCLAIMER ---
st.divider()
st.markdown(f"""
<div style="background-color: #0e1117; padding: 25px; border-radius: 12px; border: 1px solid #333; text-align: center; max-width: 900px; margin: 0 auto;">
    <h4 style="color: #ff4b4b; margin-top: 0;">{L['disclaimer_title']}</h4>
    <p style="font-size: 0.8rem; color: #888; text-align: justify; line-height: 1.5;">{L['disclaimer_text']}</p>
    <p style="font-size: 0.75rem; color: #444; margin-top: 15px;">© 2026 Omikron Orchestra Project</p>
</div>
""", unsafe_allow_html=True)
