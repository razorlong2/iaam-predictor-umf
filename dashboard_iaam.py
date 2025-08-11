#!/usr/bin/env python3
"""
EpiAI - Predictor IAAM
Dr. Boghian Lucian - UMF Iași
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import json

st.set_page_config(
    page_title="🏥 EpiAI - IAAM Predictor",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .risk-critical {
        background: #ff4757;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .risk-high {
        background: #ff6348;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .risk-moderate {
        background: #ffa502;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .risk-low {
        background: #26de81;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .metric-box {
        background: #f1f2f6;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border-left: 4px solid #5f27cd;
    }
</style>
""", unsafe_allow_html=True)

# PROFILE REZISTENȚĂ BACTERII
REZISTENTA_PROFILE = {
    "Escherichia coli": ["ESBL", "CRE", "AmpC", "NDM-1"],
    "Klebsiella pneumoniae": ["ESBL", "CRE", "KPC", "NDM", "OXA-48"],
    "Pseudomonas aeruginosa": ["MDR", "XDR", "PDR", "Carbapenemază"],
    "Acinetobacter baumannii": ["OXA-23", "OXA-24", "OXA-58", "MDR", "XDR"],
    "Staphylococcus aureus": ["MRSA", "VISA", "VRSA", "CA-MRSA"],
    "Enterococcus faecalis": ["VRE", "Ampicilină-R", "HLAR"],
    "Enterococcus faecium": ["VRE", "Ampicilină-R", "Linezolid-R"],
    "Clostridioides difficile": ["NAP1/027", "Ribotip 078", "Binar toxin+"],
    "Stenotrophomonas maltophilia": ["SXT-R", "Levofloxacin-R"],
    "Candida auris": ["Fluconazol-R", "Pan-azol-R", "Echinocandin-R"]
}

# ICD-10 CODURI
ICD_CODES = {
    "Bacteriemie": "A41.9",
    "Pneumonie nosocomiala": "J15.9",
    "ITU nosocomiala": "N39.0",
    "Infecție CVC": "T80.2",
    "Infecție plagă operatorie": "T81.4",
    "Clostridium difficile": "A04.7",
    "Sepsis": "A41.9",
    "Șoc septic": "R57.2"
}

# COMORBIDITĂȚI DETALIATE
COMORBIDITATI = {
    "Cardiovascular": {
        "Insuficiență cardiacă": {"NYHA II": 5, "NYHA III": 10, "NYHA IV": 15},
        "Cardiopatie ischemică": 8,
        "Aritmii": 5,
        "HTA necontrolată": 6
    },
    "Respirator": {
        "BPOC": {"Gold I-II": 5, "Gold III": 10, "Gold IV": 15},
        "Astm bronșic": 5,
        "Fibroză pulmonară": 12,
        "Pneumopatie interstițială": 10
    },
    "Metabolic": {
        "Diabet zaharat": {"Tip 1": 10, "Tip 2 controlat": 5, "Tip 2 necontrolat": 12},
        "Obezitate": {"BMI 30-35": 3, "BMI 35-40": 5, "BMI >40": 8},
        "Sindrom metabolic": 6
    },
    "Renal": {
        "BCR stadiul 3": 8,
        "BCR stadiul 4": 12,
        "BCR stadiul 5": 15,
        "Dializă": 20
    },
    "Oncologic": {
        "Neoplasm activ": 15,
        "Chimioterapie actuală": 20,
        "Radioterapie": 12,
        "Neutropenie": 25
    },
    "Imunologic": {
        "HIV/SIDA": 20,
        "Transplant organ": 18,
        "Imunosupresie medicamentoasă": 15,
        "Splenectomie": 10
    }
}

