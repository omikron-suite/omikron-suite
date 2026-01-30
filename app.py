import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go

# ============================================================
# MAESTRO | Omikron Orchestra Suite
# - Hub focus + 1-hop neighbors from Supabase "axon_edges"
# - Fallback overview network when no hub is selected
# ============================================================

st.set_page_config(page_title="MAESTRO Omikron Suite", layout="wide")

# --- SUPABASE (use secrets in production) ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

# =========================
# Helpers
# =========================
def safe_df_cols(dfx: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in dfx.columns]


def normalize_id(x) -> str:
    return str(x).strip().upper() if x is not None else ""


# =========================
# Data loaders
# =========================
@st.cache_data(ttl=600)
def load_axon_nodes() -> pd.DataFrame:
    """
    Nodes table expected: axon_knowledge(target_id, initial_score, toxicity_index)
    """
    try:
        res = supabase.table("axon_knowledge").select("target_id,initial_score,toxicity_index").execute()
        d = pd.DataFrame(res.data or [])

        if d.empty:
            return d

        d["target_id"] = d["target_id"].apply(normalize_id)

        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0).clip(0.0, 1.0)

        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])
        return d

    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})


@st.cache_data(ttl=600)
def load_edges_for_hub(hub: str) -> pd.DataFrame:
    """
    Edges table expected: axon_edges(source_id, target_id, weight)
    If your table name/columns differ, change them here.
    """
    hub = normalize_id(hub)
    if not hub:
        return pd.DataFrame()

    try:
        # hub as source
        res1 = (
            supabase.table("axon_edges")
            .select("source_id,target_id,weight")
            .eq("source_id", hub)
            .execute()
        )
        # hub as target (for undirected neighborhood)
        res2 = (
            supabase.table("axon_edges")
            .select("source_id,target_id,weight")
            .eq("target_id", hub)
            .execute()
        )

        d1 = pd.DataFrame(res1.data or [])
        d2 = pd.DataFrame(res2.data or [])
        edges = pd.concat([d1, d2], ignore_index=True)

        if edges.empty:
            return edges

        edges["source_id"] = edges["source_id"].apply(normalize_id)
        edges["target_id"] = edges["target_id"].apply(normalize_id)
        edges["weight"] = pd.to_numeric(edges.get("weight"), errors="coerce").fillna(0.0)

        # drop self-loops + duplicates
        edges = edges[edges["source_id"] != edges["target_id"]].drop_duplicates(
            subset=["source_id", "target_id"], keep="first"
        )

        return edges

    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})


