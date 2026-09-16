import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import time
import math
from datetime import datetime, timedelta

# --- Single Page Compact Layout ---
st.set_page_config(
    page_title="ID Fan Digital Twin",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Ultra-Compact One-Page Dashboard ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; padding-left: 1.5rem; padding-right: 1.5rem; }
        h1 { margin-bottom: 0px !important; font-size: 1.6rem !important; }
        .stMarkdown p { margin-bottom: 0.2rem !important; font-size: 0.85rem !important; }
        div[data-testid="stMetric"] { background-color: #1e2227; padding: 6px 12px; border-radius: 8px; border: 1px solid #2d3436; }
        div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
        .stAlert { padding: 4px 8px !important; margin-bottom: 0px !important; font-size: 0.8rem !important; }
        hr { margin: 8px 0px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("⚙️ ID Fan Digital Twin & Predictive Dashboard")

# --- Session State Initialization ---
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Draft_mmWC", "Power_kW", "Vibration_mms"])

if "rotation_angle" not in st.session_state:
    st.session_state.rotation_angle = 0

# --- Sidebar Controls ---
st.sidebar.header("🕹️ Controls")
speed_rpm = st.sidebar.slider("Fan Speed (RPM)", 300, 1200, 980, 10)
damper_pct = st.sidebar.slider("Damper / IGV (%)", 0, 100, 75, 1)
flue_gas_temp = st.sidebar.slider("Flue Gas Temp (°C)", 90, 220, 145, 1)

st.sidebar.markdown("---")
st.sidebar.header("⚠️ Fault Injections")
blade_health = st.sidebar.slider("Blade Health (%)", 20, 100, 100, 5)
bearing_health = st.sidebar.slider("Bearing Condition (%)", 10, 100, 100, 5)

# Rotation animation step
st.session_state.rotation_angle = (st.session_state.rotation_angle + (speed_rpm / 100.0) * 15) % 360

# --- Telemetry Engine ---
def calculate_telemetry(speed, damper, temp, blade_h, bearing_h):
    rho_gas = 1.293 * (273.15 / (273.15 + temp))
    blade_eff = blade_h / 100.0
    flow = (speed / 1000.0) * (damper / 100.0) * 450000.0 * blade_eff + random.uniform(-500, 500)
    draft = -1.0 * ((speed / 1000.0) ** 2) * (damper / 100.0) * (rho_gas / 1.0) * 350.0 * blade_eff + random.uniform(-1, 1)
    total_eff = 0.82 * blade_eff
    power = abs((flow / 3600.0) * (draft * 9.81) / (total_eff * 1000.0)) + random.uniform(-2, 2)
    current = (power * 1000.0) / (1.732 * 6600.0 * 0.88)
    
    unbalance_vib = ((100.0 - bearing_h) / 100.0) * 12.0 * (speed / 1000.0) ** 2
    blade_unbalance = ((100.0 - blade_h) / 100.0) * 6.0
    vibration = 1.2 * (speed / 1000.0) + unbalance_vib + blade_unbalance + random.uniform(-0.1, 0.1)
    
    return flow, draft, power, current, vibration

flow, draft, power, current, vibration = calculate_telemetry(
    speed_rpm, damper_pct, flue_gas_temp, blade_health, bearing_health
)

# RUL Engine
limiting_health = min(bearing_health, blade_health)
speed_factor = (speed_rpm / 980.0) ** 1.5
temp_factor = 1.0 + (max(0, flue_gas_temp - 145.0) / 100.0)
degradation_rate = 0.35 * speed_factor * temp_factor
rul_days = int(max(0.0, limiting_health - 20.0) / degradation_rate) if degradation_rate > 0 else 999
next_maint_date = datetime.now() + timedelta(days=rul_days)

# Append to history buffer
new_row = pd.DataFrame([{"Draft_mmWC": draft, "Power_kW": power, "Vibration_mms": vibration}])
st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(35)

# --- Top Header Metrics Bar ---
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Flow Rate", f"{flow:,.0f} m³/h")
m2.metric("Furnace Draft", f"{draft:.1f} mmWC")
m3.metric("Motor Power", f"{power:.1f} kW")
m4.metric("Current", f"{current:.1f} A")
m5.metric("Remaining Useful Life", f"{rul_days} Days")
m6.metric("Next Maintenance", next_maint_date.strftime("%b %d, %Y"))

st.markdown("---")

# --- Main Dashboard (Two-Column Layout) ---
col_left, col_right = st.columns([1.1, 0.9])

# --- LEFT COLUMN: Dynamic Graphic & Prescriptive Actions ---
with col_left:
    st.markdown("**🖥️ Digital Twin Live Schematic**")
    
    def render_fan_svg(angle, damper_val, vib_val):
        bearing_color = "#28a745" if vib_val < 4.5 else ("#ffc107" if vib_val < 7.1 else "#dc3545")
        damper_angle = (1.0 - (damper_val / 100.0)) * 75
        
        blade_svg = ""
        for i in range(8):
            rad = math.radians(angle + (i * 45))
            x2, y2 = 180 + 60 * math.cos(rad), 150 + 60 * math.sin(rad)
            blade_svg += f'<line x1="180" y1="150" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#00d2ff" stroke-width="5" stroke-linecap="round"/>'

        damper_lines = ""
        for y_pos in [110, 130, 150, 170, 190]:
            rad_d = math.radians(damper_angle)
            dx, dy = 18 * math.sin(rad_d), 18 * math.cos(rad_d)
            damper_lines += f'<line x1="{60-dx:.1f}" y1="{y_pos-dy:.1f}" x2="{60+dx:.1f}" y2="{y_pos+dy:.1f}" stroke="#ff9f43" stroke-width="3"/>'

        return f"""
        <div style="display:flex; justify-content:center; background:#12161a; border-radius:8px; border:1px solid #2d3436; padding:5px;">
        <svg width="100%" height="240" viewBox="0 0 650 280" xmlns="http://www.w3.org/2000/svg">
            <rect x="20" y="90" width="80" height="120" fill="none" stroke="#718093" stroke-width="3" stroke-dasharray="6 3"/>
            {damper_lines}
            <path d="M 150 70 C 90 70 90 230 180 230 C 260 230 260 30 380 30 L 380 90 C 230 90 230 170 180 170 C 150 170 150 130 180 110" fill="#2c3e50" stroke="#718093" stroke-width="3"/>
            <circle cx="180" cy="150" r="65" fill="none" stroke="#485460" stroke-width="2" stroke-dasharray="4 4"/>
            {blade_svg}
            <circle cx="180" cy="150" r="16" fill="#dcdde1" stroke="#2f3640" stroke-width="3"/>
            <rect x="196" y="143" width="180" height="14" fill="#718093" stroke="#2f3640"/>
            <rect x="290" y="125" width="45" height="50" rx="4" fill="{bearing_color}" stroke="#fff" stroke-width="2"/>
            <rect x="380" y="110" width="110" height="80" rx="6" fill="#2e86de" stroke="#10ac84" stroke-width="2"/>
            <text x="395" y="152" fill="#fff" font-size="12" font-family="sans-serif" font-weight="bold">HV MOTOR</text>
            <rect x="380" y="20" width="230" height="70" fill="none" stroke="#718093" stroke-width="3"/>
            <text x="440" y="55" fill="#a4b0be" font-size="12" font-family="sans-serif" font-weight="bold">TO ESP / CHIMNEY</text>
        </svg>
        </div>
        """

    st.components.v1.html(render_fan_svg(st.session_state.rotation_angle, damper_pct, vibration), height=250)

    # Prescriptive Actions (Compact Box)
    st.markdown("**🛠️ Prescriptive Action Plan**")
    act1, act2 = st.columns(2)
    with act1:
        if bearing_health < 50:
            st.error("Bearing: Critical wear. Schedule immediate sleeve replacement.")
        elif bearing_health < 80:
            st.warning("Bearing: Flush lube oil & check alignment.")
        else:
            st.success("Bearing: Condition optimal.")
    with act2:
        if blade_health < 50:
            st.error("Blades: High ash load. Execute soot blowing & weld buildup.")
        elif blade_health < 80:
            st.warning("Blades: Perform dynamic rotor balancing.")
        else:
            st.success("Blades: Aerodynamics nominal.")

# --- RIGHT COLUMN: Real-Time Telemetry Trends ---
with col_right:
    st.markdown("**📊 Live Telemetry Trends**")
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(6, 4.2), sharex=True)
    fig.patch.set_facecolor('#0e1117')

    for ax in (ax1, ax2, ax3):
        ax.set_facecolor('#161b22')
        ax.tick_params(colors='white', labelsize=7)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.grid(True, linestyle="--", alpha=0.3, color="#8b949e")

    ax1.plot(st.session_state.history["Draft_mmWC"].values, color="#ff4d4d", lw=1.5)
    ax1.set_ylabel("Draft (mmWC)", fontsize=8)

    ax2.plot(st.session_state.history["Power_kW"].values, color="#1e90ff", lw=1.5)
    ax2.set_ylabel("Power (kW)", fontsize=8)

    ax3.plot(st.session_state.history["Vibration_mms"].values, color="#ffa500", lw=1.5)
    ax3.set_ylabel("Vib (mm/s)", fontsize=8)
    ax3.set_xlabel("Time Step Buffer", fontsize=8)

    plt.tight_layout(pad=0.5)
    st.pyplot(fig)

# Auto-stream tick
time.sleep(0.4)
st.rerun()
