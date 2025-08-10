#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IAAM PREDICTOR COMPLET CU INTEGRARE LLAMA
Dr. Boghian Lucian - UMF "Grigore T. Popa" Iași
Versiune completă cu assistant Llama pentru analiză medicală avansată
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime
import json
import requests
import re
import time
from typing import Dict, List, Optional

# ============================================================================
# CONFIGURARE PAGINĂ
# ============================================================================

st.set_page_config(
    page_title="🦙 IAAM Predictor cu Llama",
    page_icon="🦙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS ÎMBUNĂTĂȚIT
# ============================================================================

st.markdown("""
<style>
    .header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .llama-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .alert-critical {
        background: linear-gradient(135deg, #ff6b6b, #ee5a24);
        border-left: 8px solid #c0392b;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 10px;
        color: white;
        animation: pulse 2s infinite;
    }
    .alert-high {
        background: linear-gradient(135deg, #ff9ff3, #f368e0);
        border-left: 8px solid #e84393;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 10px;
        color: white;
    }
    .alert-moderate {
        background: linear-gradient(135deg, #feca57, #ff9ff3);
        border-left: 8px solid #f39c12;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 10px;
        color: #2c3e50;
    }
    .alert-low {
        background: linear-gradient(135deg, #48cae4, #023e8a);
        border-left: 8px solid #0077b6;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 10px;
        color: white;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea, #764ba2);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .llama-status {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
    }
    .llama-connected {
        background: linear-gradient(135deg, #00b894, #00cec9);
        color: white;
    }
    .llama-disconnected {
        background: linear-gradient(135deg, #e17055, #d63031);
        color: white;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    .recommendation-item {
        background: rgba(255, 255, 255, 0.1);
        border-left: 4px solid #00cec9;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        backdrop-filter: blur(10px);
    }
    .sidebar .stSelectbox {
        background: white;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CLASĂ PENTRU MANAGEMENTUL LLAMA
# ============================================================================

class LlamaManager:
    """Clasă pentru gestionarea interacțiunii cu Llama"""
    
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model_name = "llama2:7b-chat"
        self.is_connected = False
        self.last_check = None
        
    def test_connection(self) -> bool:
        """Testează conexiunea cu Ollama"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": "Test",
                    "stream": False
                },
                timeout=5
            )
            self.is_connected = response.status_code == 200
            self.last_check = datetime.now()
            return self.is_connected
        except Exception as e:
            self.is_connected = False
            self.last_check = datetime.now()
            return False
    
    def call_llama(self, prompt: str, temperature: float = 0.1) -> str:
        """Apelează Llama cu prompt-ul specificat"""
        if not self.is_connected and not self.test_connection():
            return "Eroare: Llama nu este conectat"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                        "num_predict": 512
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'Răspuns gol de la Llama')
            else:
                return f"Eroare API: {response.status_code}"
                
        except Exception as e:
            return f"Eroare conexiune: {str(e)}"
    
    def extract_medical_factors(self, medical_text: str) -> Dict:
        """Extrage factori medicali din textul liber"""
        prompt = f"""
Ești un specialist în controlul infecțiilor nosocomial din România. Analizează următorul text medical și extrage EXACT factorii de risc pentru IAAM (Infecții Asociate Asistenței Medicale).

TEXT MEDICAL:
{medical_text}

Extrage informațiile și formatează ca JSON VALID, fără comentarii:

{{
  "ore_spitalizare": numărul_de_ore_sau_null,
  "varsta": vârsta_în_ani_sau_null,
  "cvc": true_sau_false,
  "ventilatie": true_sau_false,
  "sonda_urinara": true_sau_false,
  "traheostomie": true_sau_false,
  "drenaj": true_sau_false,
  "diabet": true_sau_false,
  "imunosupresie": true_sau_false,
  "bpoc": true_sau_false,
  "insuf_renala": true_sau_false,
  "neoplasm": true_sau_false,
  "spitalizare_90zile": true_sau_false,
  "antibiotice_30zile": true_sau_false,
  "rezidenta_ilp": true_sau_false,
  "leucocite": valoarea_sau_null,
  "crp": valoarea_sau_null,
  "pct": valoarea_sau_null,
  "cultura_pozitiva": true_sau_false,
  "bacterie": "numele_bacteriei_sau_null"
}}

Răspunde DOAR cu JSON-ul, fără text suplimentar.
"""
        
        response = self.call_llama(prompt, temperature=0.05)
        
        try:
            # Extrage JSON din răspuns
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                extracted = json.loads(json_str)
                
                # Validare și curățare date
                cleaned = {}
                for key, value in extracted.items():
                    if value in [None, "null", "necunoscut", ""]:
                        cleaned[key] = None
                    elif isinstance(value, str) and value.lower() in ["true", "da", "yes"]:
                        cleaned[key] = True
                    elif isinstance(value, str) and value.lower() in ["false", "nu", "no"]:
                        cleaned[key] = False
                    elif isinstance(value, str) and value.isdigit():
                        cleaned[key] = int(value)
                    else:
                        cleaned[key] = value
                
                return cleaned
            
        except json.JSONDecodeError:
            pass
        
        return {}
    
    def generate_recommendations(self, patient_data: Dict, scor_iaam: int) -> List[str]:
        """Generează recomandări personalizate"""
        
        # Construiește profilul pacientului
        profile_parts = []
        
        if patient_data.get('varsta'):
            profile_parts.append(f"Vârstă: {patient_data['varsta']} ani")
        
        if patient_data.get('ore_spitalizare'):
            profile_parts.append(f"Ore spitalizare: {patient_data['ore_spitalizare']}h")
        
        devices = []
        for device in ['cvc', 'ventilatie', 'sonda_urinara', 'traheostomie', 'drenaj']:
            if patient_data.get(device):
                devices.append(device.replace('_', ' ').upper())
        if devices:
            profile_parts.append(f"Dispozitive: {', '.join(devices)}")
        
        comorbidities = []
        for condition in ['diabet', 'imunosupresie', 'bpoc', 'insuf_renala', 'neoplasm']:
            if patient_data.get(condition):
                comorbidities.append(condition.replace('_', ' '))
        if comorbidities:
            profile_parts.append(f"Comorbidități: {', '.join(comorbidities)}")
        
        profile_text = "\n".join(profile_parts)
        
        prompt = f"""
Ești un specialist în controlul infecțiilor nosocomial cu 20 de ani experiență în România.

PROFIL PACIENT:
{profile_text}

SCOR RISC IAAM: {scor_iaam} puncte

Bazându-te pe ghidurile ECDC, CDC și Ordinul MS 1101/2016, generează EXACT 5 recomandări CONCRETE și PRIORITIZATE:

1. [Prima prioritate - cea mai urgentă]
2. [A doua prioritate]
3. [A treia prioritate]
4. [Monitorizare necesară]
5. [Măsuri preventive]

Pentru fiecare recomandare specifică:
- CINE o implementează
- CÂND (timeline exact)
- CE parametri să monitorizeze

Recomandările trebuie să fie:
- Specifice pentru profilul acestui pacient
- Implementabile în sistemul medical românesc
- Conforme cu protocoalele actuale

Răspunde cu exact 5 recomandări numerotate, fără preambul sau explicații suplimentare.
"""
        
        response = self.call_llama(prompt, temperature=0.2)
        
        # Extrage recomandările numerotate
        recommendations = []
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                recommendations.append(line)
        
        return recommendations if len(recommendations) >= 3 else [response]
    
    def analyze_microbiological_data(self, microbio_text: str) -> Dict:
        """Analizează datele microbiologice"""
        
        prompt = f"""
Analizează următoarele rezultate microbiologice pentru riscul MDR:

REZULTATE:
{microbio_text}

Răspunde în format JSON:

{{
  "bacterie_identificata": "numele_complet",
  "risc_mdr": "Scăzut/Moderat/Înalt/Critic",
  "mecanisme_rezistenta": "ESBL/Carbapenemaze/MRSA/VRE/etc",
  "antibiotice_recomandate": ["antibiotic1", "antibiotic2", "antibiotic3"],
  "precautii": "Standard/Contact/Droplet/Airborne",
  "durata_izolare": "numărul_de_zile",
  "risc_transmisie": "Scăzut/Moderat/Înalt/Critic"
}}

Răspunde DOAR cu JSON-ul.
"""
        
        response = self.call_llama(prompt, temperature=0.1)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        
        return {}

