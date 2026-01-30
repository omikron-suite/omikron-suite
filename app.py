@st.cache_data(ttl=600)
def load_edges_for_hub(hub: str):
    """
    Carica archi dove hub è source o target.
    Richiede tabella Supabase: axon_edges(source_id, target_id, weight)
    """
    if not hub:
        return pd.DataFrame()

    hub = str(hub).strip().upper()

    try:
        # 1) hub come source
        res1 = supabase.table("axon_edges") \
            .select("source_id,target_id,weight") \
            .eq("source_id", hub).execute()

        # 2) hub come target (se vuoi rete non direzionale)
        res2 = supabase.table("axon_edges") \
            .select("source_id,target_id,weight") \
            .eq("target_id", hub).execute()

        d1 = pd.DataFrame(res1.data or [])
        d2 = pd.DataFrame(res2.data or [])

        edges = pd.concat([d1, d2], ignore_index=True)
        if edges.empty:
            return edges

        for c in ["source_id", "target_id"]:
            edges[c] = edges[c].astype(str).str.strip().str.upper()

        edges["weight"] = pd.to_numeric(edges.get("weight"), errors="coerce").fillna(0.0)
        return edges

    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})


def build_ego_graph(df_nodes: pd.DataFrame, hub: str, edges: pd.DataFrame, top_k: int = 25):
    """
    Costruisce un grafo con hub + primi vicini (1-hop) + archi reali.
    - top_k: massimo numero di vicini
    """
    G = nx.Graph()

    if df_nodes.empty or not hub:
        return G

    hub = hub.strip().upper()

    # Indicizza attributi nodo da df_nodes
    nodes_map = df_nodes.set_index("target_id")[["initial_score", "toxicity_index", "ces_score"]].to_dict("index")

    # Se non ho archi, restituisco solo hub (o fallback)
    if edges is None or edges.empty or "error" in edges.columns:
        if hub in nodes_map:
            r = nodes_map[hub]
            G.add_node(hub, size=float(r["initial_score"]) * 60, color=float(r["toxicity_index"]))
        return G

    # Prendo i top_k archi per peso (se weight esiste)
    edges_sorted = edges.sort_values("weight", ascending=False).head(int(top_k))

    # Vicini dell'hub (sia source che target)
    neigh = set()
    for _, e in edges_sorted.iterrows():
        a, b = e["source_id"], e["target_id"]
        if a == hub and b != hub:
            neigh.add(b)
        if b == hub and a != hub:
            neigh.add(a)

    # Nodi: hub + vicini
    node_list = [hub] + sorted(neigh)

    # Aggiungi nodi con attributi (se mancano in df, li aggiungo comunque)
    for n in node_list:
        if n in nodes_map:
            r = nodes_map[n]
            size = float(r["initial_score"]) * (70 if n == hub else 35)
            color = float(r["toxicity_index"])
        else:
            size = 18.0
            color = 0.5
        G.add_node(n, size=size, color=color)

    # Aggiungi archi SOLO tra nodi presenti (ego)
    for _, e in edges_sorted.iterrows():
        a, b = e["source_id"], e["target_id"]
        if a in G.nodes and b in G.nodes and a != b:
            w = float(e.get("weight", 0.0))
            G.add_edge(a, b, weight=w)

    return G
