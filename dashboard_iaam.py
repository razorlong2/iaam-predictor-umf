#!/usr/bin/env python3
# coding: utf-8
"""
EpiMind — IAAM Predictor (Single-file, Professional, Mobile-friendly)
UMF "Grigore T. Popa" Iași — Dr. Boghian Lucian
Version: 2.1.0 — Complete single-file Streamlit application

Features added in this version:
 - Academic, richly-documented homepage (no logos) explaining methods, scope and use.
 - Detailed, well-documented functions for SOFA, qSOFA, APACHE-like score, urinary sediment analysis,
   Charlson-like comorbidity processing and the IAAM deterministic risk engine.
 - Custom toggleable navigation (works reliably on mobile and desktop) — avoids Streamlit sidebar reopen bug.
 - Responsive CSS tuned for phones and small screens; layout collapses gracefully.
 - Audit log (local CSV), JSON/CSV export, and short CSV report generation.
 - Clear tooltips/help text for nearly every input.
 - Cleaner imports and removed unused code; structured and commented for academic presentation.

Notes:
 - This is a demonstrative clinical support tool. It does not replace clinical judgement.
 - Keep data local; for production integrate authentication and encrypted storage.

To run:
    streamlit run EpiMind_IAAM_Predictor_Full.py

"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime
from pathlib import Path
import os
from typing import Dict, List, Tuple, Any, Optional

# ---------------- App configuration ----------------
APP_TITLE = "EpiMind — IAAM Predictor"
APP_ICON = "🏥"
VERSION = "2.1.0"
AUDIT_CSV = "epimind_audit.csv"
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide", initial_sidebar_state="collapsed")

# ---------------- Minimal responsive CSS (improved) ----------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    :root{--bg:#071019;--card:#0f1720;--muted:#9fb0c6;--accent:#1f78d1;--accent-2:#00a859;--danger:#dc2626;}
    body {background: linear-gradient(180deg,#061018,#08121a) !important; color: #EAF2FF;}
    .stApp { font-family: 'Inter', sans-serif; }
    .header { padding:12px; border-radius:10px; background: linear-gradient(90deg, rgba(31,120,209,0.04), rgba(0,168,89,0.02)); margin-bottom:12px; border:1px solid rgba(255,255,255,0.02);}    
    .title { font-weight:700; font-size:20px; color:#EAF2FF; }
    .subtitle { color:var(--muted); font-size:13px; margin-top:4px }
    .card { background: var(--card); border-radius:10px; padding:14px; border:1px solid rgba(255,255,255,0.02); color:#EAF2FF; }
    .metric { text-align:center; padding:8px; border-radius:8px; background: rgba(255,255,255,0.01); }
    .metric-value { font-weight:800; font-size:26px; color:var(--accent); }
    .small-muted { color: var(--muted); font-size:12px; }
    .risk-alert { padding:12px; border-radius:8px; font-weight:700; margin-bottom:8px; }
    .risk-critical { background: rgba(220,38,38,0.08); border-left:4px solid var(--danger); color:#fecaca; }
    .risk-high { background: rgba(245,158,11,0.06); border-left:4px solid #F59E0B; color:#fff4d1; }
    .risk-moderate { background: rgba(59,130,246,0.05); border-left:4px solid #3B82F6; color:#cfe6ff; }
    .risk-low { background: rgba(16,185,129,0.05); border-left:4px solid #10B981; color:#d7ffe6; }
    .muted-box { background: rgba(255,255,255,0.01); border-radius:8px; padding:8px; }

    /* Mobile tweaks */
    @media (max-width: 760px) {
      .title { font-size:18px; }
      .metric-value { font-size:20px; }
      .card { padding:10px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Domain knowledge (concise but extensible) ----------------
REZISTENTA_PROFILE = {
    "Escherichia coli": ["ESBL", "CRE", "AmpC", "NDM-1", "CTX-M"],
    "Klebsiella pneumoniae": ["ESBL", "CRE", "KPC", "NDM", "OXA-48"],
    "Pseudomonas aeruginosa": ["MDR", "XDR", "PDR"],
    "Acinetobacter baumannii": ["OXA-23", "OXA-24", "MDR"],
    "Staphylococcus aureus": ["MRSA", "VISA"],
    "Enterococcus faecalis": ["VRE"],
    "Candida auris": ["Fluconazol-R", "Echinocandin-R"]
}

ICD_CODES = {
    "Bacteriemie/Septicemie": "A41.9",
    "Pneumonie nosocomială": "J15.9",
    "ITU nosocomială": "N39.0",
    "Infecție CVC": "T80.2",
    "Infecție plagă operatorie": "T81.4",
    "Clostridioides difficile": "A04.7",
}

COMORBIDITATI = {
    "Cardiovascular": {
        "Hipertensiune arterială": {"Controlată": 3, "Necontrolată": 6, "Criză HTA": 12},
        "Insuficiență cardiacă": {"NYHA I": 3, "NYHA II": 5, "NYHA III": 10, "NYHA IV": 15},
        "Cardiopatie ischemică": {"Stabilă": 5, "Instabilă": 10},
        "Infarct miocardic anterior": 8,
        "Intervenții coronariene" : {"PCI": 5, "CABG": 7},
        "Aritmii": {"FA paroxistică": 5, "FA permanentă": 7, "TV/TVS": 10},
        "Valvulopatii semnificative": 8,
        "Boală arterială periferică": 7,
        "Tromboembolism venos (ISTORIC)": 6
    },
    "Respirator": {
        "BPOC": {"GOLD I": 3, "GOLD II": 5, "GOLD III": 10, "GOLD IV": 15},
        "Astm bronșic": {"Controlat": 3, "Parțial controlat": 5, "Necontrolat": 8},
        "Fibroză pulmonară": 12,
        "Pneumopatie interstițială": 10,
        "HTAP (hipertensiune pulmonară)": 12,
        "Sindrom apnee somn (SAS)": 5,
        "Bronșiectazii": 7,
        "Tuberculoză pulmonară (istoric/activ)": {"Istoric": 3, "Activă": 10}
    },
    "Metabolic": {
        "Diabet zaharat": {"Tip 1": 10, "Tip 2 controlat": 5, "Tip 2 necontrolat": 12, "Cu complicații micro/macrovasculare": 15},
        "Obezitate": {"BMI 25-30": 2, "BMI 30-35": 3, "BMI 35-40": 5, "BMI >40": 8},
        "Sindrom metabolic": 6,
        "Dislipidemie": 3,
        "Steatoză/NAFLD": 4,
        "Guta/hiperuricemie": 4
    },
    "Renal": {
        "BCR stadiul 1-2": 3,
        "BCR stadiul 3a": 5,
        "BCR stadiul 3b": 8,
        "BCR stadiul 4": 12,
        "BCR stadiul 5 (insuficiență renală severă)": 15,
        "Hemodializă": 20,
        "Dializă peritoneală": 18,
        "Transplant renal": 15,
        "Proteinurie/nephropatie diabetică": 8
    },
    "Hepatic": {
        "Steatoză hepatică": 3,
        "Hepatită cronică B/C": 10,
        "Ciroză": {"Child A": 8, "Child B": 12, "Child C": 18},
        "Insuficiență hepatică acută": 20,
        "Transplant hepatic": 15
    },
    "Oncologic": {
        "Neoplasm solid activ": 15,
        "Neoplasm metastazat": 25,
        "Neoplasm hematologic": 18,
        "Chimioterapie curentă": 20,
        "Radioterapie (în curs)": 12,
        "Imunoterapie/terapii biologice": 15,
        "Neutropenie": {"<1000": 15, "<500": 25, "<100": 35},
        "Post-TCSH (transplant celule stem)": 25
    },
    "Imunologic/Infectios": {
        "HIV/SIDA": {"CD4>500": 10, "CD4 200-500": 15, "CD4<200": 25},
        "Transplant organ solid": 18,
        "Imunosupresie medicamentoasă": {"Corticoterapie": 10, "Imunosupresoare": 15, "Biologice": 12},
        "Splenectomie": 10,
        "Deficit imun primar": 20,
        "Corticoterapie cronică (doses med-high)": 10
    },
    "Neurologic": {
        "AVC recent (<3 luni)": 10,
        "AVC vechi": 5,
        "Demență": 8,
        "Boală Parkinson": 6,
        "Epilepsie": 5,
        "Scleroză multiplă": 8,
        "Leziune medulară/neurologică severă": 12
    },
    "Hematologic/Coagulare": {
        "Anemie moderată": 4,
        "Anemie severă": 8,
        "Tulburări de coagulare (hemofilie, VWD)": 10,
        "Tromboză venoasă profundă activă": 8,
        "Terapie anticoagulantă cronică": 5,
        "Hemoglobinopatii (ex. drepanocitoză)": 10
    },
    "Endocrin/Alte": {
        "Boli tiroidiene (hipo/hiper)": 3,
        "Insuficiență suprarenală": 8,
        "Sarcină": {"Trimestrul 1": 3, "Trimestrul 2": 4, "Trimestrul 3": 6},
        "Malnutriție/IMC scăzut": {"Ușoară": 3, "Moderat": 6, "Severă": 10},
        "Arsuri severe": 15,
        "Fragilitate/geriatrie": 8
    }
}


# ---------------- Calculators (detailed docstrings) ----------------

def calculate_sofa_detailed(data: Dict[str, Any]) -> Tuple[int, Dict[str, int]]:
    """
    Calculate an extended SOFA score with component breakdown.

    Parameters
    ----------
    data : dict
        Expected keys: pao2_fio2, trombocite, bilirubina, hipotensiune (bool), vasopresoare (bool), glasgow, creatinina, diureza_ml_kg_h

    Returns
    -------
    (total_score, components)
    """
    components = {"Respirator": 0, "Coagulare": 0, "Hepatic": 0, "Cardiovascular": 0, "SNC": 0, "Renal": 0}
    pao2_fio2 = data.get("pao2_fio2", 400)
    if pao2_fio2 < 400:
        components["Respirator"] = 1
    if pao2_fio2 < 300:
        components["Respirator"] = 2
    if pao2_fio2 < 200:
        components["Respirator"] = 3
    if pao2_fio2 < 100:
        components["Respirator"] = 4

    platelets = data.get("trombocite", 200)
    if platelets < 150:
        components["Coagulare"] = 1
    if platelets < 100:
        components["Coagulare"] = 2
    if platelets < 50:
        components["Coagulare"] = 3
    if platelets < 20:
        components["Coagulare"] = 4

    bilirubin = data.get("bilirubina", 1.0)
    if bilirubin >= 1.2:
        components["Hepatic"] = 1
    if bilirubin >= 2.0:
        components["Hepatic"] = 2
    if bilirubin >= 6.0:
        components["Hepatic"] = 3
    if bilirubin >= 12.0:
        components["Hepatic"] = 4

    if data.get("hipotensiune"):
        components["Cardiovascular"] = max(components["Cardiovascular"], 2)
    if data.get("vasopresoare"):
        components["Cardiovascular"] = max(components["Cardiovascular"], 3)

    glasgow = data.get("glasgow", 15)
    if glasgow < 15:
        components["SNC"] = 1
    if glasgow < 13:
        components["SNC"] = 2
    if glasgow < 10:
        components["SNC"] = 3
    if glasgow < 6:
        components["SNC"] = 4

    creatinine = data.get("creatinina", 1.0)
    urine_output = data.get("diureza_ml_kg_h", 1.0)
    if creatinine >= 1.2 or urine_output < 0.5:
        components["Renal"] = 1
    if creatinine >= 2.0:
        components["Renal"] = 2
    if creatinine >= 3.5 or urine_output < 0.3:
        components["Renal"] = 3
    if creatinine >= 5.0 or urine_output < 0.1:
        components["Renal"] = 4

    total = sum(components.values())
    return total, components


def calculate_qsofa(data: Dict[str, Any]) -> int:
    """Compute qSOFA: TAS<100, FR>=22, Glasgow<15"""
    score = 0
    tas = data.get("tas", 120)
    fr = data.get("fr", 18)
    glasgow = data.get("glasgow", 15)
    if tas < 100:
        score += 1
    if fr >= 22:
        score += 1
    if glasgow < 15:
        score += 1
    return score


def calculate_apache_like(data: Dict[str, Any]) -> int:
    """
    A simplified APACHE-II-like aggregate (for additional stratification). This is not
    a replacement for the validated APACHE II instrument but a pragmatic numerical feature.
    """
    score = 0
    temp = data.get("temperatura", 37.0)
    if temp >= 41 or temp < 30:
        score += 4
    elif 39 <= temp < 41:
        score += 3
    elif 38.5 <= temp < 39:
        score += 1
    elif 34 <= temp < 36:
        score += 1
    elif 32 <= temp < 34:
        score += 2

    mapv = data.get("tam", 70)
    if mapv >= 160:
        score += 4
    elif 130 <= mapv < 160:
        score += 3
    elif 110 <= mapv < 130:
        score += 2
    elif 50 <= mapv < 70:
        score += 2
    elif mapv < 50:
        score += 4

    hr = data.get("fc", 80)
    if hr >= 180:
        score += 4
    elif 140 <= hr < 180:
        score += 3
    elif 110 <= hr < 140:
        score += 2
    elif 55 <= hr < 70:
        score += 2
    elif 40 <= hr < 55:
        score += 3
    elif hr < 40:
        score += 4

    age = data.get("varsta")
    if isinstance(age, int):
        if age >= 75:
            score += 6
        elif age >= 65:
            score += 5
        elif age >= 55:
            score += 3
        elif age >= 45:
            score += 2
    return score


def analyze_urinary_sediment(date: Dict[str, Any]) -> Tuple[List[str], int]:
    """Detailed urinary sediment interpretation returning lines of interpretation and a risk % (0-100)."""
    interp = []
    risk = 0
    leu = date.get("leu_urina", 0)
    ery = date.get("eri_urina", 0)
    bact = date.get("bact_urina", 0)
    epit = date.get("cel_epit", 0)
    nit = date.get("nitriti", False)
    est = date.get("esteraza", False)
    cilindri = date.get("cilindri", False)
    tip = date.get("tip_cilindri", "")

    if leu > 5:
        interp.append(f"Leucociturie: {leu}/câmp")
        risk += 20
        if leu > 10:
            interp.append("Piurie semnificativă")
            risk += 15
    if bact > 0:
        interp.append(f"Bacteriurie: nivel {bact}")
        risk += bact * 8
    if nit:
        interp.append("Nitriți pozitivi — sugestiv Gram-")
        risk += 25
    if est:
        interp.append("Esterază leucocitară pozitivă")
        risk += 20
    if ery > 3:
        interp.append(f"Hematurie: {ery}/câmp")
        if ery > 50:
            interp.append("Hematurie macroscopică — investigații")
    if cilindri:
        if "leucoc" in tip.lower():
            interp.append("Cilindri leucocitari — sugestiv pielonefrită")
            risk += 30
        elif "granular" in tip.lower():
            interp.append("Cilindri granulari — afectare tubulară")
            risk += 10
        else:
            interp.append(f"Cilindri: {tip}")
            risk += 5
    if epit > 5:
        interp.append("Contaminare probabilă (celule epiteliale crescute)")
        risk = max(0, risk - 10)

    risk = max(0, min(100, int(risk)))
    return interp, risk


def calculate_charlson_like(comorbidities: Dict[str, Dict[str, Any]]) -> int:
    """Simplified Charlson-like aggregate based on the COMORBIDITATI mapping.

    The function is intentionally simple: it sums mapped weights and provides a numeric index.
    """
    score = 0
    for cat, conds in (comorbidities or {}).items():
        for cond, sev in conds.items():
            mapping = COMORBIDITATI.get(cat, {}).get(cond)
            pts = 5
            if isinstance(mapping, dict):
                pts = mapping.get(sev, 5) if isinstance(sev, str) else 5
            elif isinstance(mapping, int):
                pts = mapping
            try:
                score += int(pts)
            except Exception:
                score += 5
    return score


# ---------------- Core IAAM deterministic risk engine (well commented) ----------------

def calculate_iaam_risk(payload: Dict[str, Any]) -> Tuple[int, str, List[str], List[str]]:
    """
    Deterministic IAAM risk engine. Combines:
     - temporal criteria (>=48h hospitalization),
     - presence & duration of invasive devices,
     - microbiology (culture & resistance profile),
     - severity scores (SOFA, qSOFA) and a simplified APACHE-like score,
     - urinary sediment risk,
     - comorbidity burden.

    Returns: (numeric_score, risk_level, details_lines, recommendations)
    """
    # Quick temporal gate: if <48h, not IAAM by definition
    hours = payload.get("ore_spitalizare", 0) or 0
    details: List[str] = []
    score = 0

    if hours < 48:
        return 0, "NU IAAM (temporal)", [f"Internare {hours}h <48h: criteriu temporal negat"], ["Monitorizare clinică"]

    # Temporal contribution
    if 48 <= hours < 72:
        score += 5; details.append(f"Timp spitalizare: {hours}h (+5)")
    elif hours < 168:
        score += 10; details.append(f"Timp spitalizare: {hours}h (+10)")
    else:
        score += 15; details.append(f"Timp spitalizare: {hours}h (+15)")

    # Devices: each device has base risk; longer durations add points
    device_weights = {"CVC": 20, "Ventilatie": 25, "Sonda urinara": 15, "Traheostomie": 20, "Drenaj": 10, "PEG": 12}
    for dev, info in (payload.get("dispozitive") or {}).items():
        if info.get("prezent"):
            zile = info.get("zile", 0) or 0
            base = device_weights.get(dev, 5)
            extra = 10 if zile > 7 else 5 if zile > 3 else 0
            add = base + extra
            score += add
            details.append(f"{dev} ({zile} zile): +{add}")

    # Microbiology
    if payload.get("cultura_pozitiva"):
        agent = payload.get("bacterie", "")
        score += 15
        details.append(f"Cultură pozitivă: {agent} (+15)")
        for rez in (payload.get("profil_rezistenta") or []):
            rez_pts = {"ESBL": 15, "CRE": 25, "KPC": 30, "NDM": 35, "MRSA": 20, "VRE": 25, "XDR": 30, "PDR": 40}.get(rez, 10)
            score += rez_pts
            details.append(f"Rezistență {rez}: +{rez_pts}")

    # Severity scores
    sofa_val, sofa_comp = calculate_sofa_detailed(payload)
    if sofa_val > 0:
        score += sofa_val * 3
        details.append(f"SOFA: {sofa_val} (+{sofa_val*3})")

    qsofa_val = calculate_qsofa(payload)
    if qsofa_val >= 2:
        score += 15
        details.append(f"qSOFA: {qsofa_val} (+15)")

    # APACHE-like
    apache_val = calculate_apache_like(payload)
    if apache_val > 0:
        score += int(apache_val/2)  # contribute but less weight
        details.append(f"APACHE-like: {apache_val} (+{int(apache_val/2)})")

    # Urine
    if payload.get("analiza_urina"):
        interp, risc = analyze_urinary_sediment(payload.get("sediment", {}))
        if risc > 50:
            score += 10
            details.append(f"Risc ITU: {risc}% (+10)")
        details.extend([f"Urină: {line}" for line in interp])

    # Comorbidities
    charlson = calculate_charlson_like(payload.get("comorbiditati", {}))
    if charlson > 0:
        score += charlson
        details.append(f"Comorbidități (sumă puncte): +{charlson}")

    # Determine level and recommendations
    if score >= 100:
        level = "CRITIC"
        recs = [
            "Izolare imediată și notificare CPIAAM",
            "Consult infecționist urgent",
            "Recoltare probe și inițiere ATB empirică largă conform protocoalelor locale"
        ]
    elif score >= 75:
        level = "FOARTE ÎNALT"
        recs = ["Consult infecționist în 2h", "Recoltare culturi și antibiogramă", "Izolare preventivă"]
    elif score >= 50:
        level = "ÎNALT"
        recs = ["Supraveghere activă IAAM", "Recoltare culturi țintite", "Monitorizare parametri la 8h"]
    elif score >= 30:
        level = "MODERAT"
        recs = ["Monitorizare extinsă", "Documentare completă în fișa de observație"]
    else:
        level = "SCĂZUT"
        recs = ["Monitorizare standard", "Precauții standard"]

    return int(score), level, details, recs

# ---------------- Helpers: defaults, payload and audit ----------------

def init_defaults():
    """Initialize session state defaults to keep UI stateless and reproducible."""
    defaults = {
        'nume_pacient': 'Pacient_001', 'cnp': '', 'sectie': 'ATI',
        'ore_spitalizare': 96, 'pao2_fio2': 400, 'trombocite': 200,
        'bilirubina': 1.0, 'glasgow': 15, 'creatinina': 1.0,
        'hipotensiune': False, 'vasopresoare': False,
        'tas': 120, 'fr': 18, 'cultura_pozitiva': False,
        'bacterie': '', 'profil_rezistenta': [], 'tip_infectie': list(ICD_CODES.keys())[0],
        'comorbiditati_selectate': {}, 'analiza_urina': False, 'sediment': {},
        'show_nav': True, 'current_page': 'home', 'last_result': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def collect_payload() -> Dict[str, Any]:
    """Gather current session state into a structured payload for scoring and export."""
    payload = {
        'nume_pacient': st.session_state.get('nume_pacient'),
        'cnp': st.session_state.get('cnp'),
        'sectie': st.session_state.get('sectie'),
        'ore_spitalizare': st.session_state.get('ore_spitalizare'),
        'dispozitive': {},
        'pao2_fio2': st.session_state.get('pao2_fio2'),
        'trombocite': st.session_state.get('trombocite'),
        'bilirubina': st.session_state.get('bilirubina'),
        'glasgow': st.session_state.get('glasgow'),
        'creatinina': st.session_state.get('creatinina'),
        'hipotensiune': st.session_state.get('hipotensiune'),
        'vasopresoare': st.session_state.get('vasopresoare'),
        'tas': st.session_state.get('tas'),
        'fr': st.session_state.get('fr'),
        'cultura_pozitiva': st.session_state.get('cultura_pozitiva'),
        'bacterie': st.session_state.get('bacterie'),
        'profil_rezistenta': st.session_state.get('profil_rezistenta'),
        'tip_infectie': st.session_state.get('tip_infectie'),
        'comorbiditati': st.session_state.get('comorbiditati_selectate'),
        'analiza_urina': st.session_state.get('analiza_urina'),
        'sediment': st.session_state.get('sediment'),
    }
    devices = ['CVC', 'Ventilatie', 'Sonda urinara', 'Traheostomie', 'Drenaj', 'PEG']
    for d in devices:
        payload['dispozitive'][d] = {
            'prezent': st.session_state.get(f"disp_{d}", False),
            'zile': st.session_state.get(f"zile_{d}", 0)
        }
    return payload


def append_audit(result: Dict[str, Any]):
    """Append a single result to the local CSV audit file. Minimal columns for privacy."""
    row = {
        'timestamp': result['timestamp'],
        'pacient': result['payload'].get('nume_pacient'),
        'sectie': result['payload'].get('sectie'),
        'ore_spitalizare': result['payload'].get('ore_spitalizare'),
        'scor': result['scor'],
        'nivel': result['nivel'],
        'agent': result['payload'].get('bacterie'),
        'rezistente': ','.join(result['payload'].get('profil_rezistenta', []))
    }
    df = pd.DataFrame([row])
    if not Path(AUDIT_CSV).exists():
        df.to_csv(AUDIT_CSV, index=False)
    else:
        df.to_csv(AUDIT_CSV, mode='a', header=False, index=False)


def load_audit_df() -> pd.DataFrame:
    if Path(AUDIT_CSV).exists():
        try:
            return pd.read_csv(AUDIT_CSV)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

# ---------------- UI: header, nav, pages ----------------

def render_header():
    st.markdown('<div class="header">', unsafe_allow_html=True)
    cols = st.columns([4, 1])
    with cols[0]:
        st.markdown(f'<div class="title">{APP_TITLE} <span style="font-weight:400;font-size:12px;color:#9fb0c6">v{VERSION}</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Platformă demonstrativă — evaluare predictivă IAAM. Instrument academic pentru screening și suport decizional.</div>', unsafe_allow_html=True)
    with cols[1]:
        if st.button("☰ Meniu", key='toggle_nav'):
            st.session_state['show_nav'] = not st.session_state.get('show_nav', True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_nav():
    menu = [
        ("🏠 Pagina principală", "home"),
        ("🧾 Date pacient", "patient"),
        ("🩺 Dispozitive invazive", "devices"),
        ("📊 Scoruri severitate", "severity"),
        ("🧫 Microbiologie", "microbio"),
        ("⚕️ Comorbidități", "comorbid"),
        ("🔬 Analiză urinară", "urine"),
        ("📁 Rezultate & Istoric", "results"),
    ]
    st.markdown('<div class="card">', unsafe_allow_html=True)
    for label, key in menu:
        if st.button(label, key=f"nav_{key}" + str(key)):
            st.session_state['current_page'] = key
    st.markdown('</div>', unsafe_allow_html=True)

# Page: Home (academic & detailed)

def page_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3>EpiMind — Context, scop și metodologie</h3>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="small-muted">
        <strong>Context:</strong> Infecțiile asociate asistenței medicale (IAAM) reprezintă un risc major pentru pacient
        și o sursă semnificativă de morbiditate, mortalitate și costuri spitalicești. Screeningul proactiv facilitează
        identificarea timpurie a pacienților cu risc crescut (MDR screening, izolare, antibioterapie direcționată).
        <br/><br/>
        <strong>Scop:</strong> EpiMind oferă un instrument academic pentru triere și suport decizional bazat pe reguli
        clinice și scoruri validate (SOFA/qSOFA) combinate cu factori specifici spitalului: dispozitive invazive,
        durata internării, culturi microbiologice și comorbidități.
        <br/><br/>
        <strong>Metodologie:</strong> Motorul de evaluare este determinist — combină reguli temporale, greutăți pentru
        dispozitive invazive, penalizări pentru profiluri de rezistență și componente de severitate. Scorul rezultat
        este orientativ și trebuie interpretat în context clinic.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<hr/>', unsafe_allow_html=True)
    st.markdown('<h4>Module</h4>', unsafe_allow_html=True)
    cols = st.columns([1,1,1])
    with cols[0]:
        st.markdown('<div class="muted-box"><strong>Evaluare pacient</strong><br/>Introduceți date demografice, durata internării și secția. Validare minimală pentru simulări reproducibile.</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown('<div class="muted-box"><strong>Comorbidități</strong><br/>Catalog structurat al afecțiunilor principale (cardiovascular, respirator, metabolic etc.) cu greutăți predefinite pentru model.</div>', unsafe_allow_html=True)
    with cols[2]:
        st.markdown('<div class="muted-box"><strong>Microbiologie & Urină</strong><br/>Permite introducerea rezultatelor culturilor, profilurilor de rezistență și interpretarea sedimentului urinar pentru suspiciune ITU.</div>', unsafe_allow_html=True)

    st.markdown('<hr/>', unsafe_allow_html=True)
    st.markdown('<h4>Componente detaliate evaluate</h4>', unsafe_allow_html=True)
    st.markdown(
        """
        <ul class="small-muted">
          <li><strong>Timp de internare</strong> — criteriu temporal IAAM (>=48h)</li>
          <li><strong>Dispozitive invazive</strong> — CVC, ventilație mecanică, sondă urinară, traheostomie etc. (durata influențează riscul)</li>
          <li><strong>Scoruri de severitate</strong> — SOFA (detaliat), qSOFA, APACHE-like (simplificat)</li>
          <li><strong>Microbiologie</strong> — cultură pozitivă, profil de rezistență (ESBL/CRE/KPC/MRSA etc.)</li>
          <li><strong>Comorbidități</strong> — sumar ponderat în stil Charlson-like pentru evaluare a vulnerabilității</li>
          <li><strong>Analiză urinară</strong> — interpretare sediment, nitriți, esteraă, poziționare rezultatelor</li>
        </ul>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<hr/>', unsafe_allow_html=True)
    st.markdown('<div class="small-muted">Documentație: acest instrument servește ca suport academic. În mediul clinic producție se recomandă validare locală, audit regulat, criptare a datelor și control de acces.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Other pages (streamlined but with details) ----------------

def page_patient():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>Date pacient</h4>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3,2,2])
    with c1:
        st.text_input('Nume / Cod pacient *', key='nume_pacient', placeholder='Pacient_001', help='Identificator pentru raport. Nu încărca date personale sensibile în demo.')
        st.text_input('CNP (opțional)', key='cnp', help='Dacă este necesar pentru evidență locală — atenție la confidențialitate')
        st.selectbox('Secția', ['ATI','Chirurgie','Medicină Internă','Pediatrie','Neonatologie'], key='sectie')
    with c2:
        st.number_input('Ore internare *', min_value=0, max_value=10000, value=st.session_state.get('ore_spitalizare',96), key='ore_spitalizare', help='Criteriu temporal: IAAM >=48h')
        st.selectbox('Tip internare', ['Programat','Urgent'], key='tip_internare')
    with c3:
        st.date_input('Data evaluării', key='data_evaluare')
        st.text_input('Cod intern (opțional)', key='cod_intern')
    st.markdown('<div class="small-muted">Câmpurile cu * sunt esențiale.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def page_devices():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>Dispozitive invazive (selectați prezența și durata)</h4>', unsafe_allow_html=True)
    devices = ['CVC','Ventilatie','Sonda urinara','Traheostomie','Drenaj','PEG']
    cols = st.columns(3)
    for i, d in enumerate(devices):
        with cols[i % 3]:
            present = st.checkbox(d, key=f'disp_{d}')
            if present:
                st.number_input('Zile (durată)', 0, 365, 3, key=f'zile_{d}')
    st.markdown('</div>', unsafe_allow_html=True)