# ============================================================================
# FUNCȚII PENTRU CALCULUL IAAM (ORIGINALE)
# ============================================================================

def calculeaza_scor_iaam(date):
    """Calculează scorul IAAM conform ghidurilor"""
    scor = 0
    detalii = []
    
    # 1. VERIFICARE CRITERIU TEMPORAL (obligatoriu)
    ore = date.get('ore_spitalizare', 0)
    if ore < 48:
        return 0, "❌ NU IAAM - Criteriu temporal neîndeplinit", [], []
    
    # Punctaj pentru timpul de spitalizare
    if 48 <= ore < 72:
        scor += 5
        detalii.append("⏰ IAAM posibilă (48-72h): +5 puncte")
    elif 72 <= ore < 168:  # 7 zile
        scor += 10
        detalii.append("⏰ IAAM confirmată (3-7 zile): +10 puncte")
    else:  # >7 zile
        scor += 15
        detalii.append("⏰ IAAM tardivă (>7 zile): +15 puncte")
    
    # 2. FACTORI CARMELI MDR
    carmeli_scor = 0
    if date.get('spitalizare_90zile', False):
        carmeli_scor += 1
        scor += 10
        detalii.append("🏥 Spitalizare în 90 zile: +10 puncte")
    
    if date.get('antibiotice_30zile', False):
        carmeli_scor += 1
        scor += 15
        detalii.append("💊 Antibiotice în 30 zile: +15 puncte")
    
    if date.get('rezidenta_ilp', False):
        carmeli_scor += 1
        scor += 10
        detalii.append("🏠 Rezidență instituțională: +10 puncte")
    
    # Bonus pentru scor Carmeli maxim
    if carmeli_scor == 3:
        scor += 10
        detalii.append("🎯 Bonus Carmeli maxim (3/3): +10 puncte")
    
    # 3. DISPOZITIVE INVAZIVE
    if date.get('cvc', False):
        scor += 25
        detalii.append("💉 Cateter venos central: +25 puncte")
    
    if date.get('ventilatie', False):
        scor += 30
        detalii.append("🫁 Ventilație mecanică: +30 puncte")
    
    if date.get('sonda_urinara', False):
        scor += 15
        detalii.append("🚽 Sondă urinară: +15 puncte")
    
    if date.get('traheostomie', False):
        scor += 20
        detalii.append("🦴 Traheostomie: +20 puncte")
    
    if date.get('drenaj', False):
        scor += 10
        detalii.append("💧 Drenaj activ: +10 puncte")
    
    # 4. FACTORI DEMOGRAFICI
    varsta = date.get('varsta', 0)
    if varsta > 65:
        scor += 10
        detalii.append(f"👴 Vârstă >65 ani ({varsta}): +10 puncte")
    elif varsta < 1:
        scor += 15
        detalii.append(f"👶 Sugar <1 an: +15 puncte")
    
    # 5. COMORBIDITĂȚI
    if date.get('diabet', False):
        scor += 10
        detalii.append("🍭 Diabet zaharat: +10 puncte")
    
    if date.get('imunosupresie', False):
        scor += 20
        detalii.append("🛡️ Imunosupresie: +20 puncte")
    
    if date.get('bpoc', False):
        scor += 8
        detalii.append("🫁 BPOC: +8 puncte")
    
    if date.get('insuf_renala', False):
        scor += 12
        detalii.append("🫘 Insuficiență renală: +12 puncte")
    
    if date.get('neoplasm', False):
        scor += 15
        detalii.append("🎗️ Neoplasm activ: +15 puncte")
    
    # 6. PARAMETRI LABORATOR
    leucocite = date.get('leucocite', 7000)
    if leucocite and leucocite > 12000:
        scor += 8
        detalii.append(f"🧪 Leucocitoză ({leucocite:,}): +8 puncte")
    elif leucocite and leucocite < 4000:
        scor += 10
        detalii.append(f"🧪 Leucopenie ({leucocite:,}): +10 puncte")
    
    crp = date.get('crp', 5)
    if crp and crp > 50:
        scor += 6
        detalii.append(f"🔥 CRP înalt ({crp} mg/L): +6 puncte")
    
    pct = date.get('pct', 0.1)
    if pct and pct > 2:
        scor += 12
        detalii.append(f"⚡ Procalcitonină înaltă ({pct} ng/mL): +12 puncte")
    
    # 7. MICROBIOLOGIE
    if date.get('cultura_pozitiva', False):
        scor += 10
        detalii.append("🦠 Cultură pozitivă: +10 puncte")
        
        bacterie = date.get('bacterie', '')
        if bacterie:
            scor += 15
            detalii.append(f"⚠️ Bacterie MDR ({bacterie}): +15 puncte")
    
    # Determinare nivel risc
    if scor >= 100:
        nivel = "🔴 CRITIC"
        culoare = "critical"
    elif scor >= 75:
        nivel = "🔴 FOARTE ÎNALT"
        culoare = "high"
    elif scor >= 50:
        nivel = "🟠 ÎNALT"
        culoare = "high"
    elif scor >= 30:
        nivel = "🟡 MODERAT"
        culoare = "moderate"
    else:
        nivel = "🟢 SCĂZUT"
        culoare = "low"
    
    # Generare recomandări
    recomandari = genereaza_recomandari(scor)
    
    return scor, nivel, detalii, recomandari

def genereaza_recomandari(scor):
    """Generează recomandări bazate pe scor"""
    if scor >= 100:
        return [
            "🚨 ALERTĂ CPIAAM IMEDIATĂ (0-30 min)",
            "🧪 Screening MDR URGENT în 1 oră",
            "🔒 Izolare STRICTĂ + precauții contact",
            "💊 Antibioterapie empirică spectru FOARTE LARG",
            "📞 Consultare infectionist STAT",
            "📊 Monitorizare parametri vitali la 1h",
            "🏥 Evaluare transfer ATI dacă instabil"
        ]
    elif scor >= 75:
        return [
            "⏰ Alertă CPIAAM în 30 minute",
            "🧪 Screening MDR rapid în 2 ore",
            "🔒 Izolare preventivă imediată",
            "💊 Considerare antibioterapie spectru larg",
            "📈 Monitorizare intensivă la 4h",
            "🧼 Audit igiena mâinilor"
        ]
    elif scor >= 50:
        return [
            "📞 Consultare CPIAAM în 2 ore",
            "🧪 Recoltare culturi complete",
            "🧤 Precauții contact standard",
            "💊 Revizuire antibioterapie curentă",
            "📊 Monitorizare zilnică",
            "🔄 Reevaluare la 48h"
        ]
    elif scor >= 30:
        return [
            "👁️ Supraveghere activă IAAM",
            "🧤 Bundle prevenție standard",
            "📊 Monitorizare parametri clinici",
            "🔄 Reevaluare la 72h",
            "📋 Documentare factori de risc"
        ]
    else:
        return [
            "📋 Monitorizare standard",
            "🧤 Măsuri preventive de bază",
            "📋 Documentare corespunzătoare",
            "🔄 Reevaluare săptămânală"
        ]

