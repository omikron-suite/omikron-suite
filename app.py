import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="MAESTRO Omikron Suite v20.6", layout="wide")

# --- 2. CONNESSIONE ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty:
            return d

        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)

        # Formula CES: $CES = VTG \times (1 - TMI)$
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])

        if "description_l0" not in d.columns:
            d["description_l0"] = ""

        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

def get_first_neighbors(df_all: pd.DataFrame, hub: str, k: int, min_sig: float, max_t: float) -> pd.DataFrame:
    if df_all.empty or not hub:
        return pd.DataFrame()

    cand = df_all[
        (df_all["target_id"] != hub) &
        (df_all["initial_score"] >= min_sig) &
        (df_all["toxicity_index"] <= max_t)
    ].copy()

    if cand.empty:
        return cand

    cand = cand.sort_values(["ces_score", "initial_score"], ascending=False).head(int(k))
    return cand

df = load_axon()

# --- 3. SIDEBAR ---
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("Omikron Control Center")
st.sidebar.caption("v20.6 Platinum Build | 2026")

min_sig = st.sidebar.slider(
    "Soglia Minima VTG", 0.0, 3.0, 0.8,
    help="VTG (Vitality Gene Score): intensità del segnale biologico rilevato. Più è alto, più l'hub è 'acceso'."
)
max_t = st.sidebar.slider(
    "Limite Tossicità TMI", 0.0, 1.0, 0.8,
    help="TMI (Toxicity Management Index): soglia di rischio tossicologico. Filtra i target potenzialmente dannosi."
)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Ricerca Hub Target", placeholder="es. KRAS").strip().upper()
top_k = st.sidebar.slider(
    "Numero primi vicini (K)", 3, 30, 10,
    help="Visualizza i Top-K partner molecolari più affini all'hub selezionato per importanza biologica."
)