def page_severity():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>Parametri clinici și scoruri</h4>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.number_input('PaO2/FiO2', 50, 500, value=st.session_state.get('pao2_fio2',400), key='pao2_fio2')
        st.number_input('Trombocite (x10^3/µL)', 0, 1000, value=st.session_state.get('trombocite',200), key='trombocite')
        st.number_input('Bilirubină (mg/dL)', 0.0, 30.0, value=st.session_state.get('bilirubina',1.0), key='bilirubina')
    with c2:
        st.number_input('Glasgow', 3, 15, value=st.session_state.get('glasgow',15), key='glasgow')
        st.number_input('Creatinină (mg/dL)', 0.1, 20.0, value=st.session_state.get('creatinina',1.0), key='creatinina')
        st.checkbox('Hipotensiune', key='hipotensiune')
        st.checkbox('Vasopresoare', key='vasopresoare')
    st.number_input('TAS (mmHg)', 40, 220, value=st.session_state.get('tas',120), key='tas')
    st.number_input('FR (/min)', 8, 60, value=st.session_state.get('fr',18), key='fr')
    st.markdown('<div class="small-muted">SOFA și qSOFA sunt calculate automat pe baza acestor valori.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def page_microbio():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>Microbiologie</h4>', unsafe_allow_html=True)
    cultura = st.checkbox('Cultură pozitivă', key='cultura_pozitiva')
    if cultura:
        st.selectbox('Agent patogen', [''] + list(REZISTENTA_PROFILE.keys()), key='bacterie')
        sel = st.session_state.get('bacterie', '')
        if sel:
            st.multiselect('Profil rezistență', REZISTENTA_PROFILE.get(sel, []), key='profil_rezistenta')
    st.selectbox('Tip infecție (ICD-10)', list(ICD_CODES.keys()), key='tip_infectie')
    st.markdown('</div>', unsafe_allow_html=True)


