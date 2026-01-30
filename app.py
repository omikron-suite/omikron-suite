# --- AGGIORNAMENTO SEZIONE CARTIGLIO (Punto 5) ---
if search_query and not target_data.empty:
    st.markdown(f"## 🏎️ Mission Control: {search_query}")
    
    # RIGA 1: IL MOTORE (OMI, ODI, SMI)
    st.subheader("⚙️ Meccanica Molecolare")
    c1, c2, c3 = st.columns(3)
    c1.metric("OMI (Biomarker)", "Detected", help="Presenza del biomarcatore nel tumore")
    c2.metric("SMI (Pathway)", "High Activity", help="Gli Ingranaggi: stato della segnalazione")
    c3.metric("ODI (Drug)", "Inhibitor Available", help="Il Freno: farmaci associati")

    # RIGA 2: SICUREZZA E TELAIO (TMI, GNI, BCI)
    st.subheader("🛡️ Sicurezza e Struttura")
    c4, c5, c6 = st.columns(3)
    c4.metric("TMI (Tossicità)", "OK", delta="-0.12", delta_color="inverse", help="La Spia d'Emergenza")
    c5.metric("GNI (Genetica)", "Stable", help="Il Telaio: genetica dell'ospite")
    c6.metric("BCI (Bio-cost.)", "Balanced", help="L'Additivo: olio biologico")

    # RIGA 3: AMBIENTE (EVI, MBI, GCI)
    st.subheader("🌍 Fattori Esterni e Strada")
    c7, c8, c9 = st.columns(3)
    c7.metric("EVI (Ambiente)", "Low Risk", help="Il Terreno: impatto dei tossici")
    c8.metric("MBI (Microbiota)", "Resilient", help="Il Filtro aria: stato del microbiota")
    c9.metric("GCI (Clinica)", "Phase III", help="La Prova su Strada: evidenza clinica")
    
    st.divider()