def calculeaza_sofa(date):
    """Calculează scorul SOFA"""
    scor = 0
    
    # Respirator
    pao2_fio2 = date.get('pao2_fio2', 400)
    if pao2_fio2 < 400: scor += 1
    if pao2_fio2 < 300: scor += 1
    if pao2_fio2 < 200: scor += 1
    if pao2_fio2 < 100: scor += 1
    
    # Coagulare
    trombocite = date.get('trombocite', 200)
    if trombocite < 150: scor += 1
    if trombocite < 100: scor += 1
    if trombocite < 50: scor += 1
    if trombocite < 20: scor += 1
    
    # Hepatic
    bilirubina = date.get('bilirubina', 1.0)
    if bilirubina > 1.2: scor += 1
    if bilirubina > 2.0: scor += 1
    if bilirubina > 6.0: scor += 1
    if bilirubina > 12.0: scor += 1
    
    # Cardiovascular
    if date.get('hipotensiune'): scor += 2
    if date.get('vasopresoare'): scor += 3
    
    # SNC - Glasgow
    glasgow = date.get('glasgow', 15)
    if glasgow < 15: scor += 1
    if glasgow < 13: scor += 1
    if glasgow < 10: scor += 1
    if glasgow < 6: scor += 1
    
    # Renal
    creatinina = date.get('creatinina', 1.0)
    if creatinina > 1.2: scor += 1
    if creatinina > 2.0: scor += 1
    if creatinina > 3.5: scor += 1
    if creatinina > 5.0: scor += 1
    
    return scor

def calculeaza_qsofa(date):
    """Quick SOFA"""
    scor = 0
    if date.get('tas', 120) < 100: scor += 1
    if date.get('fr', 16) >= 22: scor += 1
    if date.get('glasgow', 15) < 15: scor += 1
    return scor

def analiza_sediment_urinar(date):
    """Analizează sedimentul urinar"""
    interpretare = []
    risc_itu = 0
    
    leucocite = date.get('leu_urina', 0)
    eritrocite = date.get('eri_urina', 0)
    bacterii = date.get('bact_urina', 0)
    celule_epiteliale = date.get('cel_epit', 0)
    cilindri = date.get('cilindri', False)
    cristale = date.get('cristale', '')
    nitriti = date.get('nitriti', False)
    esteraza = date.get('esteraza', False)
    
    # Leucocite
    if leucocite > 5:
        interpretare.append(f"Leucociturie: {leucocite}/câmp")
        risc_itu += 20
    if leucocite > 10:
        interpretare.append("Piurie semnificativă")
        risc_itu += 15
    
    # Bacteriurie
    if bacterii > 2:
        interpretare.append(f"Bacteriurie: {bacterii}+")
        risc_itu += 15
    
    # Nitriti & Esterază
    if nitriti:
        interpretare.append("Nitriti pozitivi - bacterii Gram negative")
        risc_itu += 25
    if esteraza:
        interpretare.append("Esterază leucocitară pozitivă")
        risc_itu += 20
    
    # Hematurie
    if eritrocite > 3:
        interpretare.append(f"Hematurie: {eritrocite}/câmp")
        if eritrocite > 50:
            interpretare.append("⚠️ Hematurie macroscopică - investigații suplimentare")
    
    # Cilindri
    if cilindri:
        tip_cilindri = date.get('tip_cilindri', '')
        if 'hialini' in tip_cilindri:
            interpretare.append("Cilindri hialini - posibil normal")
        elif 'granulari' in tip_cilindri:
            interpretare.append("Cilindri granulari - afectare tubulară")
            risc_itu += 10
        elif 'leucocitari' in tip_cilindri:
            interpretare.append("Cilindri leucocitari - pielonefrită")
            risc_itu += 30
    
    # Cristale
    if cristale:
        interpretare.append(f"Cristale: {cristale}")
        if 'struvit' in cristale.lower():
            interpretare.append("Cristale struvit - bacterii urează pozitive")
            risc_itu += 15
    
    # Celule epiteliale
    if celule_epiteliale > 5:
        interpretare.append("Contaminare probabilă - recoltare necorespunzătoare")
        risc_itu -= 10
    
    return interpretare, max(0, min(100, risc_itu))

