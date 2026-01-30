import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite v19.0", layout="wide")

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
st.sidebar.caption("Versione 19.0.4 - Progetto MAESTRO")

min_sig = st.sidebar.slider("Soglia Minima Segnale (VTG)", 0.0, 3.0, 0.8, help="Filtra la forza del segnale biologico rilevato (VTG Score).")
max_t = st.sidebar.slider("Limite Tossicità (TMI)", 0.0, 1.0, 0.8, help="Filtra il rischio di tossicità associato al target.")

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Ricerca Intelligente")
search_query = st.sidebar.text_input("Cerca Target o Hub", placeholder="es. KRAS").strip().upper()

# --- 4. DATA PORTALS & CHECK ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
target_verified = False

if search_query and not df.empty:
    try:
        # Check se il target esiste in AXON
        if search_query in df['target_id'].values:
            target_verified = True
        
        # Query database satelliti
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except: pass

# --- 5. UI PRINCIPALE ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if search_query:
    if target_verified:
        st.success(f"✅ **Target Verificato:** {search_query} (Analisi Hub in corso...)")
    else:
        st.info(f"ℹ️ **Ricerca libera:** Mostrando occorrenze per '{search_query}' nei database correlati.")

if search_query and not df.empty:
    target_data = df[df["target_id"] == search_query]
    if not target_data.empty:
        row = target_data.iloc[0]
        st.markdown(f"## 🎼 Opera Director: {search_query}")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("OMI (Biomarker)", "DETECTED", help="Stato di rilevamento del biomarcatore nel database AXON.")
        c2.metric("SMI (Pathway)", f"{len(pmi_df)} Linked", help="Numero di pathway biochimici (PMI) correlati al target.")
        c3.metric("ODI (Drug)", "TARGETABLE" if not odi_df.empty else "NO DRUG", help="Disponibilità di farmaci (ODI) che agiscono su questo target.")
        c4.metric("TMI (Tossicità)", f"{row['toxicity_index']:.2f}", help="Indice di tossicità specifica: più basso è, più sicuro è il target.")
        c5.metric("CES (Efficiency)", f"{row['ces_score']:.2f}", help="Combined Efficiency Score: bilancio tra segnale e sicurezza.")

        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        r2c1.metric("BCI", "OPTIMAL", help="Biological Cost Index: costo energetico cellulare.")
        r2c2.metric("GNI", "STABLE", help="Genomic Network Index: stabilità del nodo genomico.")
        r2c3.metric("EVI", "LOW RISK", help="Environmental Vulnerability Index.")
        r2c4.metric("MBI", "RESILIENT", help="Microbiota Interaction Index.")
        phase = gci_df["Phase"].iloc[0] if ("Phase" in gci_df.columns and not gci_df.empty) else "N/D"
        r2c5.metric("GCI (Clinica)", phase, help="Stato dell'avanzamento clinico (Trials GCI).")

        # EXPORT TXT
        report_txt = f"MAESTRO REPORT - {search_query}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n" \
                     f"VTG Score: {row['initial_score']}\nTMI Index: {row['toxicity_index']}\n" \
                     f"Linked Drugs: {len(odi_df)}\nLinked Pathways: {len(pmi_df)}\n" \
                     f"Clinical Phase: {phase}\n\nDisclaimer: Research Use Only."
        st.download_button(label="📥 Esporta Risultati (.txt)", data=report_txt, file_name=f"MAESTRO_{search_query}.txt", mime="text/plain")
        st.divider()

# --- 6. RAGNATELA ---
st.subheader("🕸️ Network Interaction Map", help="Visualizzazione dei nodi di interazione. Il nodo centrale rappresenta il target cercato.")
filtered_df = df[df["target_id"].str.contains(search_query, na=False)] if search_query else df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
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
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="none", line=dict(color='#444', width=0.8)))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
        mode="markers+text", text=nodes, textposition="top center",
        textfont=dict(size=10, color="white"), # Testo più piccolo
        marker=dict(size=[G.nodes[n]["size"] for n in nodes], color=[G.nodes[n]["color"] for n in nodes],
                    colorscale="RdYlGn_r", showscale=True, line=dict(width=1, color='white'))
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), height=500)
    st.plotly_chart(fig_net, use_container_width=True)

# --- 7. HUB INTELLIGENCE ---
if search_query:
    st.divider()
    st.subheader(f"📂 Hub Intelligence: {search_query}", help="Database dettagliati relativi al target in esame.")
    cp, cd, ct = st.columns(3)

    with cp:
        st.markdown("### 🧬 Pathways (PMI)", help="Dati dal database PMI sui processi biologici attivati.")
        if not pmi_df.empty:
            for _, r in pmi_df.iterrows():
                with st.expander(f"**{r.get('Canonical_Name', 'N/D')}**"):
                    st.write(r.get('Description_L0', 'Nessun descrittivo presente.'))
        else: st.caption("Nessun pathway correlato.")

    with cd:
        st.markdown("### 💊 Therapeutics (ODI)", help="Dati dal database ODI sui farmaci e molecole approvate o in studio.")
        if not odi_df.empty:
            for _, r in odi_df.iterrows():
                with st.expander(f"**{r.get('Generic_Name', 'N/D')}**"):
                    st.caption(f"Status: {r.get('Regulatory_Status_US', 'N/D')}")
                    st.write(r.get('Description_L0', 'Nessuna descrizione disponibile.'))
        else: st.caption("Nessun farmaco correlato.")

    with ct:
        st.markdown("### 🧪 Clinical Trials (GCI)", help="Dati dal database GCI sugli studi clinici attivi (NCT).")
        if not gci_df.empty:
            for _, r in gci_df.iterrows():
                with st.expander(f"Phase {r.get('Phase', 'N/D')} - {r.get('NCT_Number', 'Trial')}"):
                    st.write(f"**Titolo:** {r.get('Canonical_Title', 'N/D')}")
        else: st.caption("Nessun trial correlato.")

# --- 8. DISCLAIMER COMPLETO ---
st.divider()
st.markdown("""
<div style="background-color: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333;">
    <p style="font-size: 0.8rem; color: #888; text-align: justify;">
        <b>DISCLAIMER LEGALE E SCIENTIFICO:</b> MAESTRO Omikron Suite è uno strumento destinato esclusivamente ad uso di ricerca (Research Use Only - RUO). 
        Le informazioni fornite non costituiscono consulenza medica, diagnosi o raccomandazione terapeutica. I dati sono estratti da database proprietari 
        (AXON, ODI, PMI, GCI) e possono essere soggetti a revisione scientifica costante. L'accuratezza dei collegamenti nella ragnatela è basata su 
        inferenze algoritmiche e deve essere validata sperimentalmente. Omikron Suite non si assume responsabilità per decisioni cliniche o di ricerca 
        basate sui suddetti dati.
    </p>
    <p style="font-size: 0.8rem; color: #555; text-align: center;">
        MAESTRO Omikron Suite v19.0.4 | © 2026 Omikron Orchestra Project | Powered by AXON Intelligence
    </p>
</div>
""", unsafe_allow_html=True)