def page_comorbid():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>Comorbidități (selectați severitatea dacă este cazul)</h4>', unsafe_allow_html=True)
    com_select = {}
    cats = list(COMORBIDITATI.keys())
    cols = st.columns(3)
    for i, cat in enumerate(cats):
        with cols[i % 3]:
            with st.expander(cat, expanded=False):
                for cond, val in COMORBIDITATI[cat].items():
                    key = f'com_{cat}_{cond}'
                    if isinstance(val, dict):
                        choice = st.selectbox(cond, ['Nu'] + list(val.keys()), key=key)
                        if choice and choice != 'Nu':
                            com_select.setdefault(cat, {})[cond] = choice
                    else:
                        v = st.checkbox(cond, key=key)
                        if v:
                            com_select.setdefault(cat, {})[cond] = True
    st.session_state['comorbiditati_selectate'] = com_select
    st.markdown('</div>', unsafe_allow_html=True)


def page_urine():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>Analiză urinară — sediment</h4>', unsafe_allow_html=True)
    st.checkbox('Analiză urinară disponibilă', key='analiza_urina')
    if st.session_state.get('analiza_urina', False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input('Leucocite / câmp', 0, 200, value=st.session_state.get('leu_urina',5), key='leu_urina')
            st.number_input('Eritrocite / câmp', 0, 200, value=st.session_state.get('eri_urina',1), key='eri_urina')
            st.slider('Bacterii (0-4+)', 0, 4, value=st.session_state.get('bact_urina',0), key='bact_urina')
        with c2:
            st.number_input('Celule epiteliale', 0, 50, value=st.session_state.get('cel_epit',2), key='cel_epit')
            st.checkbox('Nitriți +', key='nitriti')
            st.checkbox('Esterază +', key='esteraza')
        with c3:
            st.checkbox('Cilindri', key='cilindri')
            if st.session_state.get('cilindri', False):
                st.text_input('Tip cilindri', key='tip_cilindri')
            st.text_input('Cristale (descriere)', key='cristale')
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


def page_results_and_history():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>Rezultate & Istoric</h4>', unsafe_allow_html=True)
    last = st.session_state.get('last_result')
    if last:
        payload = last['payload']; scor = last['scor']; nivel = last['nivel']; detalii = last['detalii']; recomandari = last['recomandari']
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f'<div class="metric"><div class="metric-value">{scor}</div><div class="small-muted">Scor IAAM</div></div>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f'<div class="metric"><div style="font-weight:700;font-size:16px;">{nivel}</div><div class="small-muted">Nivel risc</div></div>', unsafe_allow_html=True)
        with cols[2]:
            sofa_val, _ = calculate_sofa_detailed(payload); st.markdown(f'<div class="metric"><div class="metric-value">{sofa_val}</div><div class="small-muted">SOFA</div></div>', unsafe_allow_html=True)
        with cols[3]:
            qsofa_val = calculate_qsofa(payload); st.markdown(f'<div class="metric"><div class="metric-value">{qsofa_val}</div><div class="small-muted">qSOFA</div></div>', unsafe_allow_html=True)

        # banner
        risk_map = {'CRITIC':'risk-critical','FOARTE ÎNALT':'risk-high','ÎNALT':'risk-high','MODERAT':'risk-moderate','SCĂZUT':'risk-low'}
        banner_class = risk_map.get(nivel, 'risk-low')
        st.markdown(f'<div class="risk-alert {banner_class}">⚠️ <strong>RISC {nivel}</strong> — Scor: {scor} • {payload.get("nume_pacient")}</div>', unsafe_allow_html=True)

        t1, t2, t3, t4 = st.tabs(['🔎 Analiză','🧾 Recomandări','🔬 Laborator','📥 Export'])
        with t1:
            st.markdown('**Componente scor (detaliate)**')
            for d in detalii:
                st.markdown(f'- {d}')
            fig = go.Figure(go.Indicator(mode='gauge+number', value=scor, domain={'x':[0,1],'y':[0,1]}, gauge={'axis':{'range':[0,150]}}))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280)
            st.plotly_chart(fig, use_container_width=True)
        with t2:
            st.markdown('**Recomandări practice**')
            for i, r in enumerate(recomandari, 1):
                st.markdown(f'{i}. {r}')
            agent = payload.get('bacterie', '')
            if agent:
                st.markdown('**Sugestii empirice (exemplu)**')
                atb_map = {
                    'Escherichia coli': ['Meropenem 1g IV q8h'],
                    'Klebsiella pneumoniae': ['Meropenem 2g perfuzie'],
                    'Pseudomonas aeruginosa': ['Ceftazidim/Avibactam 2.5g IV q8h']
                }
                for a in atb_map.get(agent, ['Consultați antibiograma locală']):
                    st.markdown(f'- {a}')
        with t3:
            st.markdown('**Microbiologie & Urină**')
            if payload.get('cultura_pozitiva'):
                st.markdown(f'- Agent: **{payload.get("bacterie")}**')
                st.markdown(f'- Rezistențe: {', '.join(payload.get("profil_rezistenta", [])) or '—'}')
            else:
                st.markdown('- Fără izolat')
            if payload.get('analiza_urina'):
                interp, risc = analyze_urinary_sediment(payload.get('sediment', {}))
                st.markdown(f'- Probabilitate ITU: **{risc}%**')
                for it in interp:
                    st.markdown(f'  - {it}')
            else:
                st.markdown('- Analiză urinară nedisponibilă')
        with t4:
            raport = {'meta':{'timestamp': last['timestamp'], 'version': VERSION}, 'pacient': payload, 'result': {'scor': scor, 'nivel': nivel, 'detalii': detalii, 'recomandari': recomandari}}
            st.download_button('📥 Descarcă raport JSON', json.dumps(raport, ensure_ascii=False, indent=2), file_name=f'epimind_{payload.get('nume_pacient')}_{datetime.now().strftime('%Y%m%d')}.json', use_container_width=True)
            df = pd.DataFrame([{
                'data': datetime.now().strftime('%Y-%m-%d'),
                'pacient': payload.get('nume_pacient'),
                'sectie': payload.get('sectie'),
                'ore_spitalizare': payload.get('ore_spitalizare'),
                'scor': scor,
                'nivel': nivel
            }])
            st.download_button('📥 Descarcă CSV scurt', df.to_csv(index=False), file_name=f'epimind_stats_{datetime.now().strftime('%Y%m%d')}.csv', use_container_width=True)
    else:
        st.info('Nu există evaluări recente. Completați datele și apăsați butonul de evaluare.')

    st.markdown('---')
    st.markdown('**Istoric audit (local)**')
    df_audit = load_audit_df()
    if not df_audit.empty:
        st.dataframe(df_audit.sort_values('timestamp', ascending=False).head(200), use_container_width=True)
        st.download_button('Descarcă Istoric (.csv)', df_audit.to_csv(index=False), file_name=AUDIT_CSV)
        if st.button('🗑 Șterge istoric (local)'):
            try:
                os.remove(AUDIT_CSV)
                st.success('Fișier audit șters.')
            except Exception as e:
                st.error('Eroare la ștergere: ' + str(e))
    else:
        st.markdown('Nu există date în auditul local.')
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Main & layout ----------------