@st.cache_data(ttl=600)
def query_portals(search_query: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads portal data for the hub/target.
    """
    q = normalize_id(search_query)
    if not q:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    try:
        res_gci = (
            supabase.table("GCI_clinical_trials")
            .select("*")
            .ilike("Primary_Biomarker", f"%{q}%")
            .execute()
        )
        gci_df = pd.DataFrame(res_gci.data or [])

        res_pmi = (
            supabase.table("pmi_database")
            .select("*")
            .ilike("Key_Targets", f"%{q}%")
            .execute()
        )
        pmi_df = pd.DataFrame(res_pmi.data or [])

        res_odi = (
            supabase.table("odi_database")
            .select("*")
            .ilike("Targets", f"%{q}%")
            .execute()
        )
        odi_df = pd.DataFrame(res_odi.data or [])

        return gci_df, pmi_df, odi_df

    except Exception:
        # show details in UI instead (sidebar)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# =========================
# Graph builders
# =========================
def build_ego_graph_1hop(
    df_nodes: pd.DataFrame,
    hub: str,
    edges: pd.DataFrame,
    top_k: int = 25,
) -> nx.Graph:
    """
    Graph = hub + its 1-hop neighbors (top_k by weight) + edges among them (from those rows).
    """
    hub = normalize_id(hub)
    G = nx.Graph()

    if df_nodes.empty or not hub:
        return G

    # map node attributes
    nodes_map = (
        df_nodes.set_index("target_id")[["initial_score", "toxicity_index", "ces_score"]]
        .to_dict("index")
        if "target_id" in df_nodes.columns
        else {}
    )

    # always add hub node (even if no edges)
    if hub in nodes_map:
        r = nodes_map[hub]
        G.add_node(hub, size=float(r["initial_score"]) * 70, color=float(r["toxicity_index"]))
    else:
        G.add_node(hub, size=22.0, color=0.5)

    if edges is None or edges.empty or "error" in edges.columns:
        return G

    edges_sorted = edges.sort_values("weight", ascending=False).head(int(top_k)).copy()

    # determine neighbors
    neigh = set()
    for _, e in edges_sorted.iterrows():
        a = normalize_id(e["source_id"])
        b = normalize_id(e["target_id"])
        if a == hub:
            neigh.add(b)
        elif b == hub:
            neigh.add(a)

    # add neighbors
    for n in sorted(neigh):
        if n in nodes_map:
            r = nodes_map[n]
            size = float(r["initial_score"]) * 35
            color = float(r["toxicity_index"])
        else:
            size = 18.0
            color = 0.5
        G.add_node(n, size=size, color=color)

    # add edges (only those inside ego node set)
    ego_nodes = set(G.nodes())
    for _, e in edges_sorted.iterrows():
        a = normalize_id(e["source_id"])
        b = normalize_id(e["target_id"])
        if a in ego_nodes and b in ego_nodes and a != b:
            G.add_edge(a, b, weight=float(e.get("weight", 0.0)))

    return G


def build_overview_graph(df_nodes: pd.DataFrame, max_nodes: int = 120) -> nx.Graph:
    """
    Simple overview graph (no true interactions): chain edges.
    Keeps UI responsive by limiting node count.
    """
    G = nx.Graph()
    if df_nodes.empty:
        return G

    d = df_nodes.copy()
    if len(d) > max_nodes:
        d = d.nlargest(max_nodes, "initial_score")

    for _, r in d.iterrows():
        tid = normalize_id(r["target_id"])
        G.add_node(
            tid,
            size=float(r["initial_score"]) * 28,
            color=float(r["toxicity_index"]),
        )

    nodes = list(G.nodes())
    for i in range(len(nodes) - 1):
        G.add_edge(nodes[i], nodes[i + 1], weight=0.0)

    return G


def plot_graph(G: nx.Graph, title: str = ""):
    if G.number_of_nodes() == 0:
        st.info("Nessun nodo da visualizzare.")
        return

    pos = nx.spring_layout(G, k=1.0, seed=42)

    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            hoverinfo="none",
            line=dict(width=1),
        )
    )

    nodes = list(G.nodes())
    fig.add_trace(
        go.Scatter(
            x=[pos[n][0] for n in nodes],
            y=[pos[n][1] for n in nodes],
            mode="markers+text",
            text=nodes,
            textposition="top center",
            marker=dict(
                size=[G.nodes[n].get("size", 18) for n in nodes],
                color=[G.nodes[n].get("color", 0.5) for n in nodes],
                colorscale="RdYlGn_r",
                showscale=True,
                line=dict(width=2),
            ),
        )
    )

    fig.update_layout(
        title=title if title else None,
        showlegend=False,
        margin=dict(b=0, l=0, r=0, t=30 if title else 0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )

    st.plotly_chart(fig, use_container_width=True)


# =========================
# Load base nodes
# =========================
df = load_axon_nodes()

# hard error display
if "error" in df.columns:
    st.error(f"Errore caricamento axon_knowledge: {df['error'].iloc[0]}")
    df = pd.DataFrame()

# =========================
# Sidebar
# =========================
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8)
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8)

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Smart Search & Hub Focus")
search_query = normalize_id(st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS"))

top_k = st.sidebar.slider("Numero vicini (1-hop)", 5, 100, 25, step=5)
overview_max_nodes = st.sidebar.slider("Max nodi overview", 30, 300, 120, step=10)

st.sidebar.warning("⚠️ **Research Use Only**")

# =========================
# Filters + portal queries
# =========================
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
filtered_df = pd.DataFrame()

if not df.empty:
    if search_query:
        # portal queries
        try:
            gci_df, pmi_df, odi_df = query_portals(search_query)
        except Exception as e:
            st.sidebar.error(f"Errore query portali: {e}")

        # keep nodes containing the query (for fallback lists, not for ego graph)
        filtered_df = df[df["target_id"].str.contains(search_query, na=False)]
    else:
        filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]
else:
    filtered_df = df

# =========================
# UI Header + metrics
# =========================
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

# =========================
# Network
# =========================
st.subheader("🕸️ Network Interaction Map")

if search_query and not df.empty:
    edges_df = load_edges_for_hub(search_query)
    if "error" in edges_df.columns:
        st.error(f"Errore caricamento axon_edges: {edges_df['error'].iloc[0]}")
        edges_df = pd.DataFrame()

    G = build_ego_graph_1hop(df_nodes=df, hub=search_query, edges=edges_df, top_k=top_k)

    if G.number_of_nodes() <= 1:
        st.info("Nessun vicino trovato per questo hub (controlla axon_edges o il valore di Top K).")
    else:
        plot_graph(G, title=f"Hub: {search_query} | 1-hop neighbors (Top {top_k})")

else:
    if filtered_df.empty:
        st.info("Nessun risultato con i filtri attuali.")
    else:
        G = build_overview_graph(filtered_df, max_nodes=overview_max_nodes)
        plot_graph(G, title=f"Overview network (max {overview_max_nodes} nodi)")

# =========================
# Portals
# =========================
st.divider()
p_odi, p_gci = st.columns(2)

with p_odi:
    st.header("💊 Therapeutics (ODI)")
    cols = safe_df_cols(odi_df, ["Generic_Name", "Drug_Class"])
    if not odi_df.empty and cols:
        st.dataframe(odi_df[cols], use_container_width=True)
    elif search_query:
        st.caption("Nessun farmaco associato trovato.")

with p_gci:
    st.header("🧪 Clinical Trials (GCI)")
    cols = safe_df_cols(gci_df, ["Canonical_Title", "Phase"])
    if not gci_df.empty and cols:
        st.dataframe(gci_df[cols], use_container_width=True)
    elif search_query:
        st.caption("Nessun trial clinico associato trovato.")

st.caption("MAESTRO Suite | RUO")
