#!/usr/bin/env python3
"""
EpiMind - IAAM Predictor (complete academic UI)
UMF "Grigore T. Popa" Iași
Single-file Streamlit app with Notion Dark theme
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# ---------------- Page config ----------------
st.set_page_config(
    page_title="EpiMind — IAAM Predictor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Assets (local images) ----------------
LOGO_FILE = "1fc80c62-72a4-49d0-a088-f496b5930eac.png"
SIDEBAR_DECOR = "4fbe00b9-c580-463a-8538-5ae75595b360.png"

LOGO_EXISTS = Path(LOGO_FILE).exists()
SIDEBAR_DECOR_EXISTS = Path(SIDEBAR_DECOR).exists()

# ---------------- Notion Dark CSS ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp { background-color: #0f0f10 !important; color: #FFFFFF !important; font-family: 'Inter', sans-serif !important; }
.main .block-container { padding: 1rem 2rem !important; max-width: 1400px; }

.header-panel { background: linear-gradient(135deg,#16223b,#0b2743); border-radius:12px; padding:18px; margin-bottom:14px; border:1px solid #2b2b2b; }
.logo-box { width:88px; height:88px; border-radius:14px; background: linear-gradient(135deg,#2D4A87,#1E3A5F); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:20px; border:2px solid rgba(255,255,255,0.06); }

.notion-section { background: rgba(22,22,22,0.6); border:1px solid #272727; border-radius:10px; padding:14px; margin-bottom:12px; }
.section-title { font-size:16px; color:#eaf2ff; font-weight:700; margin-bottom:10px; display:flex; gap:10px; align-items:center; }

.feature { background: rgba(31,31,31,0.6); border:1px solid #2f2f2f; padding:12px; border-radius:8px; }
.feature small { color:#9fb0c6; }

.stTextInput > label, .stNumberInput > label, .stSelectbox > label, .stCheckbox > label { color:#9aa4b2 !important; font-size:13px !important; font-weight:600 !important; }
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
    background:#0f1316 !important; color:#fff !important; border:1px solid #2b2b2b !important; border-radius:8px !important; padding:8px 10px !important;
}

.primary-button { background: linear-gradient(135deg,#2383E2,#1a6bb8) !important; color: white !important; padding:12px 18px !important; border-radius:10px !important; font-weight:700 !important; width:100% !important; }

.metric-card { background: rgba(19,19,19,0.6); border:1px solid #232323; border-radius:10px; padding:12px; text-align:center; }
.metric-value { color:#2383E2; font-size:28px; font-weight:800; }

.risk-alert { padding:12px; border-radius:10px; margin:8px 0; font-weight:700; }
.risk-critical { background: rgba(220,38,38,0.09); border-left:4px solid #DC2626; color:#fecaca; }
.risk-high { background: rgba(245,101,101,0.06); border-left:4px solid #F56565; color:#ffd6d6; }
.risk-moderate { background: rgba(251,191,36,0.06); border-left:4px solid #FBBF24; color:#fff4d1; }
.risk-low { background: rgba(34,197,94,0.06); border-left:4px solid #22C55E; color:#d7ffe6; }

.data-item { background: rgba(31,31,31,0.6); border:1px solid #2b2b2b; border-radius:8px; padding:10px; margin:8px 0; color:#cbd5e1; }
.small-muted { color:#9aa4b2; font-size:13px; }

#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------- Domain data (profiles, ICD, comorbid) ----------------
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

# ---------------- Clinical calculators (same logic as provided, robust) ----------------
def calculeaza_sofa(date):
    scor = 0
    pao2_fio2 = date.get('pao2_fio2', 400)
    if pao2_fio2 < 400: scor += 1
    if pao2_fio2 < 300: scor += 1
    if pao2_fio2 < 200: scor += 1
    if pao2_fio2 < 100: scor += 1

    trombocite = date.get('trombocite', 200)
    if trombocite < 150: scor += 1
    if trombocite < 100: scor += 1
    if trombocite < 50: scor += 1
    if trombocite < 20: scor += 1

    bilirubina = date.get('bilirubina', 1.0)
    if bilirubina > 1.2: scor += 1
    if bilirubina > 2.0: scor += 1
    if bilirubina > 6.0: scor += 1
    if bilirubina > 12.0: scor += 1

    if date.get('hipotensiune'): scor += 2
    if date.get('vasopresoare'): scor += 3

    glasgow = date.get('glasgow', 15)
    if glasgow < 15: scor += 1
    if glasgow < 13: scor += 1
    if glasgow < 10: scor += 1
    if glasgow < 6: scor += 1

    creatinina = date.get('creatinina', 1.0)
    if creatinina > 1.2: scor += 1
    if creatinina > 2.0: scor += 1
    if creatinina > 3.5: scor += 1
    if creatinina > 5.0: scor += 1

    return scor

def calculeaza_qsofa(date):
    scor = 0
    if date.get('tas', 120) < 100: scor += 1
    if date.get('fr', 16) >= 22: scor += 1
    if date.get('glasgow', 15) < 15: scor += 1
    return scor

def analiza_sediment_urinar(date):
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

    if leucocite > 5:
        interpretare.append(f"Leucociturie: {leucocite}/câmp")
        risc_itu += 20
    if leucocite > 10:
        interpretare.append("Piurie semnificativă")
        risc_itu += 15

    if bacterii > 2:
        interpretare.append(f"Bacteriurie: {bacterii}+")
        risc_itu += 15

    if nitriti:
        interpretare.append("Nitriti pozitivi - bacterii Gram negative")
        risc_itu += 25
    if esteraza:
        interpretare.append("Esterază leucocitară pozitivă")
        risc_itu += 20

    if eritrocite > 3:
        interpretare.append(f"Hematurie: {eritrocite}/câmp")
        if eritrocite > 50:
            interpretare.append("⚠️ Hematurie macroscopică - investigații suplimentare")

    if cilindri:
        tip_cilindri = date.get('tip_cilindri', '').lower()
        if 'hialin' in tip_cilindri:
            interpretare.append("Cilindri hialini - posibil normal")
        elif 'granular' in tip_cilindri:
            interpretare.append("Cilindri granulari - afectare tubulară")
            risc_itu += 10
        elif 'leucocitari' in tip_cilindri:
            interpretare.append("Cilindri leucocitari - pielonefrită")
            risc_itu += 30

    if cristale:
        interpretare.append(f"Cristale: {cristale}")
        if 'struvit' in cristale.lower():
            interpretare.append("Cristale struvit - bacterii urează pozitive")
            risc_itu += 15

    if celule_epiteliale > 5:
        interpretare.append("Contaminare probabilă - recoltare necorespunzătoare")
        risc_itu -= 10

    return interpretare, max(0, min(100, risc_itu))

def calculeaza_iaam_avansat(date):
    scor = 0
    detalii = []

    ore = date.get('ore_spitalizare', 0)
    if ore < 48:
        return 0, "NU IAAM", [], []

    # temporal
    if 48 <= ore < 72:
        scor += 5
        detalii.append(f"Timp spitalizare {ore}h: +5p")
    elif ore < 168:
        scor += 10
        detalii.append(f"Timp spitalizare {ore}h: +10p")
    else:
        scor += 15
        detalii.append(f"Timp spitalizare {ore}h: +15p")

    # dispozitive
    dispozitive = date.get('dispozitive', {})
    for disp, info in dispozitive.items():
        if info.get('prezent'):
            zile = info.get('zile', 0)
            punctaj_baza = {
                'CVC': 20, 'Ventilație': 25, 'Sondă urinară': 15,
                'Traheostomie': 20, 'Drenaj': 10, 'PEG': 12
            }.get(disp, 5)
            if zile > 7:
                punctaj_baza += 10
            elif zile > 3:
                punctaj_baza += 5
            scor += punctaj_baza
            detalii.append(f"{disp} ({zile} zile): +{punctaj_baza}p")

    # cultura
    if date.get('cultura_pozitiva'):
        bacterie = date.get('bacterie', '')
        profil_rezistenta = date.get('profil_rezistenta', [])
        if bacterie:
            scor += 15
            detalii.append(f"Cultură pozitivă - {bacterie}: +15p")
            for rez in profil_rezistenta:
                punctaj_rezistenta = {
                    'ESBL': 15, 'CRE': 25, 'KPC': 30, 'NDM': 35,
                    'MRSA': 20, 'VRE': 25, 'XDR': 30, 'PDR': 40
                }.get(rez, 10)
                scor += punctaj_rezistenta
                detalii.append(f"Profil {rez}: +{punctaj_rezistenta}p")

    # severitate
    sofa = calculeaza_sofa(date)
    if sofa > 0:
        scor += sofa * 3
        detalii.append(f"SOFA {sofa}: +{sofa*3}p")

    qsofa = calculeaza_qsofa(date)
    if qsofa >= 2:
        scor += 15
        detalii.append(f"qSOFA {qsofa}: +15p")

    # analiza urina
    if date.get('analiza_urina'):
        _, risc_itu = analiza_sediment_urinar(date.get('sediment', {}))
        if risc_itu > 50:
            scor += 10
            detalii.append(f"Risc ITU înalt ({risc_itu}%): +10p")

    # comorbiditati
    for categorie, boli in date.get('comorbiditati', {}).items():
        for boala, severitate in boli.items():
            if severitate:
                punctaj = COMORBIDITATI.get(categorie, {}).get(boala, 5)
                if isinstance(punctaj, dict):
                    punctaj = punctaj.get(severitate, 5)
                try:
                    add = int(punctaj)
                except:
                    add = 5
                scor += add
                detalii.append(f"{boala} ({severitate}): +{add}p")

    # nivel
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

    # recomandari
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

# ---------------- Helpers to collect inputs & render ----------------
def init_session_defaults():
    defaults = {
        'nume_pacient': 'Pacient_001',
        'cnp': '',
        'sectie': 'ATI',
        'ore_spitalizare': 96,
        'pao2_fio2': 400,
        'trombocite': 200,
        'bilirubina': 1.0,
        'glasgow': 15,
        'creatinina': 1.0,
        'hipotensiune': False,
        'vasopresoare': False,
        'tas': 120,
        'fr': 18,
        'cultura_pozitiva': False,
        'bacterie': '',
        'profil_rezistenta': [],
        'tip_infectie': list(ICD_CODES.keys())[0],
        'comorbiditati_selectate': {},
        'analiza_urina': False,
        'sediment': {}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def collect_payload():
    # patient basics
    payload = {
        'nume_pacient': st.session_state.get('nume_pacient', 'Pacient_001'),
        'cnp': st.session_state.get('cnp', ''),
        'sectie': st.session_state.get('sectie', 'ATI'),
        'ore_spitalizare': st.session_state.get('ore_spitalizare', 96),
    }
    # devices
    devices_list = ['CVC', 'Ventilație', 'Sondă urinară', 'Traheostomie', 'Drenaj', 'PEG']
    dispozitive = {}
    for d in devices_list:
        dispozitive[d] = {
            'prezent': st.session_state.get(f"disp_{d}", False),
            'zile': st.session_state.get(f"zile_{d}", 0)
        }
    payload['dispozitive'] = dispozitive
    # scores
    payload.update({
        'pao2_fio2': st.session_state.get('pao2_fio2', 400),
        'trombocite': st.session_state.get('trombocite', 200),
        'bilirubina': st.session_state.get('bilirubina', 1.0),
        'glasgow': st.session_state.get('glasgow', 15),
        'creatinina': st.session_state.get('creatinina', 1.0),
        'hipotensiune': st.session_state.get('hipotensiune', False),
        'vasopresoare': st.session_state.get('vasopresoare', False),
        'tas': st.session_state.get('tas', 120),
        'fr': st.session_state.get('fr', 18),
    })
    # microbio
    payload['cultura_pozitiva'] = st.session_state.get('cultura_pozitiva', False)
    payload['bacterie'] = st.session_state.get('bacterie', '')
    payload['profil_rezistenta'] = st.session_state.get('profil_rezistenta', [])
    payload['tip_infectie'] = st.session_state.get('tip_infectie', list(ICD_CODES.keys())[0])
    # comorbid
    payload['comorbiditati'] = st.session_state.get('comorbiditati_selectate', {})
    # urina
    payload['analiza_urina'] = st.session_state.get('analiza_urina', False)
    payload['sediment'] = st.session_state.get('sediment', {})
    return payload

def render_header():
    st.markdown('<div class="header-panel">', unsafe_allow_html=True)
    cols = st.columns([1, 5])
    with cols[0]:
        if LOGO_EXISTS:
            st.image(LOGO_FILE, width=84)
        else:
            st.markdown('<div class="logo-box">UMF</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown('<div style="font-size:18px;color:#eaf2ff;font-weight:700;">EpiMind — IAAM Predictor (Prototip Academic)</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-muted">Platformă dezvoltată în cadrul UMF "Grigore T. Popa" Iași • Conform ECDC HAI-Net v5.3</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Page renderers ----------------
def page_home():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏠 Despre EpiMind</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="color:#bfd0e6">
      <strong>EpiMind</strong> este un instrument academic pentru evaluarea predictivă a riscului de infecții asociate asistenței medicale (IAAM).
      Completează datele pacientului din secțiunile laterale (Date pacient, Microbiologie, Scoruri etc.) și apasă <strong>📊 Evaluează riscul IAAM</strong>.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:12px">
      <div class="feature"><strong>Evaluare IAAM</strong><br><small class="small-muted">Algoritm integrat pe protocoale ECDC</small></div>
      <div class="feature"><strong>Profilare microbiologică</strong><br><small class="small-muted">Rezistențe și ghid antibioterapie</small></div>
      <div class="feature"><strong>Interpretare laborator</strong><br><small class="small-muted">Sediment urinar, SOFA, qSOFA</small></div>
      <div class="feature"><strong>Export & Audit</strong><br><small class="small-muted">Export JSON/CSV/TXT pentru raportare</small></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_patient():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">👤 Date pacient</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2,2,2,1])
    with c1:
        st.text_input("Nume / Cod pacient", key='nume_pacient', placeholder='Pacient_001')
        st.text_input("CNP (opțional)", key='cnp')
    with c2:
        st.selectbox("Secția", ["ATI", "Chirurgie", "Medicină Internă", "Pediatrie", "Neonatologie"], key='sectie')
        st.number_input("Vârsta (ani)", min_value=0, max_value=120, value=65, key='varsta')
    with c3:
        st.number_input("Ore internare", min_value=0, max_value=10000, value=96, key='ore_spitalizare')
        st.selectbox("Tip internare", ["Programat", "Urgent"], key='tip_internare')
    with c4:
        st.date_input("Data evaluării", key='data_evaluare')
        st.text_input("Cod pacient intern", key='cod_intern')
    st.markdown('<div class="small-muted">Completează informațiile de pacient pentru contextul clinic.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_devices():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔧 Dispozitive invazive</div>', unsafe_allow_html=True)
    devices = ['CVC', 'Ventilație', 'Sondă urinară', 'Traheostomie', 'Drenaj', 'PEG']
    cols = st.columns(3)
    for i, d in enumerate(devices):
        with cols[i % 3]:
            prez = st.checkbox(f"{d}", key=f"disp_{d}")
            if prez:
                st.number_input("Zile", 0, 365, 3, key=f"zile_{d}")
    st.markdown('<div class="small-muted">Important: durata și prezența dispozitivelor cresc riscul IAAM.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_severity():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Scoruri severitate</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("SOFA components")
        st.number_input("PaO2/FiO2", 50, 500, 400, key='pao2_fio2', help="Raport PaO2/FiO2 - respirator")
        st.number_input("Trombocite (x10^3/µL)", 0, 1000, 200, key='trombocite')
        st.number_input("Bilirubină (mg/dL)", 0.0, 30.0, 1.0, key='bilirubina')
    with col2:
        st.subheader("Neurologie & Rinichi")
        st.number_input("Glasgow", 3, 15, 15, key='glasgow')
        st.number_input("Creatinină (mg/dL)", 0.1, 20.0, 1.0, key='creatinina')
        st.checkbox("Hipotensiune (TAS<90)", key='hipotensiune')
        st.checkbox("Vasopresoare", key='vasopresoare')
    st.markdown('<div class="small-muted">qSOFA: TAS &lt;100, FR ≥22, scădere de stare mentală.</div>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        st.number_input("TAS (mmHg)", 40, 220, 120, key='tas')
    with col4:
        st.number_input("FR (/min)", 8, 60, 18, key='fr')
    st.markdown('</div>', unsafe_allow_html=True)

def page_microbiology():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🦠 Microbiologie</div>', unsafe_allow_html=True)
    cultura = st.checkbox("Cultură pozitivă", key='cultura_pozitiva')
    if cultura:
        st.selectbox("Agent patogen", [""] + list(REZISTENTA_PROFILE.keys()), key='bacterie')
        selected = st.session_state.get('bacterie', '')
        if selected:
            st.multiselect("Profil rezistență", REZISTENTA_PROFILE.get(selected, []), key='profil_rezistenta')
    st.selectbox("Tip infecție (ICD-10)", list(ICD_CODES.keys()), key='tip_infectie')
    st.markdown('<div class="small-muted">Dacă nu există izolată, lăsați "Cultură pozitivă" nebifată.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_comorbidities():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🩺 Comorbidități</div>', unsafe_allow_html=True)
    com_select = {}
    cols = st.columns(3)
    cats = list(COMORBIDITATI.keys())
    for i, cat in enumerate(cats):
        with cols[i % 3]:
            with st.expander(f"{cat}", expanded=False):
                for cond, val in COMORBIDITATI[cat].items():
                    keyname = f"com_{cat}_{cond}"
                    if isinstance(val, dict):
                        choice = st.selectbox(cond, ["Nu"] + list(val.keys()), key=keyname)
                        if choice and choice != "Nu":
                            com_select.setdefault(cat, {})[cond] = choice
                    else:
                        b = st.checkbox(cond, key=keyname)
                        if b:
                            com_select.setdefault(cat, {})[cond] = True
    st.session_state['comorbiditati_selectate'] = com_select
    st.markdown('<div class="small-muted">Alege comorbiditățile relevante și severitatea acolo unde este cazul.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_urinalysis():
    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔬 Analiză urinară</div>', unsafe_allow_html=True)
    st.checkbox("Analiză urinară disponibilă", key='analiza_urina')
    if st.session_state.get('analiza_urina', False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input("Leucocite / câmp", 0, 200, 5, key='leu_urina')
            st.number_input("Eritrocite / câmp", 0, 200, 1, key='eri_urina')
            st.slider("Bacterii (0-4+)", 0, 4, 0, key='bact_urina')
        with c2:
            st.number_input("Celule epiteliale", 0, 50, 2, key='cel_epit')
            st.checkbox("Nitriti +", key='nitriti')
            st.checkbox("Esterază +", key='esteraza')
        with c3:
            st.checkbox("Cilindri", key='cilindri')
            if st.session_state.get('cilindri', False):
                st.text_input("Tip cilindri", key='tip_cilindri')
            st.text_input("Cristale (descriere)", key='cristale')
        # persist sediment
        st.session_state['sediment'] = {
            'leu_urina': st.session_state.get('leu_urina', 0),
            'eri_urina': st.session_state.get('eri_urina', 0),
            'bact_urina': st.session_state.get('bact_urina', 0),
            'cel_epit': st.session_state.get('cel_epit', 0),
            'nitriti': st.session_state.get('nitriti', False),
            'esteraza': st.session_state.get('esteraza', False),
            'cilindri': st.session_state.get('cilindri', False),
            'tip_cilindri': st.session_state.get('tip_cilindri', ''),
            'cristale': st.session_state.get('cristale', '')
        }
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Sidebar navigation ----------------
def sidebar():
    st.sidebar.markdown("<div style='padding:6px 8px'><strong style='font-size:14px;color:#eaf2ff;'>Meniu secțiuni</strong></div>", unsafe_allow_html=True)
    pages = [
        ("🏠 Pagina principală", "home"),
        ("👤 Date pacient", "patient"),
        ("🔧 Dispozitive invazive", "devices"),
        ("📊 Scoruri severitate", "severity"),
        ("🦠 Microbiologie", "microbio"),
        ("🩺 Comorbidități", "comorbid"),
        ("🔬 Analiză urinară", "urine")
    ]
    opts = [p[0] for p in pages]
    sel = st.sidebar.radio("Selectează secțiunea", opts, index=0)
    # map selected to page id
    page_map = dict(pages)
    st.session_state['current_page'] = page_map[sel]

    st.sidebar.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    # prominent compute button
    if st.sidebar.button("📊 Evaluează riscul IAAM", key='compute'):
        # compute immediately and display results (store in session)
        payload = collect_payload()
        scor, nivel, detalii, recomandari = calculeaza_iaam_avansat(payload)
        st.session_state['last_result'] = {
            'payload': payload,
            'scor': scor,
            'nivel': nivel,
            'detalii': detalii,
            'recomandari': recomandari,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state['current_page'] = 'results'
    st.sidebar.markdown("<hr style='border-color:#2b2b2b'/>", unsafe_allow_html=True)
    if SIDEBAR_DECOR_EXISTS:
        st.sidebar.image(SIDEBAR_DECOR, use_column_width=True)
    st.sidebar.markdown("<div style='font-size:12px;color:#9aa4b2;margin-top:6px;'>EpiMind • UMF Iași • Demo academic</div>", unsafe_allow_html=True)

# ---------------- Results renderer ----------------
def render_results():
    last = st.session_state.get('last_result', None)
    if not last:
        st.warning("Nu există rezultate disponibile. Completează formularele și apasă 'Evaluează riscul IAAM' în sidebar.")
        return
    payload = last['payload']
    scor = last['scor']
    nivel = last['nivel']
    detalii = last['detalii']
    recomandari = last['recomandari']

    st.markdown('<div class="notion-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 Rezultate evaluare IAAM</div>', unsafe_allow_html=True)

    # metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{scor}</div><div class="small-muted">Scor IAAM</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div style="font-size:16px;font-weight:700;color:#fff;">{nivel}</div><div class="small-muted">Nivel risc</div></div>', unsafe_allow_html=True)
    with c3:
        sofa_val = calculeaza_sofa(payload)
        st.markdown(f'<div class="metric-card"><div class="metric-value">{sofa_val}</div><div class="small-muted">SOFA</div></div>', unsafe_allow_html=True)
    with c4:
        qsofa_val = calculeaza_qsofa(payload)
        st.markdown(f'<div class="metric-card"><div class="metric-value">{qsofa_val}</div><div class="small-muted">qSOFA</div></div>', unsafe_allow_html=True)

    # risk banner
    risk_class = {
        "CRITIC": "risk-critical",
        "FOARTE ÎNALT": "risk-high",
        "ÎNALT": "risk-high",
        "MODERAT": "risk-moderate",
        "SCĂZUT": "risk-low"
    }.get(nivel, "risk-low")
    st.markdown(f'<div class="risk-alert {risk_class}">🚨 <strong>RISC {nivel}</strong> — Scor total: {scor} puncte</div>', unsafe_allow_html=True)

    # tabs: analysis, recommendations, lab, export
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analiză", "💊 Recomandări", "🔬 Laborator", "📋 Export"])

    with tab1:
        st.markdown("**Componente scor IAAM**")
        if detalii:
            for d in detalii:
                st.markdown(f"<div class='data-item'>{d}</div>", unsafe_allow_html=True)
            # small breakdown table
            df = pd.DataFrame({'Componentă': [d.split(':')[0] for d in detalii],
                               'Descriere': [d for d in detalii]})
            st.markdown("**Sumar componente**")
            st.dataframe(df, use_container_width=True, height=220)
        else:
            st.info("Nu există componente detaliate.")

        # gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=scor,
            domain={'x':[0,1],'y':[0,1]},
            title={'text': "Scor IAAM"},
            gauge={
                'axis': {'range':[0,150]},
                'bar': {'color': "#DC2626" if scor>=75 else "#F59E0B" if scor>=50 else "#10B981"},
                'steps': [
                    {'range':[0,30],'color': "rgba(16, 185, 129, 0.15)"},
                    {'range':[30,50],'color': "rgba(245, 158, 11, 0.12)"},
                    {'range':[50,75],'color': "rgba(239, 68, 68, 0.12)"},
                    {'range':[75,150],'color': "rgba(220, 38, 38, 0.12)"}
                ]
            }
        ))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=340, margin=dict(t=30,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("**Recomandări clinice prioritare**")
        for i, r in enumerate(recomandari, 1):
            st.markdown(f"{i}. {r}")

        # example targeted antibiotics (simple heuristics)
        agent = payload.get('bacterie', '')
        if agent:
            st.markdown("**Sugestii empirice (exemplu)**")
            # small mapping for example only
            atb_map = {
                "Escherichia coli": ["Meropenem 1g IV q8h", "Piperacilină-Tazobactam 4.5g IV q6h"],
                "Klebsiella pneumoniae": ["Meropenem 2g IV perfuzie", "Colistin (dacă MDR)"],
                "Pseudomonas aeruginosa": ["Ceftazidim/Avibactam 2.5g", "Meropenem 2g perfuzie"]
            }
            for atb in atb_map.get(agent, ["Consultați antibiograma locală"]):
                st.markdown(f"- {atb}")

    with tab3:
        st.markdown("**Microbiologie & Analiză urinară**")
        if payload.get('cultura_pozitiva'):
            st.markdown(f"- Agent: **{payload.get('bacterie')}**")
            rez = payload.get('profil_rezistenta', [])
            st.markdown(f"- Rezistențe: {', '.join(rez) if rez else '—'}")
        else:
            st.markdown("- Fără izolat disponibil")

        if payload.get('analiza_urina'):
            interp, risc_itu = analiza_sediment_urinar(payload.get('sediment', {}))
            st.markdown(f"- Probabilitate ITU: **{risc_itu}%**")
            for it in interp:
                st.markdown(f"  - {it}")
        else:
            st.markdown("- Analiză urinară nedisponibilă")

    with tab4:
        st.markdown("**Export rapoarte**")
        raport = {
            'meta': {
                'app': 'EpiMind',
                'version': 'demo',
                'timestamp': last['timestamp']
            },
            'pacient': payload,
            'result': {
                'scor': scor,
                'nivel': nivel,
                'detalii': detalii,
                'recomandari': recomandari
            }
        }
        st.download_button("📥 Descarcă raport JSON", json.dumps(raport, ensure_ascii=False, indent=2), file_name=f"epimind_report_{payload.get('nume_pacient')}_{datetime.now().strftime('%Y%m%d')}.json", use_container_width=True)
        df_export = pd.DataFrame([{
            'data': datetime.now().strftime('%Y-%m-%d'),
            'pacient': payload.get('nume_pacient'),
            'sectie': payload.get('sectie'),
            'ore_spitalizare': payload.get('ore_spitalizare'),
            'scor_iaam': scor,
            'nivel_risc': nivel,
            'sofa': sofa_val,
            'qsofa': qsofa_val,
            'agent': payload.get('bacterie'),
            'rezistente': ', '.join(payload.get('profil_rezistenta', [])),
            'infectie': payload.get('tip_infectie'),
            'cod_icd': ICD_CODES.get(payload.get('tip_infectie'), '')
        }])
        st.download_button("📈 Descarcă CSV statistici", df_export.to_csv(index=False), file_name=f"epimind_stats_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Main ----------------
def main():
    init_session_defaults()
    render_header()
    sidebar()

    page = st.session_state.get('current_page', 'home')
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if page == 'home':
        page_home()
    elif page == 'patient':
        page_patient()
    elif page == 'devices':
        page_devices()
    elif page == 'severity':
        page_severity()
    elif page == 'microbio':
        page_microbiology()
    elif page == 'comorbid':
        page_comorbidities()
    elif page == 'urine':
        page_urinalysis()
    elif page == 'results':
        render_results()
    else:
        st.info("Pagina nu există")

    # small help
    with st.expander("ℹ️ Ghid rapid EpiMind", expanded=False):
        st.markdown("""
        • Completează secțiunile din meniul lateral (Date pacient, Dispozitive, Scoruri, Microbiologie, Comorbidități, Analiză urinară).  
        • Apasă **📊 Evaluează riscul IAAM** din bara laterală pentru a rula analiza agregată.  
        • Rezultatele sunt afișate în pagina *Rezultate* cu export JSON/CSV/TXT.  
        • Atenție: aceasta este o aplicație demonstrativă; deciziile clinice se iau conform protocolului local.
        """)

    st.markdown("""
    <div style="text-align:center;padding:12px;margin-top:12px;color:#9aa4b2;font-size:12px;border-top:1px solid #222;">
      EpiMind • UMF "Grigore T. Popa" Iași — Demo academic • Conform ECDC HAI-Net v5.3
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
