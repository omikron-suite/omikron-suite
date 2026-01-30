import streamlit as st
import pandas as pd
from supabase import create_client
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io  # <--- AGGIUNGI QUESTA RIGA







# --- 1. CONFIGURATION ---
st.set_page_config(page_title="MAESTRO Omikron Suite v2.6.2 build 2630012026", layout="wide")

# --- GLOBAL TYPOGRAPHY TUNING (shrink big titles only) ---
st.markdown("""
<style>
/* Streamlit main title (st.title) */
div[data-testid="stAppViewContainer"] h1 {
    font-size: 1.75rem !important;   /* was ~2.25rem */
    line-height: 1.15 !important;
    margin-bottom: 0.35rem !important;
}

/* Section headers from markdown ## and similar */
div[data-testid="stAppViewContainer"] h2 {
    font-size: 1.35rem !important;   /* was ~1.75rem */
    line-height: 1.2 !important;
    margin-top: 0.6rem !important;
    margin-bottom: 0.35rem !important;
}

/* Subheaders / markdown ### */
div[data-testid="stAppViewContainer"] h3 {
    font-size: 1.10rem !important;   /* was ~1.4rem */
    line-height: 1.25 !important;
    margin-top: 0.55rem !important;
    margin-bottom: 0.3rem !important;
}

/* Optional: slightly smaller "st.subheader" spacing without changing body text */
div[data-testid="stAppViewContainer"] [data-testid="stHeader"] {
    margin-bottom: 0.25rem !important;
}
</style>
""", unsafe_allow_html=True)



# --- 2. CONNECTION (Secrets Recommended) ---
URL = st.secrets.get("SUPABASE_URL", "https://zwpahhbxcugldxchiunv.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_yrLrhe_iynvz_WdAE0jJ-A_qCR1VdZ1")
supabase = create_client(URL, KEY)

@st.cache_data(ttl=300)
def load_data_orchestra():
    try:
        # Carica Registro
        reg = supabase.table("target_registry").select("*").execute()
        df_reg = pd.DataFrame(reg.data or [])
        
        # Carica Dati AXON
        axon = supabase.table("axon_knowledge").select("*").execute()
        df_axon = pd.DataFrame(axon.data or [])
        
        return df_reg, df_axon
    except Exception as e:
        st.error(f"Errore connessione: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_reg, df_axon = load_data_orchestra()


@st.cache_data(ttl=600)
def load_axon():
    try:
        res = supabase.table("axon_knowledge").select("*").execute()
        d = pd.DataFrame(res.data or [])
        if d.empty:
            return d

        # Normalization
        d["target_id"] = d["target_id"].astype(str).str.strip().str.upper()
        d["initial_score"] = pd.to_numeric(d.get("initial_score"), errors="coerce").fillna(0.0)
        d["toxicity_index"] = pd.to_numeric(d.get("toxicity_index"), errors="coerce").fillna(0.0)

        # CES Formula: $CES = VTG \times (1 - TMI)$
        d["ces_score"] = d["initial_score"] * (1.0 - d["toxicity_index"])

        # Optional Description Column
        if "description_l0" not in d.columns:
            d["description_l0"] = ""

        return d
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})
        

def get_first_neighbors(df_all: pd.DataFrame, hub: str, k: int, min_sig: float, max_t: float) -> pd.DataFrame:
    """
    Defines "first neighbors" as Top-K candidates ordered by CES (then initial_score)
    respecting the VTG/TMI filters.
    """
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
st.sidebar.caption("v2.6.2 Platinum Build | 2026")

min_sig = st.sidebar.slider(
    "Minimum VTG Threshold", 0.0, 3.0, 0.8,
    help="VTG (Vitality Gene Score): Intensity of the detected biological signal. Higher values mean the hub is 'active'."
)
max_t = st.sidebar.slider(
    "TMI Toxicity Limit", 0.0, 1.0, 0.8,
    help="TMI (Toxicity Management Index): Toxicological risk threshold. Filters out potentially harmful targets."
)

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Hub Target", placeholder="e.g. KRAS").strip().upper()
top_k = st.sidebar.slider(
    "Number of Neighbors (K)", 3, 30, 10,
    help="Number of neighboring partners to display around the selected hub."
)