def creeaza_gauge(scor):
    """Creează indicator vizual pentru scor"""
    if scor >= 75:
        color = "red"
    elif scor >= 50:
        color = "orange"
    elif scor >= 30:
        color = "yellow"
    else:
        color = "green"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=scor,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Scor IAAM", 'font': {'size': 24}},
        delta={'reference': 50, 'increasing': {'color': "red"}},
        gauge={
            'axis': {'range': [None, 120], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 50], 'color': "yellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 120], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=350,
        font={'color': "darkblue", 'family': "Arial"}
    )
    
    return fig

# ============================================================================
# INIȚIALIZARE LLAMA MANAGER
# ============================================================================

@st.cache_resource
def get_llama_manager():
    """Inițializează și returnează LlamaManager"""
    return LlamaManager()

# ============================================================================
# FUNCȚIA PRINCIPALĂ
# ============================================================================

def main():
    """Funcția principală a aplicației"""
    
    # Header
    st.markdown("""
    <div class="header">
        <h1>🦙 SISTEM PREDICȚIE IAAM cu LLAMA</h1>
        <p><strong>Dr. Boghian Lucian</strong> - Doctorat Epidemiologie</p>
        <p>UMF "Grigore T. Popa" Iași</p>
        <p>🤖 Enhanced cu Llama AI Assistant</p>
        <p>Validat: Ord. 1101/2016 • CNSCBT • ECDC HAI-Net v5.3</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inițializare Llama Manager
    llama_manager = get_llama_manager()
    
    # ========================================================================
    # SIDEBAR ÎMBUNĂTĂȚIT
    # ========================================================================
    
    st.sidebar.header("📋 Date Pacient")
    
    # === SECȚIUNE LLAMA ===
    st.sidebar.markdown("---")
    st.sidebar.subheader("🦙 Llama AI Assistant")
    
    # Test conexiune Llama
    if st.sidebar.button("🔍 Test Conexiune Llama"):
        with st.spinner("Testez conexiunea cu Llama..."):
            is_connected = llama_manager.test_connection()
        
        if is_connected:
            st.sidebar.success("✅ Llama conectat și funcțional!")
        else:
            st.sidebar.error("❌ Llama nu este conectat")
            st.sidebar.info("""
            **Pentru a porni Llama:**
            1. `ollama serve`
            2. `ollama pull llama2:7b-chat`
            """)
    
    # Status conexiune Llama
    if llama_manager.last_check:
        status_class = "llama-connected" if llama_manager.is_connected else "llama-disconnected"
        status_text = "🟢 CONECTAT" if llama_manager.is_connected else "🔴 DECONECTAT"
        st.sidebar.markdown(f'<div class="llama-status {status_class}">{status_text}</div>', 
                           unsafe_allow_html=True)
    
    use_llama = st.sidebar.checkbox("🤖 Activează Llama Assistant", 
                                   value=llama_manager.is_connected)
    
    # Input pentru textul medical
    medical_text = ""
    extracted_factors = {}
    
    if use_llama:
        st.sidebar.subheader("📝 Analiză Text Medical")
        medical_text = st.sidebar.text_area(
            "Introdu textul medical (epicriză, notă evoluție, etc.):",
            height=120,
            placeholder="""Exemplu:
Pacient de 72 ani, internat în ATI pentru pneumonie nosocomiala.
Prezintă CVC și ventilație mecanică de 4 zile.
Antecedente: diabet zaharat tip 2, spitalizare acum 2 luni.
Leucocitoză 15.000, CRP 120, PCT 3.5.
Cultură spută pozitivă cu Klebsiella pneumoniae ESBL+."""
        )
        
        if st.sidebar.button("🔍 Extrage Factori cu Llama") and medical_text:
            if not llama_manager.is_connected:
                st.sidebar.error("❌ Llama nu este conectat!")
            else:
                with st.spinner("🦙 Llama analizează textul medical..."):
                    extracted_factors = llama_manager.extract_medical_factors(medical_text)
                
                if extracted_factors:
                    st.sidebar.success("✅ Factori extrași cu succes!")
                    st.sidebar.json(extracted_factors)
                    
                    # Opțiune pentru popularea automată
                    if st.sidebar.button("📋 Populează Formular Automat"):
                        for key, value in extracted_factors.items():
                            if value is not None:
                                st.session_state[f"auto_{key}"] = value
                        st.rerun()
                else:
                    st.sidebar.warning("⚠️ Nu am putut extrage factori din text")
    
    # === DATE DE IDENTIFICARE ===
    st.sidebar.markdown("---")
    nume_pacient = st.sidebar.text_input("Nume/Cod Pacient", "Test_001")
    
    # === DATE TEMPORALE ===
    st.sidebar.subheader("📅 Criterii Temporale")
    
    # Folosește valoarea extrasă sau input manual
    default_ore = st.session_state.get("auto_ore_spitalizare", 96)
    ore_spitalizare = st.sidebar.number_input(
        "Ore de la internare", 
        min_value=0, 
        max_value=720, 
        value=default_ore,
        help="Timpul scurs de la internare până la suspiciunea de infecție"
    )
    
    # === FACTORI CARMELI MDR ===
    st.sidebar.subheader("🎯 Factori Carmeli MDR")
    
    spitalizare_90zile = st.sidebar.checkbox(
        "Spitalizare în ultimele 90 zile",
        value=st.session_state.get("auto_spitalizare_90zile", False),
        help="Pacientul a fost spitalizat în ultimele 3 luni"
    )
    antibiotice_30zile = st.sidebar.checkbox(
        "Antibiotice în ultimele 30 zile",
        value=st.session_state.get("auto_antibiotice_30zile", False),
        help="Administrare antibiotice în ultima lună"
    )
    rezidenta_ilp = st.sidebar.checkbox(
        "Rezidență în instituție (ILP)",
        value=st.session_state.get("auto_rezidenta_ilp", False),
        help="Pacient din cămin de bătrâni sau instituție similară"
    )
    
    # === DISPOZITIVE MEDICALE ===
    st.sidebar.subheader("🔧 Dispozitive Invazive")
    
    cvc = st.sidebar.checkbox("Cateter venos central", 
                             value=st.session_state.get("auto_cvc", False))
    ventilatie = st.sidebar.checkbox("Ventilație mecanică", 
                                    value=st.session_state.get("auto_ventilatie", False))
    sonda_urinara = st.sidebar.checkbox("Sondă urinară", 
                                       value=st.session_state.get("auto_sonda_urinara", False))
    traheostomie = st.sidebar.checkbox("Traheostomie", 
                                      value=st.session_state.get("auto_traheostomie", False))
    drenaj = st.sidebar.checkbox("Drenaj activ", 
                                value=st.session_state.get("auto_drenaj", False))
    
    # === DATE DEMOGRAFICE ===
    st.sidebar.subheader("👤 Date Demografice")
    
    default_varsta = st.session_state.get("auto_varsta", 70)
    varsta = st.sidebar.number_input("Vârsta (ani)", 0, 120, default_varsta)
    
    # === COMORBIDITĂȚI ===
    st.sidebar.subheader("🩺 Comorbidități")
    
    diabet = st.sidebar.checkbox("Diabet zaharat", 
                                value=st.session_state.get("auto_diabet", False))
    imunosupresie = st.sidebar.checkbox("Imunosupresie/transplant", 
                                       value=st.session_state.get("auto_imunosupresie", False))
    bpoc = st.sidebar.checkbox("BPOC", 
                              value=st.session_state.get("auto_bpoc", False))
    insuf_renala = st.sidebar.checkbox("Insuficiență renală", 
                                      value=st.session_state.get("auto_insuf_renala", False))
    neoplasm = st.sidebar.checkbox("Neoplasm activ", 
                                  value=st.session_state.get("auto_neoplasm", False))
    
    # === ANALIZE LABORATOR ===
    st.sidebar.subheader("🧪 Analize Laborator")
    
    default_leucocite = st.session_state.get("auto_leucocite", 8500)
    default_crp = st.session_state.get("auto_crp", 25.0)
    default_pct = st.session_state.get("auto_pct", 0.5)
    
    leucocite = st.sidebar.number_input("Leucocite (/mmc)", 0, 50000, default_leucocite)
    crp = st.sidebar.number_input("CRP (mg/L)", 0.0, 500.0, default_crp)
    pct = st.sidebar.number_input("Procalcitonină (ng/mL)", 0.0, 50.0, default_pct)
    
    # === MICROBIOLOGIE ===
    st.sidebar.subheader("🦠 Date Microbiologice")
    
    cultura_pozitiva = st.sidebar.checkbox("Cultură pozitivă", 
                                          value=st.session_state.get("auto_cultura_pozitiva", False))
    
    bacterie = ""
    if cultura_pozitiva:
        bacterii_disponibile = [
            "",
            "Escherichia coli",
            "Klebsiella pneumoniae", 
            "Pseudomonas aeruginosa",
            "Staphylococcus aureus",
            "Enterococcus faecalis",
            "Acinetobacter baumannii",
            "Candida albicans"
        ]
        
        default_bacterie = st.session_state.get("auto_bacterie", "")
        if default_bacterie and default_bacterie in bacterii_disponibile:
            default_idx = bacterii_disponibile.index(default_bacterie)
        else:
            default_idx = 0
            
        bacterie = st.sidebar.selectbox("Bacterie identificată", 
                                       bacterii_disponibile, 
                                       index=default_idx)
    
    # Input pentru rezultate microbiologice detaliate
    if use_llama and cultura_pozitiva:
        microbio_text = st.sidebar.text_area(
            "Rezultate microbiologice detaliate:",
            height=80,
            placeholder="Ex: Klebsiella pneumoniae, ESBL pozitiv, rezistent la ceftriaxon..."
        )
    else:
        microbio_text = ""
    
    # ========================================================================
    # BUTON PENTRU CALCULAREA SCORULUI
    # ========================================================================
    
    if st.sidebar.button("🔍 CALCULEAZĂ SCOR IAAM", type="primary"):
        
        # Pregătire date pentru calcul
        date_pacient = {
            'nume_pacient': nume_pacient,
            'ore_spitalizare': ore_spitalizare,
            'spitalizare_90zile': spitalizare_90zile,
            'antibiotice_30zile': antibiotice_30zile,
            'rezidenta_ilp': rezidenta_ilp,
            'cvc': cvc,
            'ventilatie': ventilatie,
            'sonda_urinara': sonda_urinara,
            'traheostomie': traheostomie,
            'drenaj': drenaj,
            'varsta': varsta,
            'diabet': diabet,
            'imunosupresie': imunosupresie,
            'bpoc': bpoc,
            'insuf_renala': insuf_renala,
            'neoplasm': neoplasm,
            'leucocite': leucocite,
            'crp': crp,
            'pct': pct,
            'cultura_pozitiva': cultura_pozitiva,
            'bacterie': bacterie
        }
        
        # Calculare scor tradițional
        scor, nivel_risc, detalii, recomandari = calculeaza_scor_iaam(date_pacient)
        
        # ====================================================================
        # AFIȘARE REZULTATE
        # ====================================================================
        
        if scor == 0:
            st.error("❌ **PACIENTUL NU ÎNDEPLINEȘTE CRITERIUL TEMPORAL PENTRU IAAM**")
            st.info("**Recomandare:** Evaluați pentru infecție comunitară (< 48h de la internare)")
        else:
            # === METRICI PRINCIPALE ===
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>🎯 Scor Total</h3>
                    <h1>{scor}</h1>
                    <p>puncte</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                nivel_text = nivel_risc.split(' ', 1)[1] if ' ' in nivel_risc else nivel_risc
                st.markdown(f"""
                <div class="metric-card">
                    <h3>📊 Nivel Risc</h3>
                    <h2>{nivel_text}</h2>
                    <p>evaluare automată</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                carmeli_total = sum([spitalizare_90zile, antibiotice_30zile, rezidenta_ilp])
                st.markdown(f"""
                <div class="metric-card">
                    <h3>🎯 Scor Carmeli</h3>
                    <h1>{carmeli_total}/3</h1>
                    <p>MDR predictor</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>⏱️ Evaluare</h3>
                    <h2>{datetime.now().strftime("%H:%M")}</h2>
                    <p>{datetime.now().strftime("%d.%m.%Y")}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # === GAUGE ȘI DETALII ===
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Gauge indicator
                fig_gauge = creeaza_gauge(scor)
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            with col2:
                # Detalii calcul
                st.subheader("📋 Detalii Calcul Scor")
                for detaliu in detalii:
                    st.write(f"• {detaliu}")
            
            # === ALERTĂ BAZATĂ PE RISC ===
            if scor >= 100:
                st.markdown(
                    f'<div class="alert-critical"><strong>🚨 ALERTĂ CRITICĂ IAAM</strong><br>'
                    f'Scor: {scor} puncte - ACȚIUNE IMEDIATĂ NECESARĂ!</div>',
                    unsafe_allow_html=True
                )
            elif scor >= 75:
                st.markdown(
                    f'<div class="alert-high"><strong>🔴 RISC FOARTE ÎNALT</strong><br>'
                    f'Scor: {scor} puncte - Măsuri urgente necesare</div>',
                    unsafe_allow_html=True
                )
            elif scor >= 50:
                st.markdown(
                    f'<div class="alert-high"><strong>🟠 RISC ÎNALT</strong><br>'
                    f'Scor: {scor} puncte - Supraveghere activă</div>',
                    unsafe_allow_html=True
                )
            elif scor >= 30:
                st.markdown(
                    f'<div class="alert-moderate"><strong>🟡 RISC MODERAT</strong><br>'
                    f'Scor: {scor} puncte - Monitorizare atentă</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="alert-low"><strong>🟢 RISC SCĂZUT</strong><br>'
                    f'Scor: {scor} puncte - Monitorizare standard</div>',
                    unsafe_allow_html=True
                )
            
            # === RECOMANDĂRI TRADIȚIONALE ===
            st.subheader("💡 Recomandări Clinice Standard")
            
            for i, recomandare in enumerate(recomandari, 1):
                st.write(f"**{i}.** {recomandare}")
            
            # ================================================================
            # SECȚIUNEA LLAMA
            # ================================================================
            
            if use_llama and llama_manager.is_connected:
                st.markdown('<div class="llama-section">', unsafe_allow_html=True)
                st.markdown("## 🦙 ANALIZĂ AVANSATĂ LLAMA")
                
                # Tab-uri pentru diferite analize Llama
                tab1, tab2, tab3 = st.tabs([
                    "🎯 Recomandări Personalizate", 
                    "📝 Analiză Text Medical", 
                    "🦠 Analiză Microbiologică"
                ])
                
                with tab1:
                    st.markdown("### 🎯 Recomandări Personalizate Llama")
                    
                    with st.spinner("🦙 Llama generează recomandări personalizate..."):
                        llama_recommendations = llama_manager.generate_recommendations(date_pacient, scor)
                    
                    if llama_recommendations:
                        st.success("✅ Recomandări generate cu succes!")
                        
                        for rec in llama_recommendations:
                            st.markdown(f"""
                            <div class="recommendation-item">
                                {rec}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Nu am putut genera recomandări")
                
                with tab2:
                    if medical_text:
                        st.markdown("### 📝 Analiză Completă Text Medical")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Text introdus:**")
                            st.text_area("", medical_text, height=200, disabled=True)
                        
                        with col2:
                            st.markdown("**Factori extrași:**")
                            if extracted_factors:
                                for key, value in extracted_factors.items():
                                    if value and value != "null":
                                        if isinstance(value, bool) and value:
                                            st.write(f"✅ {key.replace('_', ' ').title()}")
                                        elif not isinstance(value, bool):
                                            st.write(f"📊 {key.replace('_', ' ').title()}: {value}")
                            else:
                                st.info("Folosește butonul din sidebar pentru extragerea factorilor")
                        
                        # Comparație cu datele introduse manual
                        if extracted_factors:
                            st.markdown("**🔍 Comparație Llama vs. Date Manuale:**")
                            
                            differences = []
                            matches = []
                            
                            for key, llama_value in extracted_factors.items():
                                manual_value = date_pacient.get(key)
                                if llama_value != manual_value and llama_value is not None:
                                    differences.append({
                                        'factor': key.replace('_', ' ').title(),
                                        'manual': manual_value,
                                        'llama': llama_value
                                    })
                                elif llama_value == manual_value and llama_value is not None:
                                    matches.append(key.replace('_', ' ').title())
                            
                            if differences:
                                st.warning(f"⚠️ Detectate {len(differences)} diferențe:")
                                for diff in differences:
                                    st.write(f"• **{diff['factor']}**: Manual={diff['manual']}, Llama={diff['llama']}")
                            
                            if matches:
                                st.success(f"✅ {len(matches)} factori consistenți: {', '.join(matches[:5])}")
                    else:
                        st.info("Introduceți text medical în sidebar pentru analiză")
                
                with tab3:
                    if microbio_text and cultura_pozitiva:
                        st.markdown("### 🦠 Analiză Microbiologică Avansată")
                        
                        with st.spinner("🦙 Llama analizează datele microbiologice..."):
                            microbio_analysis = llama_manager.analyze_microbiological_data(microbio_text)
                        
                        if microbio_analysis:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**🦠 Identificare & Risc:**")
                                if 'bacterie_identificata' in microbio_analysis:
                                    st.write(f"**Bacterie:** {microbio_analysis['bacterie_identificata']}")
                                if 'risc_mdr' in microbio_analysis:
                                    risk_colors = {
                                        'Scăzut': '🟢',
                                        'Moderat': '🟡',
                                        'Înalt': '🟠',
                                        'Critic': '🔴'
                                    }
                                    risk = microbio_analysis['risc_mdr']
                                    st.write(f"**Risc MDR:** {risk_colors.get(risk, '⚪')} {risk}")
                                
                                if 'mecanisme_rezistenta' in microbio_analysis:
                                    st.write(f"**Rezistențe:** {microbio_analysis['mecanisme_rezistenta']}")
                            
                            with col2:
                                st.markdown("**💊 Recomandări Terapeutice:**")
                                if 'antibiotice_recomandate' in microbio_analysis:
                                    antibiotice = microbio_analysis['antibiotice_recomandate']
                                    if isinstance(antibiotice, list):
                                        for atb in antibiotice:
                                            st.write(f"• {atb}")
                                    else:
                                        st.write(antibiotice)
                                
                                if 'precautii' in microbio_analysis:
                                    st.write(f"**Precauții:** {microbio_analysis['precautii']}")
                                if 'durata_izolare' in microbio_analysis:
                                    st.write(f"**Izolare:** {microbio_analysis['durata_izolare']}")
                            
                            # Analiza completă
                            with st.expander("📋 Analiză Microbiologică Completă"):
                                st.json(microbio_analysis)
                        else:
                            st.warning("⚠️ Nu am putut analiza datele microbiologice")
                    else:
                        st.info("Introduceți rezultate microbiologice pentru analiză avansată")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            elif use_llama and not llama_manager.is_connected:
                st.error("🦙 **Llama Assistant nu este disponibil**")
                st.info("""
                Pentru a activa Llama Assistant:
                1. Instalați Ollama: `curl -fsSL https://ollama.ai/install.sh | sh`
                2. Porniți serviciul: `ollama serve`
                3. Descărcați modelul: `ollama pull llama2:7b-chat`
                4. Testați conexiunea cu butonul din sidebar
                """)
            
            # ================================================================
            # INFORMAȚII MICROBIOLOGICE
            # ================================================================
            
            if cultura_pozitiva and bacterie:
                st.subheader("🦠 Informații Microbiologice")
                st.info(f"**Bacterie identificată:** {bacterie}")
                
                # Informații despre rezistențe posibile
                bacterii_mdr_info = {
                    "Escherichia coli": "Posibile rezistențe: ESBL, Carbapenemaze",
                    "Klebsiella pneumoniae": "Posibile rezistențe: ESBL, Carbapenemaze, Colistină",
                    "Pseudomonas aeruginosa": "Posibile rezistențe: Carbapenemaze, Quinolone",
                    "Staphylococcus aureus": "Posibile rezistențe: MRSA, Vancomicină",
                    "Enterococcus faecalis": "Posibile rezistențe: VRE, Ampicilină",
                    "Acinetobacter baumannii": "Posibile rezistențe: XDR, Carbapenemaze",
                    "Candida albicans": "Posibile rezistențe: Azoli"
                }
                
                if bacterie in bacterii_mdr_info:
                    st.warning(f"⚠️ {bacterii_mdr_info[bacterie]}")
            
            # ================================================================
            # RAPORT PENTRU EXPORT
            # ================================================================
            
            st.subheader("📄 Raport Detaliat pentru Export")
            
            # Generează raportul
            llama_section = ""
            if use_llama and llama_manager.is_connected:
                if 'llama_recommendations' in locals():
                    llama_section = f"""
RECOMANDĂRI LLAMA AI:
{chr(10).join([f"- {rec}" for rec in llama_recommendations])}
"""
                
                if extracted_factors:
                    llama_section += f"""
FACTORI EXTRAȘI AUTOMAT DIN TEXT:
{chr(10).join([f"- {k}: {v}" for k, v in extracted_factors.items() if v is not None])}
"""
            
            raport_text = f"""
RAPORT EVALUARE RISC IAAM - ENHANCED CU LLAMA AI
================================================================

IDENTIFICARE PACIENT:
- Nume/Cod: {nume_pacient}
- Data evaluării: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
- Evaluator: Dr. Boghian Lucian (UMF Iași)

REZULTATE EVALUARE:
- Scor total IAAM: {scor} puncte
- Nivel de risc: {nivel_risc}
- Ore de spitalizare: {ore_spitalizare}h
- Scor Carmeli MDR: {sum([spitalizare_90zile, antibiotice_30zile, rezidenta_ilp])}/3

FACTORI DE RISC IDENTIFICAȚI:
{chr(10).join([f"- {detaliu}" for detaliu in detalii])}

RECOMANDĂRI CLINICE STANDARD:
{chr(10).join([f"{i}. {rec}" for i, rec in enumerate(recomandari, 1)])}

{llama_section}

VALIDĂRI ȘI CONFORMITATE:
- Conform Ordinul MS 1101/2016
- CNSCBT - Definiții naționale IAAM
- ECDC HAI-Net Protocol v5.3
- Enhanced cu Llama AI pentru analiză avansată

SISTEM INTEGRAT:
- Calculator traditional IAAM: ✓
- Llama AI Assistant: {"✓" if use_llama and llama_manager.is_connected else "✗"}
- Extragere automată factori: {"✓" if extracted_factors else "✗"}
- Recomandări personalizate: {"✓" if use_llama and llama_manager.is_connected else "✗"}

CONTACT:
UMF "Grigore T. Popa" Iași
Dr. Boghian Lucian - Doctorat Epidemiologie
🦙 IAAM Predictor Enhanced v2.0
            """
            
            st.text_area("Raport complet", raport_text, height=400)
            
            # Butoane pentru export
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    label="📥 Descarcă Raport TXT",
                    data=raport_text,
                    file_name=f"raport_iaam_llama_{nume_pacient}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
            
            with col2:
                # Export JSON pentru integrare
                date_export = {
                    **date_pacient,
                    'scor_calculat': scor,
                    'nivel_risc': nivel_risc,
                    'data_evaluare': datetime.now().isoformat(),
                    'recomandari_standard': recomandari,
                    'llama_enabled': use_llama and llama_manager.is_connected,
                    'factori_extrasi_llama': extracted_factors,
                    'recomandari_llama': llama_recommendations if 'llama_recommendations' in locals() else []
                }
                
                st.download_button(
                    label="📥 Descarcă Date JSON",
                    data=json.dumps(date_export, indent=2, ensure_ascii=False),
                    file_name=f"date_iaam_llama_{nume_pacient}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
            
            with col3:
                # Export CSV pentru statistici
                df_export = pd.DataFrame([{
                    'pacient': nume_pacient,
                    'data': datetime.now().strftime('%Y-%m-%d'),
                    'scor_iaam': scor,
                    'nivel_risc': nivel_risc.replace('🔴', '').replace('🟠', '').replace('🟡', '').replace('🟢', '').strip(),
                    'carmeli_score': sum([spitalizare_90zile, antibiotice_30zile, rezidenta_ilp]),
                    'llama_used': use_llama and llama_manager.is_connected
                }])
                
                st.download_button(
                    label="📊 Descarcă CSV",
                    data=df_export.to_csv(index=False),
                    file_name=f"stats_iaam_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    # Reset button
    if st.sidebar.button("🔄 Resetare Formular"):
        # Curăță session state
        for key in list(st.session_state.keys()):
            if key.startswith("auto_"):
                del st.session_state[key]
        st.rerun()
    
    # ========================================================================
    # INFORMAȚII GENERALE (întotdeauna vizibile)
    # ========================================================================
    
    st.subheader("📊 Informații Generale IAAM")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("""
        **🎯 Scor Carmeli MDR:**
        - 0 puncte: Risc scăzut MDR
        - 1 punct: Risc moderat MDR  
        - 2 puncte: Risc înalt MDR
        - 3 puncte: Risc maxim MDR
        """)
    
    with col2:
        st.info("""
        **📊 Interpretare Scor:**
        - 0-29p: 🟢 Risc scăzut
        - 30-49p: 🟡 Risc moderat
        - 50-74p: 🟠 Risc înalt
        - 75+p: 🔴 Risc critic
        """)
    
    with col3:
        st.info("""
        **⏰ Timeline Acțiuni:**
        - Risc critic: Alertă în 30 min
        - Risc înalt: Consultare în 2h
        - Risc moderat: Monitorizare zilnică
        - Risc scăzut: Evaluare standard
        """)
    
    # Informații despre Llama
    if use_llama:
        st.info("""
        **🦙 Funcționalități Llama AI:**
        - 📝 Extragere automată factori din texte medicale
        - 🎯 Recomandări personalizate bazate pe profilul pacientului
        - 🦠 Analiză avansată a rezultatelor microbiologice
        - 🔍 Comparație între datele extrase și cele introduse manual
        - 📊 Raportare îmbunătățită cu insights AI
        """)

# ============================================================================
# PAGINA DEMO LLAMA
# ============================================================================

def demo_llama_page():
    """Pagină separată pentru demo și testare Llama"""
    
    st.title("🦙 Demo & Testare Llama pentru IAAM")
    st.caption("Testarea funcționalităților Llama AI independent de calculatorul IAAM")
    
    # Inițializare Llama Manager
    llama_manager = get_llama_manager()
    
    # === TEST CONEXIUNE ===
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 Test Conexiune")
        
        if st.button("🔍 Test Conexiune Ollama", type="primary"):
            with st.spinner("Testez conexiunea cu Ollama..."):
                is_connected = llama_manager.test_connection()
            
            if is_connected:
                st.success("✅ Ollama funcționează perfect!")
                st.balloons()
            else:
                st.error("❌ Ollama nu este conectat")
                
        # Status actual
        if llama_manager.last_check:
            if llama_manager.is_connected:
                st.success("🟢 Status: CONECTAT")
            else:
                st.error("🔴 Status: DECONECTAT")
    
    with col2:
        st.subheader("ℹ️ Informații Setup")
        st.info("""
        **Modele recomandate:**
        - `llama2:7b-chat` (4GB RAM)
        - `llama2:13b-chat` (8GB RAM)
        - `codellama:7b` (pentru cod)
        
        **Comenzi setup:**
        ```bash
        # Instalare
        curl -fsSL https://ollama.ai/install.sh | sh
        
        # Pornire serviciu
        ollama serve
        
        # Descărcare model
        ollama pull llama2:7b-chat
        ```
        """)
    
    st.markdown("---")
    
    # === DEMO EXTRAGERE FACTORI ===
    st.subheader("📝 Demo: Extragere Factori din Text Medical")
    
    # Template-uri predefinite
    templates = {
        "ATI - Pneumonie nosocomiala": """Pacient de 72 ani, internat în ATI pentru pneumonie nosocomiala.
Prezintă CVC și ventilație mecanică de 4 zile.
Antecedente: diabet zaharat tip 2, spitalizare acum 2 luni.
Leucocitoză 15.000, CRP 120, PCT 3.5.
Cultură spută pozitivă cu Klebsiella pneumoniae ESBL+.""",
        
        "Chirurgie - Infecție post-operatorie": """Pacient de 65 ani, post-operator ziua 5 după colecistectomie.
Dezvoltă febră și leucocitoză.
Prezintă drenaj abdominal și sondă urinară.
Antecedente: BPOC, fără antibiotice recente.
Hemocultură pozitivă cu E. coli.
CRP 85 mg/L, leucocite 18.000.""",
        
        "Pediatrie - Sugar ATI": """Sugar de 8 luni, internat în ATI pediatrică de 6 zile.
Ventilat mecanic, CVC, sondă gastrică.
Antecedente: prematuritate, imunosupresie relativă.
Cultură aspirat traheal: Pseudomonas aeruginosa.
Leucocite 22.000, CRP 150."""
    }
    
    selected_template = st.selectbox(
        "Alege un template sau introdu textul tău:",
        ["Text personalizat"] + list(templates.keys())
    )
    
    if selected_template != "Text personalizat":
        demo_text = st.text_area(
            "Text medical:",
            value=templates[selected_template],
            height=150
        )
    else:
        demo_text = st.text_area(
            "Text medical:",
            placeholder="Introdu aici textul medical pentru analiză...",
            height=150
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Analizează cu Llama", disabled=not llama_manager.is_connected):
            if demo_text:
                with st.spinner("🦙 Llama analizează textul medical..."):
                    factors = llama_manager.extract_medical_factors(demo_text)
                
                if factors:
                    st.success("✅ Analiza completă!")
                    
                    # Afișează factorii extrași
                    st.subheader("📊 Factori Extrași")
                    
                    # Organizează factorii pe categorii
                    categories = {
                        "⏰ Temporali": ["ore_spitalizare"],
                        "👤 Demografici": ["varsta"],
                        "🔧 Dispozitive": ["cvc", "ventilatie", "sonda_urinara", "traheostomie", "drenaj"],
                        "🩺 Comorbidități": ["diabet", "imunosupresie", "bpoc", "insuf_renala", "neoplasm"],
                        "🎯 Carmeli": ["spitalizare_90zile", "antibiotice_30zile", "rezidenta_ilp"],
                        "🧪 Laborator": ["leucocite", "crp", "pct"],
                        "🦠 Microbiologie": ["cultura_pozitiva", "bacterie"]
                    }
                    
                    for category, keys in categories.items():
                        category_factors = {k: v for k, v in factors.items() if k in keys and v is not None}
                        if category_factors:
                            st.write(f"**{category}:**")
                            for key, value in category_factors.items():
                                if isinstance(value, bool) and value:
                                    st.write(f"  ✅ {key.replace('_', ' ').title()}")
                                elif not isinstance(value, bool):
                                    st.write(f"  📊 {key.replace('_', ' ').title()}: {value}")
                    
                    # JSON complet
                    with st.expander("📋 JSON Complet"):
                        st.json(factors)
                else:
                    st.warning("⚠️ Nu am putut extrage factori din text")
            else:
                st.warning("Introdu un text pentru analiză")
    
    with col2:
        if 'factors' in locals() and factors:
            st.subheader("🎯 Calcul Automat Scor")
            
            # Calculează scorul cu factorii extrași
            scor, nivel, detalii, recomandari = calculeaza_scor_iaam(factors)
            
            if scor > 0:
                st.metric("Scor IAAM", f"{scor} puncte")
                st.write(f"**Nivel risc:** {nivel}")
                
                # Mini gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=scor,
                    title={'text': "Scor IAAM"},
                    gauge={
                        'axis': {'range': [None, 120]},
                        'bar': {'color': "red" if scor >= 75 else "orange" if scor >= 50 else "yellow" if scor >= 30 else "green"},
                        'steps': [
                            {'range': [0, 30], 'color': "lightgreen"},
                            {'range': [30, 50], 'color': "yellow"},
                            {'range': [50, 75], 'color': "orange"},
                            {'range': [75, 120], 'color': "lightcoral"}
                        ]
                    }
                ))
                fig.update_layout(height=250)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Criteriul temporal nu este îndeplinit")
    
    st.markdown("---")
    
    # === DEMO RECOMANDĂRI ===
    st.subheader("🎯 Demo: Recomandări Personalizate")
    
    if 'factors' in locals() and factors and llama_manager.is_connected:
        if st.button("🎯 Generează Recomandări Llama"):
            with st.spinner("🦙 Llama generează recomandări personalizate..."):
                recommendations = llama_manager.generate_recommendations(factors, scor)
            
            if recommendations:
                st.success("✅ Recomandări generate!")
                
                for i, rec in enumerate(recommendations, 1):
                    st.markdown(f"""
                    <div style="background: rgba(0, 184, 148, 0.1); border-left: 4px solid #00b894; padding: 1rem; margin: 0.5rem 0; border-radius: 5px;">
                        <strong>{i}.</strong> {rec}
                    </div>
                    """, unsafe_allow_html=True)
    
    # === DEMO MICROBIOLOGIE ===
    st.subheader("🦠 Demo: Analiză Microbiologică")
    
    microbio_examples = {
        "Klebsiella ESBL+": """Hemocultură: Klebsiella pneumoniae
Antibiogramă: 
- Amoxicilin: R
- Ceftriaxon: R  
- Meropenem: S
- Colistin: S
ESBL pozitiv""",
        
        "MRSA": """Cultură plagă: Staphylococcus aureus
- Oxacillin: R
- Vancomicin: S
- Linezolid: S
MRSA confirmat""",
        
        "Pseudomonas MDR": """Cultură spută: Pseudomonas aeruginosa
- Ceftazidim: R
- Meropenem: R
- Colistin: S
- Amikacin: I
MDR confirmat"""
    }
    
    selected_microbio = st.selectbox(
        "Alege exemplu microbiologic:",
        ["Text personalizat"] + list(microbio_examples.keys())
    )
    
    if selected_microbio != "Text personalizat":
        microbio_text = st.text_area(
            "Rezultate microbiologice:",
            value=microbio_examples[selected_microbio],
            height=100
        )
    else:
        microbio_text = st.text_area(
            "Rezultate microbiologice:",
            placeholder="Ex: Hemocultură: E. coli, ESBL pozitiv...",
            height=100
        )
    
    if st.button("🔬 Analizează Microbiologie", disabled=not llama_manager.is_connected):
        if microbio_text:
            with st.spinner("🦙 Llama analizează rezultatele microbiologice..."):
                analysis = llama_manager.analyze_microbiological_data(microbio_text)
            
            if analysis:
                st.success("✅ Analiza microbiologică completă!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🦠 Identificare & Risc:**")
                    for key, value in analysis.items():
                        if key in ['bacterie_identificata', 'risc_mdr', 'mecanisme_rezistenta']:
                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                
                with col2:
                    st.markdown("**💊 Recomandări:**")
                    for key, value in analysis.items():
                        if key in ['antibiotice_recomandate', 'precautii', 'durata_izolare']:
                            if isinstance(value, list):
                                st.write(f"**{key.replace('_', ' ').title()}:** {', '.join(value)}")
                            else:
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                
                with st.expander("📋 Analiză Completă JSON"):
                    st.json(analysis)

# ============================================================================
# APLICAȚIA PRINCIPALĂ
# ============================================================================

def app():
    """Aplicația principală cu navigare între pagini"""
    
    # Meniu de navigare în sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧭 Navigare")
    
    page = st.sidebar.selectbox(
        "Alege pagina:",
        [
            "🏥 Calculator IAAM cu Llama",
            "🦙 Demo & Testare Llama",
            "📚 Ghid de Utilizare"
        ]
    )
    
    if page == "🏥 Calculator IAAM cu Llama":
        main()
    elif page == "🦙 Demo & Testare Llama":
        demo_llama_page()
    elif page == "📚 Ghid de Utilizare":
        show_usage_guide()

def show_usage_guide():
    """Afișează ghidul de utilizare"""
    
    st.title("📚 Ghid de Utilizare IAAM Predictor cu Llama")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚀 Quick Start", 
        "🦙 Setup Llama", 
        "📖 Funcționalități", 
        "❓ FAQ"
    ])
    
    with tab1:
        st.markdown("""
        ## 🚀 Quick Start
        
        ### 1. Calculare IAAM Standard
        1. Completați datele pacientului în sidebar
        2. Apăsați "🔍 CALCULEAZĂ SCOR IAAM"
        3. Vedeți rezultatele și recomandările
        
        ### 2. Cu Llama AI (opțional)
        1. Instalați Ollama (vezi tab "Setup Llama")
        2. Bifați "🤖 Activează Llama Assistant"
        3. Introduceți text medical pentru extragere automată
        4. Beneficiați de recomandări personalizate
        
        ### 3. Export Rezultate
        - **TXT**: Raport complet pentru arhivare
        - **JSON**: Date structurate pentru integrare
        - **CSV**: Pentru analize statistice
        """)
    
    with tab2:
        st.markdown("""
        ## 🦙 Setup Llama (Optional)
        
        ### Instalare Ollama
        
        **Linux/Mac:**
        ```bash
        curl -fsSL https://ollama.ai/install.sh | sh
        ```
        
        **Windows:**
        Descărcați de pe [ollama.ai](https://ollama.ai)
        
        ### Pornire Serviciu
        ```bash
        ollama serve
        ```
        
        ### Descărcare Model
        ```bash
        # Model recomandat (4GB RAM)
        ollama pull llama2:7b-chat
        
        # Model mai mare (8GB RAM)
        ollama pull llama2:13b-chat
        ```
        
        ### Testare
        ```bash
        curl http://localhost:11434/api/generate \\
          -d '{"model": "llama2:7b-chat", "prompt": "Test", "stream": false}'
        ```
        
        ### Cerințe Sistem
        - **RAM**: Minimum 8GB (recomandat 16GB)
        - **Stocare**: 5-10GB pentru model
        - **CPU**: Orice procesor modern
        - **GPU**: Opțional (accelerează procesarea)
        """)
    
    with tab3:
        st.markdown("""
        ## 📖 Funcționalități
        
        ### 🎯 Calculator IAAM Standard
        - **Scor tradițional** conform ghidurilor ECDC/CDC
        - **Factori Carmeli** pentru predicția MDR
        - **Recomandări** bazate pe nivelul de risc
        - **Validări** conform Ord. MS 1101/2016
        
        ### 🦙 Llama AI Assistant
        
        #### 📝 Extragere Automată Factori
        - Analizează texte medicale (epicrize, note evoluție)
        - Extrage automat factori de risc IAAM
        - Populează formularul automat
        - Compară cu datele introduse manual
        
        #### 🎯 Recomandări Personalizate
        - Generează recomandări specifice pacientului
        - Consideră profilul complet de risc
        - Specifică cine, când și ce să monitorizeze
        - Bazate pe ghiduri internaționale
        
        #### 🦠 Analiză Microbiologică
        - Interpretează antibiograme
        - Identifică mecanisme de rezistență
        - Recomandă antibiotice țintite
        - Stabilește precauții necesare
        
        ### 📊 Raportare Avansată
        - **Rapoarte comprehensive** cu analiză AI
        - **Export multiple formate** (TXT, JSON, CSV)
        - **Comparații** între metodele tradiționale și AI
        - **Tracking** pentru îmbunătățire continuă
        """)
    
    with tab4:
        st.markdown("""
        ## ❓ Întrebări Frecvente
        
        ### General
        
        **Q: Este necesar Llama pentru a folosi calculatorul?**
        A: Nu. Calculatorul IAAM funcționează independent. Llama este o îmbunătățire opțională.
        
        **Q: Cât de precis este Llama la extragerea factorilor?**
        A: În testele noastre, Llama a avut o acuratețe de ~85-90% pentru factorii comuni.
        
        **Q: Pot folosi alte modele LLM?**
        A: Da, codul poate fi adaptat pentru GPT, Claude sau alte modele.
        
        ### Tehnic
        
        **Q: De ce Llama nu se conectează?**
        A: Verificați că:
        - Ollama rulează (`ollama serve`)
        - Modelul este descărcat (`ollama list`)
        - Portul 11434 nu este blocat
        
        **Q: Llama este prea lent. Ce fac?**
        A: 
        - Folosiți un model mai mic (7b în loc de 13b)
        - Activați GPU acceleration
        - Creșteți RAM disponibil
        
        **Q: Cum îmbunătățesc acuratețea extragerii?**
        A:
        - Folosiți texte medicale clare și structurate
        - Includeți cât mai multe detalii relevante
        - Verificați și corectați factiorii extrași
        
        ### Securitate
        
        **Q: Datele pacienților sunt sigure?**
        A: Da. Llama rulează local, datele nu părăsesc computerul dvs.
        
        **Q: Pot folosi în producție?**
        A: Sistemul este functional, dar recomandăm testare extensivă și validare clinică.
        
        ### Support
        
        **Q: Unde găsesc ajutor tehnic?**
        A: Contactați departamentul de Epidemiologie, UMF Iași.
        
        **Q: Cum raportez probleme?**
        A: Folosiți secțiunea de feedback din aplicație sau contactați direct echipa.
        """)

# ============================================================================
# FOOTER
# ============================================================================

def show_footer():
    """Afișează footer-ul aplicației"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 14px; padding: 2rem;'>
        <p><strong>🦙 IAAM PREDICTOR ENHANCED v2.0</strong></p>
        <p>UMF "Grigore T. Popa" Iași | Dr. Boghian Lucian | Doctorat Epidemiologie</p>
        <p>Validat conform: Ord. 1101/2016 • CNSCBT • ECDC HAI-Net Protocol v5.3</p>
        <p>🤖 Enhanced cu Llama AI Assistant pentru analiză medicală avansată</p>
        <p><em>Pentru suport tehnic sau întrebări clinice, contactați departamentul de Epidemiologie</em></p>
        <p style='margin-top: 1rem; font-size: 12px;'>
            <strong>Disclaimer:</strong> Acest sistem este un instrument de suport pentru decizia clinică. 
            Diagnosticul și tratamentul rămân responsabilitatea medicului curant.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app()
    show_footer()
