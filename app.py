import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import time
import math

# --- Page Configuration ---
st.set_page_config(
    page_title="ID Fan Digital Twin",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Thermal Power Plant ID Fan - Digital Twin Simulator")
st.markdown("Real-time telemetry, aerodynamic degradation, and dynamic physics simulation.")

# --- Session State Initialization ---
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Draft_mmWC", "Power_kW", "Vibration_mms"])

if "rotation_angle" not in st.session_state:
    st.session_state.rotation_angle = 0

# --- Sidebar Controls & Fault Injections ---
st.sidebar.header("🕹️ Operational Controls")

speed_rpm = st.sidebar.slider("Fan Speed (RPM)", min_value=300, max_value=1200, value=980, step=10)
damper_pct = st.sidebar.slider("Inlet Damper / IGV Position (%)", min_value=0, max_value=100, value=75, step=1)
flue_gas_temp = st.sidebar.slider("Flue Gas Temp (°C)", min_value=90, max_value=220, value=145, step=1)

st.sidebar.markdown("---")
st.sidebar.header("⚠️ Fault Injections & Wear")

blade_health = st.sidebar.slider("Blade Health (Erosion / Ash Load %)", min_value=20, max_value=100, value=100, step=5)
bearing_health = st.sidebar.slider("Bearing Condition (%)", min_value=10, max_value=100, value=100, step=5)

# --- Update Rotation Angle for Dynamic Animation ---
st.session_state.rotation_angle = (st.session_state.rotation_angle + (speed_rpm / 100.0) * 15) % 360

# --- Physics & Telemetry Calculation Engine ---
def calculate_telemetry(speed, damper, temp, blade_h, bearing_h):
    rho_gas = 1.293 * (273.15 / (273.15 + temp))
    blade_eff = blade_h / 100.0
    flow = (speed / 1000.0) * (damper / 100.0) * 450000.0 * blade_eff + random.uniform(-1000, 1000)
    draft = -1.0 * ((speed / 1000.0) ** 2) * (damper / 100.0) * (rho_gas / 1.0) * 350.0 * blade_eff + random.uniform(-2, 2)
    total_eff = 0.82 * blade_eff
    power = abs((flow / 3600.0) * (draft * 9.81) / (total_eff * 1000.0)) + random.uniform(-5, 5)
    current = (power * 1000.0) / (1.732 * 6600.0 * 0.88)
    
    unbalance_vib = ((100.0 - bearing_h) / 100.0) * 12.0 * (speed / 1000.0) ** 2
    blade_unbalance = ((100.0 - blade_h) / 100.0) * 6.0
    vibration = 1.2 * (speed / 1000.0) + unbalance_vib + blade_unbalance + random.uniform(-0.15, 0.15)
    
    return flow, draft, power, current, vibration

flow, draft, power, current, vibration = calculate_telemetry(
    speed_rpm, damper_pct, flue_gas_temp, blade_health, bearing_health
)

# Append data point
new_row = pd.DataFrame([{
    "Draft_mmWC": draft,
    "Power_kW": power,
    "Vibration_mms": vibration
}])
st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(50)

# --- Top Dashboard Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Flow Rate", f"{flow:,.0f} m³/h")
col2.metric("Furnace Draft", f"{draft:.1f} mmWC")
col3.metric("Motor Power", f"{power:.1f} kW", f"{current:.1f} A")

if vibration > 7.1:
    col4.metric("Vibration RMS", f"{vibration:.2f} mm/s", "🚨 Danger", delta_color="inverse")
elif vibration > 4.5:
    col4.metric("Vibration RMS", f"{vibration:.2f} mm/s", "⚠️ Warning", delta_color="off")
else:
    col4.metric("Vibration RMS", f"{vibration:.2f} mm/s", "Normal")

st.markdown("---")

# --- Dynamic SVG Diagram Rendering Function ---
def render_fan_svg(angle, damper_val, vib_val, temp_val):
    # Dynamic Colors based on alerts
    bearing_color = "#28a745" if vib_val < 4.5 else ("#ffc107" if vib_val < 7.1 else "#dc3545")
    damper_angle = (1.0 - (damper_val / 100.0)) * 75  # Damper blade angle in deg
    
    # Generate 8 fan impeller blades rotated around center (200, 180)
    blade_svg_elements = ""
    for i in range(8):
        b_angle = angle + (i * 45)
        rad = math.radians(b_angle)
        x2 = 200 + 75 * math.cos(rad)
        y2 = 180 + 75 * math.sin(rad)
        blade_svg_elements += f'<line x1="200" y1="180" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#00d2ff" stroke-width="6" stroke-linecap="round"/>'

    # Generate Damper Vane lines
    damper_lines = ""
    for y_pos in [130, 155, 180, 205, 230]:
        rad_d = math.radians(damper_angle)
        dx = 25 * math.sin(rad_d)
        dy = 25 * math.cos(rad_d)
        damper_lines += f'<line x1="{70-dx:.1f}" y1="{y_pos-dy:.1f}" x2="{70+dx:.1f}" y2="{y_pos+dy:.1f}" stroke="#ff9f43" stroke-width="4"/>'

    svg_code = f"""
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1a1e24; padding: 15px; border-radius: 12px; margin-bottom: 25px;">
    <svg width="780" height="340" viewBox="0 0 780 340" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="gasFlow" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ff9f43" stop-opacity="0.2"/>
                <stop offset="50%" stop-color="#00d2ff" stop-opacity="0.6"/>
                <stop offset="100%" stop-color="#54a0ff" stop-opacity="0.8"/>
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>

        <!-- Background grid details -->
        <rect x="10" y="10" width="760" height="320" rx="10" fill="#111418" stroke="#2d3436" stroke-width="2"/>

        <!-- Inlet Duct -->
        <rect x="30" y="110" width="100" height="140" fill="none" stroke="#718093" stroke-width="4" stroke-dasharray="8 4"/>
        <text x="40" y="95" fill="#a4b0be" font-size="12" font-family="sans-serif" font-weight="bold">INLET DUCT</text>

        <!-- Inlet Guide Vanes (IGV / Damper) -->
        <g>
            {damper_lines}
            <text x="45" y="270" fill="#ff9f43" font-size="11" font-family="sans-serif">IGV Damper ({damper_val:.0f}%)</text>
        </g>

        <!-- Flue Gas Flow Arrows -->
        <path d="M 35 150 Q 120 150 160 180" fill="none" stroke="url(#gasFlow)" stroke-width="8" marker-end="url(#arrow)" />
        <path d="M 35 210 Q 120 210 160 180" fill="none" stroke="url(#gasFlow)" stroke-width="8" />
        <path d="M 230 110 Q 300 40 450 40 L 520 40" fill="none" stroke="url(#gasFlow)" stroke-width="12" filter="url(#glow)"/>

        <!-- Scroll / Volute Casing -->
        <path d="M 170 80 C 100 80 100 280 200 280 C 310 280 310 40 450 40 L 450 110 C 260 110 260 210 200 210 C 170 210 170 150 200 130" fill="#2c3e50" stroke="#718093" stroke-width="4" opacity="0.85"/>
        <text x="210" y="305" fill="#a4b0be" font-size="13" font-family="sans-serif" font-weight="bold">VOLUTE CASING</text>

        <!-- Fan Impeller / Blades (Dynamic Rotated) -->
        <circle cx="200" cy="180" r="82" fill="none" stroke="#485460" stroke-width="3" stroke-dasharray="4 4"/>
        {blade_svg_elements}
        <circle cx="200" cy="180" r="22" fill="#dcdde1" stroke="#2f3640" stroke-width="4"/>

        <!-- Drive Shaft -->
        <rect x="220" y="172" width="220" height="16" fill="#718093" stroke="#2f3640" stroke-width="2"/>
        <text x="290" y="165" fill="#a4b0be" font-size="11" font-family="sans-serif">DRIVE SHAFT</text>

        <!-- Bearing Pedestal Unit -->
        <rect x="330" y="150" width="50" height="60" rx="5" fill="{bearing_color}" stroke="#ffffff" stroke-width="2" filter="url(#glow)"/>
        <text x="335" y="185" fill="#ffffff" font-size="11" font-family="sans-serif" font-weight="bold">BEARING</text>
        <text x="325" y="230" fill="{bearing_color}" font-size="11" font-family="sans-serif">Vib: {vib_val:.2f} mm/s</text>

        <!-- Electric Motor Drive -->
        <rect x="440" y="130" width="130" height="100" rx="8" fill="#2e86de" stroke="#10ac84" stroke-width="3"/>
        <!-- Motor Fins -->
        <line x1="460" y1="130" x2="460" y2="230" stroke="#54a0ff" stroke-width="3"/>
        <line x1="490" y1="130" x2="490" y2="230" stroke="#54a0ff" stroke-width="3"/>
        <line x1="520" y1="130" x2="520" y2="230" stroke="#54a0ff" stroke-width="3"/>
        <text x="455" y="175" fill="#ffffff" font-size="13" font-family="sans-serif" font-weight="bold">HV MOTOR</text>
        <text x="455" y="195" fill="#c8d6e5" font-size="11" font-family="sans-serif">{speed_rpm:.0f} RPM</text>

        <!-- Outlet Duct -->
        <rect x="450" y="25" width="280" height="85" fill="none" stroke="#718093" stroke-width="4"/>
        <path d="M 470 65 L 700 65" stroke="#00d2ff" stroke-width="6" stroke-dasharray="15 10" filter="url(#glow)"/>
        <text x="560" y="55" fill="#a4b0be" font-size="12" font-family="sans-serif" font-weight="bold">TO CHIMNEY / ESP</text>
        <text x="560" y="85" fill="#ff9f43" font-size="11" font-family="sans-serif">Temp: {temp_val:.0f} °C</text>
    </svg>
    </div>
    """
    return svg_code

# --- Display Interactive SVG Graphic ---
st.subheader("🖥️ Interactive Digital Twin Schematic Diagram")
st.components.v1.html(
    render_fan_svg(st.session_state.rotation_angle, damper_pct, vibration, flue_gas_temp), 
    height=370
)

# --- Real-Time Trend Charts ---
st.subheader("📊 Dynamic Telemetry Trends")

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 6), sharex=True)

ax1.plot(st.session_state.history["Draft_mmWC"].values, color="crimson", lw=2)
ax1.set_ylabel("Draft (mmWC)")
ax1.set_title("Furnace Suction Pressure")
ax1.grid(True, linestyle="--", alpha=0.6)

ax2.plot(st.session_state.history["Power_kW"].values, color="royalblue", lw=2)
ax2.set_ylabel("Power (kW)")
ax2.set_title("Motor Power Draw")
ax2.grid(True, linestyle="--", alpha=0.6)

ax3.plot(st.session_state.history["Vibration_mms"].values, color="darkorange", lw=2)
ax3.set_ylabel("Vibration (mm/s)")
ax3.set_xlabel("Time Step Buffer")
ax3.set_title("Bearing Vibration")
ax3.grid(True, linestyle="--", alpha=0.6)

plt.tight_layout()
st.pyplot(fig)

# Auto-refresh loop
st.sidebar.markdown("---")
auto_run = st.sidebar.checkbox("Auto-Stream Live Simulation", value=True)
if auto_run:
    time.sleep(0.4)
    st.rerun()
