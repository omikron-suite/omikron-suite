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
        data = res.data or []
        d = pd.DataFrame(data)
        if d.empty: return d
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0).clip(0.0, 1.0)
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

df = load_axon()

# --- SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Smart Search & Hub Focus")
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS")
search_query = (search_query or "").strip().upper()

# --- DATA PORTALS & LOGICA CARTELLA ---
gci_df = pd.DataFrame()
pmi_df = pd.DataFrame()
odi_df = pd.DataFrame()

if search_query and not df.empty:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])

        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])

        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except Exception as e:
        st.sidebar.error(f"Errore query: {e}")

# --- NUOVO MATTONCINO: CARTELLA FARMACI NELLA SIDEBAR ---
if not odi_df.empty:
    st.sidebar.success(f"📂 **Cartella Farmaci: {len(odi_df)}**")
    with st.sidebar.expander("Apri Cartella"):
        for drug in odi_df['Generic_Name'].unique():
            st.write(f"💊 {drug}")

st.sidebar.warning("⚠️ **Research Use Only**")

# --- FILTRO DATI ---
if "error" in df.columns:
    st.error(f"Errore: {df['error'].iloc[0]}")
    df = pd.DataFrame()

filtered_df = pd.DataFrame()
if search_query and not df.empty:
    # Filtro hub e vicini
    filtered_df = df[df["target_id"].str.contains(search_query, na=False)]
else:
    filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)] if not df.empty else df

# --- UI ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Biomarker)", "DETECTED")
        c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked")
        c3.metric("ODI (Drug)", "TARGETABLE" if not odi_df.empty else "NO DRUG")
        c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", delta_color="inverse")
        c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}")

        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI", "OPTIMAL")
        r2c2.metric("GNI", "STABLE")
        r2c3.metric("EVI", "LOW RISK")
        r2c4.metric("MBI", "RESILIENT")
        phase = gci_df["Phase"].iloc[0] if ("Phase" in gci_df.columns and not gci_df.empty) else "N/D"
        r2c5.metric("GCI", phase)
        st.divider()

st.subheader("🕸️ Network Interaction Map")

if not filtered_df.empty:
    G = nx.Graph()
    # Aggiunta nodi Target
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_f = (tid == search_query)
        G.add_node(tid, size=float(r["initial_score"]) * (50 if is_f else 30),
                   color=float(r["toxicity_index"]), type="target")

    # --- AGGIUNTA NODI E LINEE (SATELLITI) ---
    if search_query in G.nodes:
        # Aggiunta Farmaci
        for _, drug in odi_df.head(5).iterrows():
            d_label = f"💊 {drug['Generic_Name']}"
            G.add_node(d_label, size=25, color=0.2, type="drug")
            G.add_edge(search_query, d_label) # CREA LINEA
        # Aggiunta Pathway
        for _, path in pmi_df.head(3).iterrows():
            p_label = f"🧬 {path['Canonical_Name']}"
            G.add_node(p_label, size=25, color=0.8, type="pathway")
            G.add_edge(search_query, p_label) # CREA LINEA

    # Link tra Hub e Target vicini
    nodes = list(G.nodes())
    if search_query in nodes:
        for n in nodes:
            if n != search_query and G.nodes[n].get("type") == "target":
                G.add_edge(search_query, n)

    pos = nx.spring_layout(G, k=1.3, seed=42)

    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color='#888'), hoverinfo="none"))
    
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes],
        y=[pos[n][1] for n in nodes],
        mode="markers+text",
        text=nodes,
        textposition="top center",
        marker=dict(
            size=[G.nodes[n].get("size", 25) for n in nodes],
            color=[G.nodes[n].get("color", 0.5) for n in nodes],
            colorscale="RdYlGn_r",
            showscale=True,
            line=dict(width=2, color="white"),
        )
    ))

    fig_net.update_layout(showlegend=False, margin=dict(b=0, l=0, r=0, t=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                          yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig_net, use_container_width=True)
else:
    st.info("Nessun risultato con i filtri attuali.")

st.divider()
p_odi, p_gci = st.columns(2)
with p_odi:
    st.header("💊 Therapeutics (ODI)")
    if not odi_df.empty:
        st.dataframe(odi_df[["Generic_Name", "Drug_Class"]], use_container_width=True)
with p_gci:
    st.header("🧪 Clinical Trials (GCI)")
    if not gci_df.empty:
        st.dataframe(gci_df[["Canonical_Title", "Phase"]], use_container_width=True)

st.caption("MAESTRO Suite | RUO")
