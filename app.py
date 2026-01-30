# --- RAGNATELA OTTIMIZZATA ---
st.divider()
st.subheader("🕸️ Network Interaction Map (AXON Web)")

if not filtered_df.empty:
    G = nx.Graph()
    for _, row in filtered_df.iterrows():
        # Usiamo .get() o valori di default per evitare errori se mancano dati
        G.add_node(row['target_id'], 
                   size=float(row.get('initial_score', 1)) * 20, 
                   color=float(row.get('toxicity_index', 0.5)))
    
    nodes = list(G.nodes())
    # Crea connessioni artificiali per l'MVP se ci sono più nodi
    if len(nodes) > 1:
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 3, len(nodes))):
                G.add_edge(nodes[i], nodes[j])
    
    # Layout spaziale
    pos = nx.spring_layout(G, k=0.5, seed=42)
    
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none')

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append(G.nodes[node]['color'])
        node_size.append(G.nodes[node]['size'])

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=node_text, 
        textposition="top center",
        marker=dict(showscale=True, colorscale='RdYlGn_r', color=node_color, size=node_size, line_width=2)
    )

    fig_net = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            showlegend=False,
                            margin=dict(b=0,l=0,r=0,t=0),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)'
                        ))
    st.plotly_chart(fig_net, use_container_width=True)
else:
    st.warning("Nessun nodo da visualizzare nella ragnatela.")