def calculeaza_iaam_avansat(date):
    """Calculator avansat IAAM"""
    scor = 0
    detalii = []
    
    # CRITERIU TEMPORAL
    ore = date.get('ore_spitalizare', 0)
    if ore < 48:
        return 0, "NU IAAM", [], []
    
    if 48 <= ore < 72:
        scor += 5
        detalii.append(f"Timp spitalizare {ore}h: +5p")
    elif ore < 168:
        scor += 10
        detalii.append(f"Timp spitalizare {ore}h: +10p")
    else:
        scor += 15
        detalii.append(f"Timp spitalizare {ore}h: +15p")
    
    # DISPOZITIVE CU DURATĂ
    dispozitive = date.get('dispozitive', {})
    for disp, info in dispozitive.items():
        if info['prezent']:
            zile = info.get('zile', 0)
            punctaj_baza = {
                'CVC': 20, 'Ventilație': 25, 'Sondă urinară': 15,
                'Traheostomie': 20, 'Drenaj': 10, 'PEG': 12
            }.get(disp, 5)
            
            # Punctaj suplimentar pentru durată
            if zile > 7:
                punctaj_baza += 10
            elif zile > 3:
                punctaj_baza += 5
            
            scor += punctaj_baza
            detalii.append(f"{disp} ({zile} zile): +{punctaj_baza}p")
    
    # BACTERIE CU PROFIL REZISTENȚĂ
    if date.get('cultura_pozitiva'):
        bacterie = date.get('bacterie', '')
        profil_rezistenta = date.get('profil_rezistenta', [])
        
        if bacterie:
            scor += 15
            detalii.append(f"Cultură pozitivă - {bacterie}: +15p")
            
            for rezistenta in profil_rezistenta:
                punctaj_rezistenta = {
                    'ESBL': 15, 'CRE': 25, 'KPC': 30, 'NDM': 35,
                    'MRSA': 20, 'VRE': 25, 'XDR': 30, 'PDR': 40
                }.get(rezistenta, 10)
                scor += punctaj_rezistenta
                detalii.append(f"Profil {rezistenta}: +{punctaj_rezistenta}p")
    
    # SCORURI SEVERITATE
    sofa = calculeaza_sofa(date)
    if sofa > 0:
        scor += sofa * 3
        detalii.append(f"SOFA {sofa}: +{sofa*3}p")
    
    qsofa = calculeaza_qsofa(date)
    if qsofa >= 2:
        scor += 15
        detalii.append(f"qSOFA {qsofa}: +15p")
    
    # SEDIMENT URINAR
    if date.get('analiza_urina'):
        _, risc_itu = analiza_sediment_urinar(date.get('sediment', {}))
        if risc_itu > 50:
            scor += 10
            detalii.append(f"Risc ITU înalt ({risc_itu}%): +10p")
    
    # COMORBIDITĂȚI DETALIATE
    for categorie, boli in date.get('comorbiditati', {}).items():
        for boala, severitate in boli.items():
            if severitate:
                punctaj = COMORBIDITATI.get(categorie, {}).get(boala, 5)
                if isinstance(punctaj, dict):
                    punctaj = punctaj.get(severitate, 5)
                scor += punctaj
                detalii.append(f"{boala} ({severitate}): +{punctaj}p")
    
    # NIVEL RISC
    if scor >= 100:
        nivel = "CRITIC"
    elif scor >= 75:
        nivel = "FOARTE ÎNALT"
    elif scor >= 50:
        nivel = "ÎNALT"
    elif scor >= 30:
        nivel = "MODERAT"
    else:
        nivel = "SCĂZUT"
    
    # RECOMANDĂRI
    recomandari = []
    if scor >= 100:
        recomandari = [
            "🚨 ALERTĂ CPIAAM IMEDIATĂ",
            "🧪 Screening MDR complet urgent",
            "🔒 Izolare strictă + precauții contact",
            "💊 Antibioterapie empirică largă urgentă",
            "📋 Formular CNAS tip A - urgență"
        ]
    elif scor >= 75:
        recomandari = [
            "⚠️ Consultare infectionist în 2h",
            "🧪 Culturi complete + antibiogramă",
            "🔒 Izolare preventivă",
            "📋 Raportare INSP în 24h"
        ]
    elif scor >= 50:
        recomandari = [
            "👁️ Supraveghere activă IAAM",
            "🧪 Recoltare culturi țintite",
            "📊 Monitorizare parametri la 8h",
            "📋 Completare fișă supraveghere"
        ]
    else:
        recomandari = [
            "📊 Monitorizare standard",
            "🧤 Precauții standard",
            "📋 Documentare în foaia de observație"
        ]
    
    return scor, nivel, detalii, recomandari

