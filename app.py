import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="ID Fan Digital Twin",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Thermal Power Plant ID Fan - Digital Twin Simulator")
st.markdown("Real-time telemetry, aerodynamic degradation, and dynamic physics simulation.")

# --- Session State Initialization for Real-Time Telemetry History ---
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Draft_mmWC", "Power_kW", "Vibration_mms"])

# --- Sidebar Controls & Fault Injections ---
st.sidebar.header("🕹️ Operational Controls")

speed_rpm = st.sidebar.slider("Fan Speed (RPM)", min_value=300, max_value=1200, value=980, step=10)
damper_pct = st.sidebar.slider("Inlet Damper / IGV Position (%)", min_value=0, max_value=100, value=75, step=1)
flue_gas_temp = st.sidebar.slider("Flue Gas Temp (°C)", min_value=90, max_value=220, value=145, step=1)

st.sidebar.markdown("---")
st.sidebar.header("⚠️ Fault Injections & Wear")

blade_health = st.sidebar.slider("Blade Health (Erosion / Ash Load %)", min_value=20, max_value=100, value=100, step=5)
bearing_health = st.sidebar.slider("Bearing Condition (%)", min_value=10, max_value=100, value=100, step=5)

# --- Physics & Telemetry Calculation Engine ---
def calculate_telemetry(speed, damper, temp, blade_h, bearing_h):
    # Density correction for flue gas
    rho_gas = 1.293 * (273.15 / (273.15 + temp))
    
    # Airflow (Affinity Laws + Blade Efficiency)
    blade_eff = blade_h / 100.0
    flow = (speed / 1000.0) * (damper / 100.0) * 450000.0 * blade_eff + random.uniform(-1000, 1000)
    
    # Draft Pressure (mmWC)
    draft = -1.0 * ((speed / 1000.0) ** 2) * (damper / 100.0) * (rho_gas / 1.0) * 350.0 * blade_eff + random.uniform(-2, 2)
    
    # Motor Power & Current
    total_eff = 0.82 * blade_eff
    power = abs((flow / 3600.0) * (draft * 9.81) / (total_eff * 1000.0)) + random.uniform(-5, 5)
    current = (power * 1000.0) / (1.732 * 6600.0 * 0.88)
    
    # Vibration RMS Calculation (Unbalance + Speed component)
    unbalance_vib = ((100.0 - bearing_h) / 100.0) * 12.0 * (speed / 1000.0) ** 2
    blade_unbalance = ((100.0 - blade_h) / 100.0) * 6.0
    vibration = 1.2 * (speed / 1000.0) + unbalance_vib + blade_unbalance + random.uniform(-0.15, 0.15)
    
    return flow, draft, power, current, vibration

# Run single step calculation
flow, draft, power, current, vibration = calculate_telemetry(
    speed_rpm, damper_pct, flue_gas_temp, blade_health, bearing_health
)

# Append to live telemetry history buffer (keep last 50 points)
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

# Color alert for high vibration
if vibration > 7.1:
    col4.metric("Vibration RMS", f"{vibration:.2f} mm/s", "🚨 Danger", delta_color="inverse")
elif vibration > 4.5:
    col4.metric("Vibration RMS", f"{vibration:.2f} mm/s", "⚠️ Warning", delta_color="off")
else:
    col4.metric("Vibration RMS", f"{vibration:.2f} mm/s", "Normal")

st.markdown("---")

# --- Real-Time Trend Charts ---
st.subheader("📊 Dynamic Telemetry Trends")

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 7), sharex=True)

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

# Auto-refresh option for live simulation feel
st.sidebar.markdown("---")
auto_run = st.sidebar.checkbox("Auto-Stream Live Simulation", value=True)
if auto_run:
    time.sleep(0.5)
    st.rerun()