# SIDEBAR DISCLAIMER
st.sidebar.markdown("""
<div style="background-color: #1a1a1a; padding: 12px; border-radius: 8px; border-left: 4px solid #ff4b4b; margin-top: 10px;">
    <p style="font-size: 0.75rem; color: #ff4b4b; font-weight: bold; margin-bottom: 5px;">⚠️ RUO STATUS</p>
    <p style="font-size: 0.7rem; color: #aaa; text-align: justify; line-height: 1.2;">
        Research Use Only (RUO). Data does not constitute medical or clinical advice.
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
    st.error("AXON database empty or unavailable.")
elif "error" in df.columns:
    st.error(f"Error loading AXON: {df['error'].iloc[0]}")
else:
    if search_query:
        target_data = df[df["target_id"] == search_query]

        if target_data.empty:
            st.info(f"No hub found for: **{search_query}**")
        else:
            row = target_data.iloc[0]
            st.markdown(f"## 🎼 Opera Director: {search_query}")

            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 15px;">
                <div title="OMI: Molecular Identification" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #007bff; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">OMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">DETECTED</span>
                </div>
                <div title="SMI: Pathway Connection Index" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #6f42c1; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">SMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{len(pmi_df)} Linked</span>
                </div>
                <div title="ODI: Drugs/Molecules available" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #ffc107; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">ODI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{len(odi_df)} Items</span>
                </div>
                <div title="TMI: Toxicity Index" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #dc3545; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">TMI</span><br><span style="font-size: 1.2rem; font-weight: bold;">{row['toxicity_index']:.2f}</span>
                </div>
                <div title="CES: Combined Efficiency Score" style="background: #111; padding: 12px; border-radius: 8px; border-top: 4px solid #28a745; text-align: center;">
                    <span style="font-size: 0.7rem; color: #aaa;">CES</span><br><span style="font-size: 1.2rem; font-weight: bold;">{row['ces_score']:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.warning(f"**🧬 Biological Description L0:** {row.get('description_l0', 'Functional target analysis in progress: critical signaling hub detected.')}")

            # --- INIZIO BLOCCO COLORI MAESTRO ---
            st.divider()
            st.subheader("📊 Analisi Cromatica Target")

# Assicuriamoci che i dati siano pronti per il colore
# Il colore sarà basato sulla toxicity_index (TMI)
# Rosso = Pericoloso, Verde = Sicuro

            fig_colors = px.bar(
                target_data, 
                x="action_verb", 
                y="initial_score",
                color="toxicity_index", 
                color_continuous_scale="RdYlGn_r", # La scala Rosso-Giallo-Verde invertita
                range_color=[0, 1], # Definisce i confini della tossicità
                labels={'toxicity_index': 'Rischio TMI', 'initial_score': 'Forza VTG', 'action_verb': 'Meccanismo'},
                template="plotly_dark"
            )

# Rende il grafico più leggibile e professionale
fig_colors.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    coloraxis_colorbar=dict(title="Safety Index")
)

st.plotly_chart(fig_colors, use_container_width=True)
# --- FINE BLOCCO COLORI MAESTRO ---

            # --- FIRST NEIGHBORS (Top-K) ---
neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)

            st.markdown("### 🔗 First Neighbors (Hub Context)")
            if neighbors_df.empty:
                st.info("No neighbors found with current filters. Try lowering VTG or increasing TMI.")
            else:
                # Compact Chips
                chips = []
                for _, r in neighbors_df.iterrows():
                    chips.append(
                        f"**{r['target_id']}** · CES {r['ces_score']:.2f} · "
                        f"TMI {r['toxicity_index']:.2f} · VTG {r['initial_score']:.2f}"
                    )
                st.markdown("\n".join([f"- {c}" for c in chips]))

                show_cols = ["target_id", "initial_score", "toxicity_index", "ces_score"]
                st.dataframe(neighbors_df[show_cols], use_container_width=True, hide_index=True)



# --- ADVANCED INTELLIGENCE EXPORT (FULL ORCHESTRA VERSION) ---
            st.markdown("### 📥 Intelligence Export")
            
            # 1. Prepare Data Blocks
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Hub Core Metrics Block (AXON)
            df_hub_core = pd.DataFrame([{
                "SECTION": "1_HUB_CORE_METRICS",
                "Target_ID": search_query,
                "VTG_Score": row['initial_score'],
                "TMI_Index": row['toxicity_index'],
                "CES_Score": row['ces_score'],
                "Biological_Description": row.get('description_l0', 'N/A'),
                "Export_Date": timestamp
            }])

            # Neighbors Block (Network context)
            neighbors_export = neighbors_df.copy()
            neighbors_export["SECTION"] = "2_NETWORK_NEIGHBORS"
            
            # Therapeutics Block (ODI)
            if not odi_df.empty:
                odi_export = odi_df.copy()
                odi_export["SECTION"] = "3_THERAPEUTICS_ODI"
            else:
                odi_export = pd.DataFrame([{"SECTION": "3_THERAPEUTICS_ODI", "Status": "No pharmacological matches found"}])

            # Clinical Trials Block (GCI)
            if not gci_df.empty:
                gci_export = gci_df.copy()
                gci_export["SECTION"] = "4_CLINICAL_TRIALS_GCI"
            else:
                gci_export = pd.DataFrame([{"SECTION": "4_CLINICAL_TRIALS_GCI", "Status": "No active trials found"}])

            # Pathways Block (PMI)
            if not pmi_df.empty:
                pmi_export = pmi_df.copy()
                pmi_export["SECTION"] = "5_BIOLOGICAL_PATHWAYS_PMI"
            else:
                pmi_export = pd.DataFrame([{"SECTION": "5_BIOLOGICAL_PATHWAYS_PMI", "Status": "No pathway mappings found"}])

            # 2. Consolidated CSV Buffer Function
            def create_full_orchestra_report():
                output = io.StringIO()
                # Global Header
                output.write(f"MAESTRO FULL INTELLIGENCE DOSSIER - HUB: {search_query}\n")
                output.write(f"Project: Omikron Orchestra v20.6\n")
                output.write(f"Generated: {timestamp}\n\n")
                
                output.write("--- SECTION 1: CORE ANALYTICS (AXON) ---\n")
                df_hub_core.to_csv(output, index=False)
                
                output.write("\n--- SECTION 2: MOLECULAR NEIGHBORS (TOP-K) ---\n")
                neighbors_export.to_csv(output, index=False)
                
                output.write("\n--- SECTION 3: PHARMACOLOGICAL LANDSCAPE (ODI) ---\n")
                odi_export.to_csv(output, index=False)
                
                output.write("\n--- SECTION 4: REGISTERED CLINICAL TRIALS (GCI) ---\n")
                gci_export.to_csv(output, index=False)
                
                output.write("\n--- SECTION 5: BIOLOGICAL PATHWAYS (PMI) ---\n")
                pmi_export.to_csv(output, index=False)
                
                return output.getvalue()

            # 3. Download Execution
            full_report_data = create_full_orchestra_report()
            
            st.download_button(
                label="📊 Download Full Intelligence Dossier (.csv)",
                data=full_report_data,
                file_name=f"MAESTRO_Full_Dossier_{search_query}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                help="Export a complete dossier including AXON, Neighbors, ODI, GCI and PMI."
            )

# --- 6. NETWORK MAP & RANKING ---
st.divider()

if df.empty or ("error" in df.columns):
    st.stop()

# Hub Mode: network = hub + neighbors
if search_query:
    neighbors_df = get_first_neighbors(df, search_query, top_k, min_sig, max_t)
    hub_df = df[df["target_id"] == search_query]
    if not hub_df.empty and not neighbors_df.empty:
        filtered_df = pd.concat([hub_df, neighbors_df], ignore_index=True)
    else:
        filtered_df = hub_df
else:
    filtered_df = df[(df["initial_score"] >= min_sig) & (df["toxicity_index"] <= max_t)]

if not filtered_df.empty:
    st.subheader("🕸️ Network Interaction Map")
    
    

    G = nx.Graph()

    # Nodes
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

    # Edges
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
    fig_net.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#444", width=0.9),
        hoverinfo="none"
    ))

    fig_net.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes],
        y=[pos[n][1] for n in nodes],
        mode="markers+text",
        text=nodes,
        textposition="top center",
        textfont=dict(size=10, color="white"),
        marker=dict(
            size=[G.nodes[n]["size"] for n in nodes],
            color=[G.nodes[n]["color"] for n in nodes],
            colorscale="RdYlGn_r",
            showscale=True,
            line=dict(
                width=[3 if G.nodes[n].get("is_hub") else 1 for n in nodes],
                color="white"
            )
        ),
        hovertemplate="<b>%{text}</b><extra></extra>"
    ))

    fig_net.update_layout(
        showlegend=False,
        margin=dict(b=0, l=0, r=0, t=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=500
    )
    st.plotly_chart(fig_net, use_container_width=True)

    st.subheader("📊 Hub Signal Ranking")
    
    

    fig_bar = px.bar(
        filtered_df.sort_values("initial_score", ascending=True).tail(15),
        x="initial_score",
        y="target_id",
        orientation="h",
        color="toxicity_index",
        color_continuous_scale="RdYlGn_r",
        template="plotly_dark"
    )
    fig_bar.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No data available with current filters.")

# --- 7. HUB INTELLIGENCE DESK ---
if search_query:
    st.divider()
    st.subheader(f"📂 Hub Intelligence Desk: {search_query}")
    c_odi, c_gci, c_pmi = st.columns(3)

    with c_odi:
        st.markdown(f"### 💊 Therapeutics (ODI: {len(odi_df)})")
        if not odi_df.empty:
            for _, r in odi_df.iterrows():
                with st.expander(f"**{r.get('Generic_Name', 'N/A')}**"):
                    st.write(f"**Class:** {r.get('Drug_Class', 'N/A')}")
                    st.write(f"**Mechanism:** {r.get('Description_L0', 'Details not available.')}")
                    st.caption(f"Status: {r.get('Regulatory_Status_US', 'N/A')}")
        else:
            st.info("No ODI items found.")

    with c_gci:
        st.markdown(f"### 🧪 Clinical Trials (GCI: {len(gci_df)})")
        if not gci_df.empty:
            for _, r in gci_df.iterrows():
                with st.expander(f"**Phase {r.get('Phase', 'N/A')} Trial**"):
                    st.write(f"**ID:** {r.get('NCT_Number', 'N/A')}")
                    st.write(f"**Title:** {r.get('Canonical_Title', 'Details not available.')}")
        else:
            st.info("No GCI trials found.")

    with c_pmi:
        st.markdown(f"### 🧬 Pathways (PMI: {len(pmi_df)})")
        if not pmi_df.empty:
            for _, r in pmi_df.iterrows():
                with st.expander(f"**{r.get('Canonical_Name', 'N/A')}**"):
                    st.write(f"**Detail:** {r.get('Description_L0', 'Details not available.')}")
        else:
            st.info("No PMI pathways found.")

# --- 8. FOOTER & DISCLAIMER ---
st.divider()
st.subheader("📚 MAESTRO Intelligence Repository")
exp1, exp2, exp3 = st.columns(3)
with exp1:
    with st.expander("🛡️ AXON Intelligence (OMI/BCI)"):
        st.write("OMI: Target Detection Hub. BCI: Biological Cost Index.")
with exp2:
    with st.expander("💊 ODI & PMI Systems"):
        st.write("ODI: Pharmaceutical Database. PMI: Pathway Mappings.")
with exp3:
    with st.expander("🧪 GCI & TMI (Clinical/Safety)"):
        st.write("GCI: Clinical Trial Monitoring. TMI: Toxicity Index.")

st.markdown(f"""
<div style="background-color: #0e1117; padding: 25px; border-radius: 12px; border: 1px solid #333; text-align: center; max-width: 900px; margin: 0 auto; margin-top: 20px;">
    <h4 style="color: #ff4b4b; margin-top: 0;">⚠️ SCIENTIFIC AND LEGAL DISCLAIMER</h4>
    <p style="font-size: 0.8rem; color: #888; text-align: justify; line-height: 1.5;">
        <b>MAESTRO Omikron Suite</b> is intended exclusively for Research Use Only (RUO). 
        Generated analyses do not replace medical advice. Data reflects the current state of Omikron databases.
    </p>
    <p style="font-size: 0.75rem; color: #444; margin-top: 15px;">
        MAESTRO v20.6 | © 2026 Omikron Orchestra Project | Powered by AXON Intelligence
    </p>
</div>
""", unsafe_allow_html=True)