def genereaza_formular_cnas(date, tip="A"):
    """Generează date pentru formular CNAS"""
    formular = {
        "tip": tip,
        "data": datetime.now().strftime("%d.%m.%Y"),
        "ora": datetime.now().strftime("%H:%M"),
        "cnp": date.get("cnp", ""),
        "nume": date.get("nume_pacient", ""),
        "diagnostic_principal": date.get("diagnostic", ""),
        "cod_icd": ICD_CODES.get(date.get("tip_infectie", ""), "A41.9"),
        "servicii": [],
        "investigatii": []
    }
    
    # Adaugă servicii necesare
    if date.get("cultura_pozitiva"):
        formular["servicii"].append("Hemocultură")
        formular["investigatii"].append("Antibiogramă")
    
    if date.get("scor_iaam", 0) >= 75:
        formular["servicii"].append("Consultație interdisciplinară")
        formular["investigatii"].append("Screening MDR")
    
    return formular

def genereaza_raport_insp(date):
    """Generează raport pentru INSP"""
    raport = {
        "unitate": "UMF Iași",
        "sectie": date.get("sectie", "ATI"),
        "data_raportare": datetime.now().isoformat(),
        "tip_infectie": date.get("tip_infectie", ""),
        "agent_patogen": date.get("bacterie", "Neidentificat"),
        "profil_rezistenta": date.get("profil_rezistenta", []),
        "masuri_luate": [],
        "cod_icd": ICD_CODES.get(date.get("tip_infectie", ""), "A41.9")
    }
    
    # Măsuri în funcție de severitate
    scor = date.get("scor_iaam", 0)
    if scor >= 75:
        raport["masuri_luate"].extend([
            "Izolare pacient",
            "Precauții contact stricte",
            "Antibioterapie țintită",
            "Screening contacti"
        ])
    
    if date.get("profil_rezistenta"):
        raport["alerta_rezistenta"] = True
        raport["tip_alerta"] = "MDR" if len(date.get("profil_rezistenta", [])) >= 3 else "Rezistență"
    
    return raport