st.sidebar.markdown("""
<div style="background-color: #1a1a1a; padding: 12px; border-radius: 8px; border-left: 4px solid #ff4b4b; margin-top: 10px;">
    <p style="font-size: 0.75rem; color: #ff4b4b; font-weight: bold; margin-bottom: 5px;">⚠️ RUO STATUS</p>
    <p style="font-size: 0.7rem; color: #aaa; text-align: justify; line-height: 1.2;">
        Research Use Only. I dati algoritmici non costituiscono diagnosi o parere clinico.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. DATA PORTALS ---
gci_df, pmi_df, odi_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if search_query and not df.empty and "error" not in df.columns:
    try:
        res_gci = supabase.table("GCI_clinical_trials").select("*").ilike("Primary_Biomarker", f"%{search_query}%").execute()
        gci_df = pd.DataFrame(res_gci.data or [])
        res_pmi = supabase.table("pmi_database").select("*").ilike("Key_Targets", f"%{search_query}%").execute()
        pmi_df = pd.DataFrame(res_pmi.data or [])
        res_odi = supabase.table("odi_database").select("*").ilike("Targets", f"%{search_query}%").execute()
        odi_df = pd.DataFrame(res_odi.data or [])
    except Exception:
        pass

# --- 5. UI: OPERA DIRECTOR ---
st.title("🛡️ MAESTRO: Omikron Orchestra Suite")

if df.empty:
    st.error("AXON database vuoto o non disponibile.")
elif "error" in df.columns:
    st.error(f"Errore caricamento AXON: {df['error'].iloc[0]}")
else:
    if search_query:
        target_data = df[df["target_id"] == search_query]

        if target_data.empty:
            st.info(f"Nessun hub trovato per: **{search_query}**")
        else:
            row = target_data.iloc[0]
            st.markdown(f"## 🎼 Opera Director: {search_query}")

            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 15px;">
                <div title="OMI: Rilevamento della presenza molecolare nel database" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #007bff; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">OMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">DETECTED</span>
                </div>
                <div title="SMI: Indice di connessione con i Pathway PMI" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #6f42c1; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">SMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{len(pmi_df)} Linked</span>
                </div>
                <div title="ODI: Numero di farmaci o molecole attive nel database" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #ffc107; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">ODI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{len(odi_df)} Items</span>
                </div>
                <div title="TMI: Toxicity Management Index (0=Sicuro, 1=Critico)" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #dc3545; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">TMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{row['toxicity_index']:.2f}</span>
                </div>
                <div title="CES: Combined Efficiency Score (Bilancio Segnale/Sicurezza)" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #28a745; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">CES</span><br><span style="font-size: 1.2rem; font-weight: bold;">{row['ces_score']:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.warning(f"**🧬 Biological Description L0:** {row.get('description_l0', 'Analisi funzionale del target in corso: rilevato nodo critico per la segnalazione cellulare.')}")

            neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)

            st.markdown("### 🔗 Primi vicini (contesto dell’hub)")
            if neighbors_df.empty:
                st.info("Nessun vicino trovato con i filtri attuali.")
            else:
                show_cols = ["target_id", "initial_score", "toxicity_index", "ces_score"]
                st.dataframe(neighbors_df[show_cols], use_container_width=True, hide_index=True)

            full_report = f"MAESTRO v20.6 REPORT\nTarget: {search_query}\nDate: {datetime.now()}"
            st.download_button("📥 Esporta Full Intelligence (.txt)", full_report, file_name=f"MAESTRO_{search_query}.txt")

# --- 6. RAGNATELA & RANKING ---
st.divider()

if search_query:
    neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
    hub_df = df[df["target_id"] == search_query]
    filtered_df = pd.concat([hub_df, neighbors_df], ignore_index=True) if not hub_df.empty else pd.DataFrame()
else:
    filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    
    # 
    
    G = nx.Graph()
    for _, r in filtered_df.iterrows():
        tid = r["target_id"]
        is_hub = bool(search_query) and (tid == search_query)
        G.add_node(
            tid,
            size=float(r["initial_score"]) * (70 if is_hub else 35),
            color=float(r["toxicity_index"]),
            is_hub=is_hub
        )

    nodes = list(G.nodes())
    if search_query and search_query in nodes:
        for n in nodes:
            if n != search_query:
                G.add_edge(search_query, n)
    elif len(nodes) > 1:
        for i in range(len(nodes) - 1):
            G.add_edge(nodes[i], nodes[i + 1])

    pos = nx.spring_layout(G, k=1.1, seed=42)
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color="#444", width=0.9), hoverinfo="none"))
    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes],
        y=[pos[n][1] for n in nodes],
        mode="markers+text",
        text=nodes,
        textposition="top center",
        marker=dict(
            size=[G.nodes[n]["size"] for n in nodes],
            color=[G.nodes[n]["color"] for n in nodes],
            colorscale="RdYlGn_r",
            showscale=True,
            line=dict(width=[3 if G.nodes[n].get("is_hub") else 1 for n in nodes], color="white")
        )
    ))
    fig_net.update_layout(showlegend=False, margin=dict(b=0, l=0, r=0, t=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
    st.plotly_chart(fig_net, use_container_width=True)

    st.subheader("📊 Hub Signal Ranking")
    
    # 
    
    fig_bar = px.bar(
        filtered_df.sort_values("initial_score", ascending=True).tail(15),
        x="initial_score", y="target_id", orientation="h",
        color="toxicity_index", color_continuous_scale="RdYlGn_r",
        template="plotly_dark"
    )
    fig_bar.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)

# --- 7. HUB INTELLIGENCE DESK ---
if search_query:
    st.divider()
    st.subheader(f"📂 Hub Intelligence Desk: {search_query}")
    c_odi, c_gci, c_pmi = st.columns(3)

    with c_odi:
        st.markdown(f"### 💊 Therapeutics (ODI: {len(odi_df)})")
        if not odi_df.empty:
            for _, r in odi_df.iterrows():
                with st.expander(f"**{r.get('Generic_Name', 'N/D')}**"):
                    st.write(f"**Classe:** {r.get('Drug_Class', 'N/D')}")
                    st.write(f"**Meccanismo:** {r.get('Description_L0', 'Dettagli non disponibili.')}")
                    st.caption(f"Status: {r.get('Regulatory_Status_US', 'N/D')}")
        else:
            st.info("Nessun item ODI trovato.")

    with c_gci:
        st.markdown(f"### 🧪 Clinical Trials (GCI: {len(gci_df)})")
        if not gci_df.empty:
            for _, r in gci_df.iterrows():
                with st.expander(f"**Phase {r.get('Phase', 'N/D')} Trial**"):
                    st.write(f"**ID:** {r.get('NCT_Number', 'N/D')}")
                    st.write(f"**Titolo:** {r.get('Canonical_Title', 'Dettaglio non presente.')}")
        else:
            st.info("Nessun trial GCI trovato.")

    with c_pmi:
        st.markdown(f"### 🧬 Pathways (PMI: {len(pmi_df)})")
        if not pmi_df.empty:
            for _, r in pmi_df.iterrows():
                with st.expander(f"**{r.get('Canonical_Name', 'N/D')}**"):
                    st.write(f"**Dettaglio:** {r.get('Description_L0', 'Dettagli non disponibili.')}")
        else:
            st.info("Nessun pathway PMI trovato.")

# --- 8. FOOTER & DISCLAIMER ---
st.divider()
st.subheader("📚 MAESTRO Intelligence Repository")
exp1, exp2, exp3 = st.columns(3)
with exp1:
    with st.expander("🛡️ AXON Intelligence (OMI/BCI)"):
        st.write("OMI: Target Detection Hub. BCI: Biological Cost Index.")
with exp2:
    with st.expander("💊 ODI & PMI Systems"):
        st.write("ODI: Database Farmaceutico. PMI: Mappatura Pathway.")
with exp3:
    with st.expander("🧪 GCI & TMI (Clinical/Safety)"):
        st.write("GCI: Monitoraggio Trial Clinici. TMI: Toxicity Index.")

st.markdown(f"""
<div style="background-color: #0e1117; padding: 25px; border-radius: 12px; border: 1px solid #333; text-align: center; max-width: 900px; margin: 0 auto; margin-top: 20px;">
    <h4 style="color: #ff4b4b; margin-top: 0;">⚠️ DISCLAIMER SCIENTIFICO E LEGALE</h4>
    <p style="font-size: 0.8rem; color: #888; text-align: justify; line-height: 1.5;">
        <b>MAESTRO Omikron Suite</b> è destinato esclusivamente ad uso di ricerca (RUO). 
        Le analisi generate non sostituiscono pareri medici. I dati riflettono lo stato attuale dei database Omikron.
    </p>
    <p style="font-size: 0.75rem; color: #444; margin-top: 15px;">
        MAESTRO v20.6 | © 2026 Omikron Orchestra Project | Powered by AXON Intelligence
    </p>
</div>
""", unsafe_allow_html=True)