def main():
    init_defaults()
    render_header()

    if st.session_state.get('show_nav', True):
        left, main_col = st.columns([1.2, 4])
        with left:
            render_nav()
        with main_col:
            render_current_page()
    else:
        render_current_page()

    # bottom controls
    st.markdown('<hr/>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,3])
    with c1:
        if st.button('▶️ Evaluează riscul IAAM', key='compute_main'):
            missing = []
            if not st.session_state.get('nume_pacient'):
                missing.append('Nume pacient')
            if st.session_state.get('ore_spitalizare',0) is None:
                missing.append('Ore spitalizare')
            if missing:
                st.error('Completați: ' + ', '.join(missing))
            else:
                payload = collect_payload()
                scor, nivel, detalii, recomandari = calculate_iaam_risk(payload)
                result = {
                    'payload': payload,
                    'scor': scor,
                    'nivel': nivel,
                    'detalii': detalii,
                    'recomandari': recomandari,
                    'timestamp': datetime.now().isoformat()
                }
                st.session_state['last_result'] = result
                try:
                    append_audit(result)
                except Exception as e:
                    st.warning('Eroare scriere audit: ' + str(e))
                st.success(f'Calcul efectuat — Scor: {scor} • Nivel: {nivel}')
                st.session_state['current_page'] = 'results'
    with c2:
        if st.button('⟳ Reset formular', key='reset_main'):
            keys = [k for k in list(st.session_state.keys()) if k not in ('last_result','show_nav','current_page')]
            for k in keys:
                try:
                    del st.session_state[k]
                except Exception:
                    pass
            st.experimental_rerun()
    with c3:
        st.markdown('<div class="small-muted">EpiMind • Demo academic • Datele se salvează local (CSV). Pentru producție: integrare autentificare, stocare securizată și audit externalizat.</div>', unsafe_allow_html=True)


def render_current_page():
    page = st.session_state.get('current_page','home')
    if page == 'home':
        page_home()
    elif page == 'patient':
        page_patient()
    elif page == 'devices':
        page_devices()
    elif page == 'severity':
        page_severity()
    elif page == 'microbio':
        page_microbio()
    elif page == 'comorbid':
        page_comorbid()
    elif page == 'urine':
        page_urine()
    elif page == 'results':
        page_results_and_history()
    else:
        st.info('Pagina nu există')

if __name__ == '__main__':
    main()