def main():
    st.markdown("""
    <div class="header">
        <h1>🦠 EpiAI - Predictor IAAM</h1>
        <p>Dr. Boghian Lucian | UMF Iași | Epidemiologie</p>
    </div>
    """, unsafe_allow_html=True)
    
    # SIDEBAR
    st.sidebar.header("📋 Date Pacient")
    
    # Date identificare
    nume_pacient = st.sidebar.text_input("Nume/Cod", "Pacient_001")
    cnp = st.sidebar.text_input("CNP (opțional)", "")
    sectie = st.sidebar.selectbox("Secție", ["ATI", "Chirurgie", "Medicină Internă", "Pediatrie", "Neonatologie"])
    
    # Timp spitalizare
    ore_spitalizare = st.sidebar.number_input("Ore de la internare", 0, 720, 96)
    
    # DISPOZITIVE CU DURATĂ
    st.sidebar.subheader("🔧 Dispozitive Invazive")
    dispozitive = {}
    
    for disp in ['CVC', 'Ventilație', 'Sondă urinară', 'Traheostomie', 'Drenaj', 'PEG']:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            prezent = st.checkbox(disp, key=f"disp_{disp}")
        with col2:
            if prezent:
                zile = st.number_input(f"Zile {disp}", 0, 30, 3, key=f"zile_{disp}")
            else:
                zile = 0
        dispozitive[disp] = {'prezent': prezent, 'zile': zile}
    
    # COMORBIDITĂȚI ORGANIZATE
    st.sidebar.subheader("🩺 Comorbidități")
    comorbiditati_selectate = {}
    
    for categorie in ["Cardiovascular", "Respirator", "Metabolic", "Renal", "Oncologic", "Imunologic"]:
        with st.sidebar.expander(f"{categorie}"):
            comorbiditati_selectate[categorie] = {}
            for boala in COMORBIDITATI[categorie]:
                if isinstance(COMORBIDITATI[categorie][boala], dict):
                    severitate = st.selectbox(
                        boala,
                        ["Nu"] + list(COMORBIDITATI[categorie][boala].keys()),
                        key=f"comorb_{categorie}_{boala}"
                    )
                    if severitate != "Nu":
                        comorbiditati_selectate[categorie][boala] = severitate
                else:
                    if st.checkbox(boala, key=f"comorb_{categorie}_{boala}"):
                        comorbiditati_selectate[categorie][boala] = True
    
    # SCORURI SEVERITATE
    st.sidebar.subheader("📊 Scoruri Severitate")
    
    with st.sidebar.expander("SOFA"):
        pao2_fio2 = st.number_input("PaO2/FiO2", 100, 500, 400)
        trombocite = st.number_input("Trombocite (×10³)", 20, 500, 200)
        bilirubina = st.number_input("Bilirubină (mg/dl)", 0.0, 20.0, 1.0)
        glasgow = st.number_input("Glasgow", 3, 15, 15)
        creatinina = st.number_input("Creatinină (mg/dl)", 0.5, 10.0, 1.0)
        hipotensiune = st.checkbox("Hipotensiune")
        vasopresoare = st.checkbox("Vasopresoare")
    
    with st.sidebar.expander("qSOFA"):
        tas = st.number_input("TAS (mmHg)", 60, 200, 120)
        fr = st.number_input("FR (/min)", 8, 40, 18)
    
    # MICROBIOLOGIE
    st.sidebar.subheader("🦠 Microbiologie")
    cultura_pozitiva = st.sidebar.checkbox("Cultură pozitivă")
    
    bacterie = ""
    profil_rezistenta = []
    
    if cultura_pozitiva:
        bacterie = st.sidebar.selectbox("Bacterie", [""] + list(REZISTENTA_PROFILE.keys()))
        if bacterie and bacterie in REZISTENTA_PROFILE:
            profil_rezistenta = st.sidebar.multiselect(
                "Profil rezistență",
                REZISTENTA_PROFILE[bacterie]
            )
    
    # SEDIMENT URINAR
    st.sidebar.subheader("🔬 Sediment Urinar")
    analiza_urina = st.sidebar.checkbox("Analiză urinară disponibilă")
    
    sediment = {}
    if analiza_urina:
        with st.sidebar.expander("Detalii sediment"):
            sediment['leu_urina'] = st.number_input("Leucocite/câmp", 0, 100, 5)
            sediment['eri_urina'] = st.number_input("Eritrocite/câmp", 0, 100, 1)
            sediment['bact_urina'] = st.slider("Bacterii", 0, 4, 0)
            sediment['cel_epit'] = st.number_input("Celule epiteliale/câmp", 0, 20, 2)
            sediment['nitriti'] = st.checkbox("Nitriti pozitivi")
            sediment['esteraza'] = st.checkbox("Esterază leucocitară")
            sediment['cilindri'] = st.checkbox("Cilindri prezenți")
            if sediment['cilindri']:
                sediment['tip_cilindri'] = st.text_input("Tip cilindri")
            sediment['cristale'] = st.text_input("Cristale (dacă există)")
    
    # TIP INFECȚIE pentru ICD
    st.sidebar.subheader("📋 Tip Infecție")
    tip_infectie = st.sidebar.selectbox("Tip infecție suspectată", list(ICD_CODES.keys()))
    
    # BUTON CALCUL
    if st.sidebar.button("🔍 CALCULEAZĂ RISC", type="primary"):
        
        # Pregătire date
        date_calcul = {
            'nume_pacient': nume_pacient,
            'cnp': cnp,
            'sectie': sectie,
            'ore_spitalizare': ore_spitalizare,
            'dispozitive': dispozitive,
            'comorbiditati': comorbiditati_selectate,
            'pao2_fio2': pao2_fio2,
            'trombocite': trombocite,
            'bilirubina': bilirubina,
            'glasgow': glasgow,
            'creatinina': creatinina,
            'hipotensiune': hipotensiune,
            'vasopresoare': vasopresoare,
            'tas': tas,
            'fr': fr,
            'cultura_pozitiva': cultura_pozitiva,
            'bacterie': bacterie,
            'profil_rezistenta': profil_rezistenta,
            'analiza_urina': analiza_urina,
            'sediment': sediment,
            'tip_infectie': tip_infectie
        }
        
        # Calcul scor
        scor, nivel, detalii, recomandari = calculeaza_iaam_avansat(date_calcul)
        date_calcul['scor_iaam'] = scor
        
        if scor == 0:
            st.error("❌ Nu îndeplinește criteriul temporal IAAM (< 48h)")
        else:
            # AFIȘARE REZULTATE
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-box">
                    <h2>{scor}</h2>
                    <p>Scor Total</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-box">
                    <h3>{nivel}</h3>
                    <p>Nivel Risc</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                sofa_scor = calculeaza_sofa(date_calcul)
                st.markdown(f"""
                <div class="metric-box">
                    <h2>{sofa_scor}</h2>
                    <p>SOFA</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                qsofa_scor = calculeaza_qsofa(date_calcul)
                st.markdown(f"""
                <div class="metric-box">
                    <h2>{qsofa_scor}</h2>
                    <p>qSOFA</p>
                </div>
                """, unsafe_allow_html=True)
            
            # ALERTĂ RISC
            risk_class = {
                "CRITIC": "risk-critical",
                "FOARTE ÎNALT": "risk-high",
                "ÎNALT": "risk-high",
                "MODERAT": "risk-moderate",
                "SCĂZUT": "risk-low"
            }.get(nivel, "risk-low")
            
            st.markdown(f'<div class="{risk_class}">🚨 Risc {nivel} - Scor: {scor} puncte</div>', 
                       unsafe_allow_html=True)
            
            # TABS
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Detalii", "💊 Recomandări", "🔬 Laborator", 
                "📋 Formulare", "📄 Raport"
            ])
            
            with tab1:
                st.subheader("Detalii Calcul Scor")
                for detaliu in detalii:
                    st.write(f"• {detaliu}")
                
                # Gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=scor,
                    title={'text': "Scor IAAM"},
                    gauge={
                        'axis': {'range': [0, 150]},
                        'bar': {'color': "red" if scor >= 75 else "orange" if scor >= 50 else "yellow" if scor >= 30 else "green"},
                        'steps': [
                            {'range': [0, 30], 'color': "lightgreen"},
                            {'range': [30, 50], 'color': "yellow"},
                            {'range': [50, 75], 'color': "orange"},
                            {'range': [75, 150], 'color': "lightcoral"}
                        ]
                    }
                ))
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.subheader("💊 Recomandări Clinice")
                for rec in recomandari:
                    st.write(rec)
                
                # Recomandări antibiotice bazate pe bacterie
                if bacterie:
                    st.subheader("💊 Antibioterapie Recomandată")
                    antibiotice = {
                        "Escherichia coli": ["Meropenem", "Piperacilină-Tazobactam", "Amikacin"],
                        "Klebsiella pneumoniae": ["Meropenem", "Colistin", "Tigecyclină"],
                        "Pseudomonas aeruginosa": ["Ceftazidim-Avibactam", "Meropenem", "Colistin"],
                        "Acinetobacter baumannii": ["Colistin", "Tigecyclină", "Ampicilină-Sulbactam"],
                        "Staphylococcus aureus": ["Vancomicină", "Linezolid", "Daptomicină"],
                        "Enterococcus faecalis": ["Ampicilină", "Vancomicină", "Linezolid"],
                        "Enterococcus faecium": ["Vancomicină", "Linezolid", "Daptomicină"]
                    }
                    
                    if bacterie in antibiotice:
                        for atb in antibiotice[bacterie]:
                            if profil_rezistenta:
                                st.warning(f"• {atb} (verificați sensibilitatea - profil {', '.join(profil_rezistenta)})")
                            else:
                                st.success(f"• {atb}")
            
            with tab3:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🦠 Microbiologie")
                    if cultura_pozitiva:
                        st.info(f"**Bacterie:** {bacterie}")
                        if profil_rezistenta:
                            st.error(f"**Rezistențe:** {', '.join(profil_rezistenta)}")
                    else:
                        st.warning("Fără cultură pozitivă")
                
                with col2:
                    st.subheader("🔬 Sediment Urinar")
                    if analiza_urina:
                        interpretare, risc_itu = analiza_sediment_urinar(sediment)
                        
                        if risc_itu >= 70:
                            st.error(f"Risc ITU: {risc_itu}% - ÎNALT")
                        elif risc_itu >= 40:
                            st.warning(f"Risc ITU: {risc_itu}% - MODERAT")
                        else:
                            st.success(f"Risc ITU: {risc_itu}% - SCĂZUT")
                        
                        for interp in interpretare:
                            st.write(f"• {interp}")
                    else:
                        st.info("Analiză nedisponibilă")
            
            with tab4:
                st.subheader("📋 Formulare Administrative")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📄 Formular CNAS**")
                    formular_cnas = genereaza_formular_cnas(date_calcul)
                    
                    st.write(f"• Tip formular: {formular_cnas['tip']}")
                    st.write(f"• Cod ICD-10: {formular_cnas['cod_icd']}")
                    st.write(f"• Diagnostic: {tip_infectie}")
                    
                    if formular_cnas['servicii']:
                        st.write("**Servicii necesare:**")
                        for serv in formular_cnas['servicii']:
                            st.write(f"  - {serv}")
                    
                    # Buton descărcare formular
                    formular_json = json.dumps(formular_cnas, indent=2, ensure_ascii=False)
                    st.download_button(
                        "📥 Descarcă Date CNAS",
                        formular_json,
                        f"cnas_{nume_pacient}_{datetime.now().strftime('%Y%m%d')}.json",
                        "application/json"
                    )
                
                with col2:
                    st.markdown("**📊 Raport INSP**")
                    raport_insp = genereaza_raport_insp(date_calcul)
                    
                    st.write(f"• Cod ICD-10: {raport_insp['cod_icd']}")
                    st.write(f"• Agent patogen: {raport_insp['agent_patogen']}")
                    
                    if raport_insp.get('alerta_rezistenta'):
                        st.error(f"⚠️ ALERTĂ {raport_insp['tip_alerta']}")
                    
                    if raport_insp['masuri_luate']:
                        st.write("**Măsuri implementate:**")
                        for masura in raport_insp['masuri_luate']:
                            st.write(f"  - {masura}")
                    
                    # Buton descărcare raport INSP
                    raport_json = json.dumps(raport_insp, indent=2, ensure_ascii=False)
                    st.download_button(
                        "📥 Descarcă Raport INSP",
                        raport_json,
                        f"insp_{nume_pacient}_{datetime.now().strftime('%Y%m%d')}.json",
                        "application/json"
                    )
            
            with tab5:
                st.subheader("📄 Raport Complet")
                
                # Generare raport text
                raport = f"""
RAPORT EVALUARE RISC IAAM - EpiAI
=====================================
Data: {datetime.now().strftime('%d.%m.%Y %H:%M')}
Unitate: UMF Iași
Medic: Dr. Boghian Lucian

IDENTIFICARE PACIENT
--------------------
Nume/Cod: {nume_pacient}
CNP: {cnp if cnp else 'Nedeclarat'}
Secție: {sectie}
Ore spitalizare: {ore_spitalizare}h

REZULTATE EVALUARE
------------------
Scor IAAM: {scor} puncte
Nivel risc: {nivel}
SOFA: {calculeaza_sofa(date_calcul)}
qSOFA: {calculeaza_qsofa(date_calcul)}

DISPOZITIVE INVAZIVE
--------------------"""
                
                for disp, info in dispozitive.items():
                    if info['prezent']:
                        raport += f"\n• {disp}: {info['zile']} zile"
                
                if cultura_pozitiva:
                    raport += f"""

MICROBIOLOGIE
-------------
Bacterie: {bacterie}
Profil rezistență: {', '.join(profil_rezistenta) if profil_rezistenta else 'Nedeterminat'}"""
                
                if analiza_urina:
                    interpretare, risc_itu = analiza_sediment_urinar(sediment)
                    raport += f"""

ANALIZĂ URINARĂ
---------------
Risc ITU: {risc_itu}%
Interpretare:"""
                    for interp in interpretare:
                        raport += f"\n• {interp}"
                
                raport += f"""

CODIFICARE
----------
ICD-10: {ICD_CODES.get(tip_infectie, 'A41.9')}
Tip infecție: {tip_infectie}

RECOMANDĂRI
-----------"""
                for rec in recomandari:
                    raport += f"\n{rec}"
                
                raport += f"""

VALIDARE
--------
Conform: Ord. MS 1101/2016
Protocol: ECDC HAI-Net v5.3
Sistem: EpiAI v1.0

Dr. Boghian Lucian
UMF "Grigore T. Popa" Iași
                """
                
                # Afișare raport
                st.text_area("", raport, height=400)
                
                # Butoane export
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        "📥 Descarcă TXT",
                        raport,
                        f"raport_{nume_pacient}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        "text/plain"
                    )
                
                with col2:
                    # Export JSON complet
                    date_export = {
                        **date_calcul,
                        'scor': scor,
                        'nivel': nivel,
                        'detalii': detalii,
                        'recomandari': recomandari,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    st.download_button(
                        "📥 Descarcă JSON",
                        json.dumps(date_export, indent=2, ensure_ascii=False),
                        f"date_{nume_pacient}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                        "application/json"
                    )
                
                with col3:
                    # Export CSV pentru statistici
                    df_export = pd.DataFrame([{
                        'pacient': nume_pacient,
                        'sectie': sectie,
                        'data': datetime.now().strftime('%Y-%m-%d'),
                        'ora': datetime.now().strftime('%H:%M'),
                        'scor_iaam': scor,
                        'nivel_risc': nivel,
                        'sofa': calculeaza_sofa(date_calcul),
                        'qsofa': calculeaza_qsofa(date_calcul),
                        'bacterie': bacterie,
                        'rezistente': ', '.join(profil_rezistenta),
                        'cod_icd': ICD_CODES.get(tip_infectie, 'A41.9')
                    }])
                    
                    st.download_button(
                        "📊 Descarcă CSV",
                        df_export.to_csv(index=False),
                        f"stats_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
    
    # INFORMAȚII GENERALE
    st.markdown("---")
    
    with st.expander("ℹ️ Ghid Rapid"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📊 Interpretare Scor**
            - 0-29p: Risc scăzut
            - 30-49p: Risc moderat
            - 50-74p: Risc înalt
            - 75-99p: Risc foarte înalt
            - ≥100p: Risc critic
            """)
        
        with col2:
            st.markdown("""
            **🦠 Profile Rezistență**
            - ESBL: Beta-lactamaze spectru extins
            - CRE: Enterobacterii carbapenem-rezistente
            - MRSA: S. aureus meticilino-rezistent
            - VRE: Enterococ vancomicino-rezistent
            - XDR: Rezistență extinsă
            """)
        
        with col3:
            st.markdown("""
            **📋 Coduri ICD-10**
            - A41.9: Septicemie
            - J15.9: Pneumonie bacteriană
            - N39.0: ITU
            - T80.2: Infecție CVC
            - A04.7: C. difficile
            """)

if __name__ == "__main__":
    main()
