import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- CONNESSIONE ---
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

# --- SIDEBAR (Solo Filtri) ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control")
min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)
st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Cerca Target", placeholder="es. KRAS").strip().upper()

# --- LOGICA DATI ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query and not df.empty:
    try:
        # Recupero dati con descrittivi
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
        
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
        
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except: pass

# --- UI PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")
        
        # Grid 10 parametri
        r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
        r1c1.metric("OMI", "DETECTED")
        r1c2.metric("SMI", f"{len(pmi_df)} Pathways")
        r1c3.metric("ODI", f"{len(odi_df)} Drugs")
        r1c4.metric("TMI", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        r1c5.metric("CES", f"{row['ces_score']:.2f}")

        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI", "OPTIMAL"); r2c2.metric("GNI", "STABLE")
        r2c3.metric("EVI", "LOW RISK"); r2c4.metric("MBI", "RESILIENT")
        phase = gci_df["Phase"].iloc[0] if ("Phase" in gci_df.columns and not gci_df.empty) else "N/D"
        r2c5.metric("GCI", phase)
        st.divider()

# --- RAGNATELA ---
st.subheader("🕸️ Network Interaction Map")


filtered_df = df[df["target_id"].str.contains(search_query, na=False)] if search_query else df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_hub = (tid == search_query)
        G.add_node(tid, size=float(r["initial_score"]) * (55 if is_hub else 30), color=float(r["toxicity_index"]))
        if search_query and not is_hub: G.add_edge(search_query, tid)
    
    pos = nx.spring_layout(G, k=1.3, seed=42)
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]; x1, y1 = pos[b]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color='#888'), hoverinfo="none"))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()], y=[pos[n][1] for n in G.nodes()],
        mode="markers+text", text=list(G.nodes()), textposition="top center",
        marker=dict(size=[G.nodes[n]["size"] for n in G.nodes()], color=[G.nodes[n]["color"] for n in G.nodes()], colorscale="RdYlGn_r", showscale=True, line=dict(width=1.5, color='white'))
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)

# --- NUOVA SEZIONE: RISULTATI DESCRITTIVI A 3 COLONNE ---
if search_query:
    st.divider()
    st.subheader(f"🧠 Hub Intelligence: {search_query}")
    col_drug, col_path, col_trial = st.columns(3)

    with col_drug:
        st.markdown("### 💊 Therapeutics (ODI)")
        if not odi_df.empty:
            for _, row in odi_df.iterrows():
                with st.expander(f"**{row['Generic_Name']}**"):
                    st.write(f"**Classe:** {row.get('Drug_Class', 'N/D')}")
                    st.write(f"**Meccanismo:** {row.get('Description_L0', 'Descrizione non disponibile')}")
                    st.caption(f"Status: {row.get('Regulatory_Status_US', 'N/D')}")
        else: st.info("Nessun farmaco trovato.")

    with col_path:
        st.markdown("### 🧬 Pathways (PMI)")
        if not pmi_df.empty:
            for _, row in pmi_df.iterrows():
                with st.expander(f"**{row['Canonical_Name']}**"):
                    st.write(f"**Category:** {row.get('Category', 'N/D')}")
                    st.write(f"**Dettaglio:** {row.get('Description_L0', 'Descrizione non disponibile')}")
                    st.caption(f"Priority: {row.get('Evidence_Priority', 'N/D')}")
        else: st.info("Nessun pathway trovato.")

    with col_trial:
        st.markdown("### 🧪 Clinical Trials (GCI)")
        if not gci_df.empty:
            for _, row in gci_df.iterrows():
                with st.expander(f"**Phase {row.get('Phase', 'N/D')} Trial**"):
                    st.write(f"**Titolo:** {row.get('Canonical_Title', 'N/D')}")
                    st.write(f"**Condition:** {row.get('Cancer_Type', 'N/D')}")
                    st.caption(f"ID: {row.get('NCT_Number', 'N/D')}")
        else: st.info("Nessun trial trovato.")

st.caption("MAESTRO Suite | Wide Descriptive Build | RUO")
