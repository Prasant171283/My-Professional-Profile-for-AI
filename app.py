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

# --- Custom CSS: Fixed Spacing & Styling ---
st.markdown("""
    <style>
        /* Hide default Streamlit header bar space */
        header[data-testid="stHeader"] { height: 0px !important; background: transparent !important; }

        /* Soft ice-blue background with proper top margin */
        .stApp { background-color: #e6eff8 !important; }
        .block-container { 
            padding-top: 2.2rem !important; 
            padding-bottom: 0.5rem !important; 
            padding-left: 1.5rem !important; 
            padding-right: 1.5rem !important; 
        }
        
        /* Force Header & Title Text Visibility */
        h1, h2, h3, .stApp h1, .stApp h2, .stApp h3 { 
            color: #0b2545 !important; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }
        
        .stMarkdown p, .stMarkdown span { 
            margin-bottom: 0.2rem !important; 
            font-size: 0.85rem !important; 
            color: #1e293b !important; 
        }
        
        .stAlert { padding: 4px 8px !important; margin-bottom: 0px !important; font-size: 0.8rem !important; }
        hr { margin: 8px 0px !important; border-color: #cbd5e1 !important; }
        div[data-testid="stHorizontalBlock"] { align-items: stretch !important; }
    </style>
""", unsafe_allow_html=True)

# --- Clean Main Title Header ---
st.markdown("<h2 style='margin:0 0 10px 0; font-size:1.6rem; font-weight:900; color:#0b2545 !important;'>⚙️ ID Fan Digital Twin</h2>", unsafe_allow_html=True)

# --- Session State Initialization ---
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Draft_mmWC", "Power_kW", "Vibration_mms"])

if "rotation_angle" not in st.session_state:
    st.session_state.rotation_angle = 0

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "👋 Hello! I am your ID Fan Virtual Assistant. Ask me anything about current telemetry, vibration limits, or maintenance procedures."}
    ]

# --- Sidebar Controls ---
st.sidebar.header("🕹️ Operational Controls")
speed_rpm = st.sidebar.slider("Fan Speed (RPM)", 300, 1200, 980, 10)
damper_pct = st.sidebar.slider("Damper / IGV (%)", 0, 100, 75, 1)
flue_gas_temp = st.sidebar.slider("Flue Gas Temp (°C)", 90, 220, 145, 1)

st.sidebar.markdown("---")
st.sidebar.header("⚠️ Wear & Maintenance History")

days_since_maint = st.sidebar.slider("Days Since Last Maintenance", 0, 730, 45, 5)
months_since_new = st.sidebar.slider("Months Since New Bearing Install", 0, 60, 12, 1)
cumulative_run_hrs = st.sidebar.slider("Cumulative Run Hours (kHrs)", 0.0, 50.0, 8.5, 0.5)
blade_health = st.sidebar.slider("Blade Health (%)", 20, 100, 100, 5)

maint_wear = (days_since_maint / 730.0) * 35.0          
install_wear = (months_since_new / 60.0) * 25.0         
hours_wear = (cumulative_run_hrs / 50.0) * 30.0          
calculated_bearing_health = max(10.0, min(100.0, 100.0 - (maint_wear + install_wear + hours_wear)))

st.sidebar.markdown("---")
override_bearing = st.sidebar.checkbox("Manual Bearing Override", value=False)
if override_bearing:
    bearing_health = st.sidebar.slider("Bearing Condition (%)", 10, 100, 80, 5)
else:
    bearing_health = st.sidebar.slider("Bearing Condition (%) (Auto-Calculated)", 10, 100, int(calculated_bearing_health), 1)

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

limiting_health = min(bearing_health, blade_health)
speed_factor = (speed_rpm / 980.0) ** 1.5
temp_factor = 1.0 + (max(0, flue_gas_temp - 145.0) / 100.0)
degradation_rate = 0.35 * speed_factor * temp_factor
rul_days = int(max(0.0, limiting_health - 20.0) / degradation_rate) if degradation_rate > 0 else 999
next_maint_date = datetime.now() + timedelta(days=rul_days)

new_row = pd.DataFrame([{"Draft_mmWC": draft, "Power_kW": power, "Vibration_mms": vibration}])
st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(35)

# --- AI Chatbot Response Generator (Top Level Function) ---
def get_ai_response(query):
    q = query.lower()
    
    # 1. Motor Current Draw (Amps)
    if any(w in q for w in ["current", "ampere", "amp", "amps", "amperage"]) and not any(w in q for w in ["telemetry", "summary", "status"]):
        return f"⚡ **Motor Current Draw:** The fan motor current draw is currently **{current:.1f} A** (operating on a 6.6 kV line)."
    
    # 2. Motor Power (kW)
    elif any(w in q for w in ["power", "kw", "kilowatt", "load", "energy"]):
        return f"🔌 **Motor Power Draw:** The fan motor is currently drawing **{power:.1f} kW** of power at **{current:.1f} A**."
        
    # 3. Speed / RPM
    elif any(w in q for w in ["speed", "rpm", "rotation"]):
        return f"🔄 **Fan Speed:** The ID Fan is currently rotating at **{speed_rpm:.0f} RPM**."

    # 4. Flue Gas Temp
    elif any(w in q for w in ["temp", "temperature", "heat", "celsius"]):
        return f"🌡️ **Flue Gas Temperature:** The flue gas inlet temperature is **{flue_gas_temp:.0f} °C**."

    # 5. Vibration & Bearing Diagnostic
    elif any(w in q for w in ["vibration", "bearing", "noise", "shake"]):
        status = "CRITICAL 🚨" if vibration > 7.1 else ("WARNING ⚠️" if vibration > 4.5 else "NORMAL ✅")
        action = (
            "Execute emergency shutdown & sleeve bearing replacement immediately." if vibration > 7.1 
            else ("Schedule lube oil flushing and dynamic shaft re-alignment." if vibration > 4.5 
            else "Bearing vibration is within nominal limits (< 4.5 mm/s).")
        )
        return (
            f"**Bearing & Vibration Diagnostic:**\n"
            f"* Current Vibration RMS: **{vibration:.2f} mm/s** ({status})\n"
            f"* Bearing Health Condition: **{bearing_health:.0f}%**\n"
            f"* **Prescriptive Action:** {action}"
        )

    # 6. Draft & Flow Rate
    elif any(w in q for w in ["draft", "flow", "damper", "igv", "suction"]):
        return (
            f"**Aerodynamic Telemetry:**\n"
            f"* **Inlet Damper (IGV):** {damper_pct}%\n"
            f"* **Volumetric Flow Rate:** {flow:,.0f} m³/h\n"
            f"* **Furnace Draft Suction:** {draft:.1f} mmWC\n"
            f"* **Blade Condition:** {blade_health}%\n\n"
            f"Adjusting the inlet damper changes flue gas intake volume and modifies negative furnace draft."
        )

    # 7. Predictive Maintenance & RUL
    elif any(w in q for w in ["maintenance", "rul", "repair", "overhaul", "schedule", "life"]):
        return (
            f"**Prognostics & Maintenance Schedule:**\n"
            f"* **Remaining Useful Life (RUL):** {rul_days} Days\n"
            f"* **Target Maintenance Date:** {next_maint_date.strftime('%B %d, %Y')}\n"
            f"* Days Since Overhaul: {days_since_maint} days\n"
            f"* Cumulative Run Hours: {cumulative_run_hrs} kHrs."
        )

    # 8. Full Telemetry Summary
    elif any(w in q for w in ["telemetry", "status", "summary", "all readings", "overview"]):
        return (
            f"**Current ID Fan Operational Summary:**\n"
            f"* **Speed:** {speed_rpm:.0f} RPM\n"
            f"* **Flow Rate:** {flow:,.0f} m³/h\n"
            f"* **Furnace Draft:** {draft:.1f} mmWC\n"
            f"* **Motor Power:** {power:.1f} kW\n"
            f"* **Motor Current:** {current:.1f} A\n"
            f"* **Vibration:** {vibration:.2f} mm/s RMS\n"
            f"* **Remaining Useful Life (RUL):** {rul_days} days"
        )

    # 9. General Fallback
    else:
        return (
            f"For your question **\"{query}\"**:\n\n"
            f"The ID Fan is running at **{speed_rpm:.0f} RPM**, drawing **{current:.1f} A** ({power:.1f} kW) "
            f"and maintaining **{draft:.1f} mmWC** furnace suction. "
            f"Current bearing vibration is **{vibration:.2f} mm/s**."
        )

# --- Custom Metric Card Generator ---
def custom_metric_card(icon_svg, icon_bg, label, value, unit, subtext):
    return f"""
    <div style="
        background-color: #ffffff; 
        border-radius: 12px; 
        padding: 10px 14px; 
        box-shadow: 0px 4px 12px rgba(11, 37, 69, 0.05);
        display: flex;
        align-items: center;
        gap: 12px;
        min-height: 78px;
    ">
        <div style="
            background-color: {icon_bg};
            border-radius: 10px;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        ">
            {icon_svg}
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
            <div style="
                color: #64748b !important; 
                font-size: 0.7rem !important; 
                font-weight: 800 !important; 
                text-transform: uppercase; 
                letter-spacing: 0.6px;
                line-height: 1;
                margin-bottom: 3px;
            ">{label}</div>
            <div style="line-height: 1.1;">
                <span style="
                    color: #0b2545 !important; 
                    font-size: 1.3rem !important; 
                    font-weight: 900 !important;
                    letter-spacing: -0.5px;
                ">{value}</span>
                <span style="
                    color: #475569 !important; 
                    font-size: 0.75rem !important; 
                    font-weight: 700 !important;
                    margin-left: 2px;
                ">{unit}</span>
            </div>
            <div style="
                color: #94a3b8 !important; 
                font-size: 0.7rem !important; 
                font-weight: 600 !important;
                margin-top: 2px;
                line-height: 1;
            ">{subtext}</div>
        </div>
    </div>
    """

# --- Metric Card Icons ---
fan_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0b2545" stroke-width="2.2"><path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"/><path d="M12 9c0 -3.5 2.5 -6 5.5 -6c0 3.5 -2.5 6 -5.5 6z"/><path d="M15 12c3.5 0 6 2.5 6 5.5c-3.5 0 -6 -2.5 -6 -5.5z"/><path d="M12 15c0 3.5 -2.5 6 -5.5 6c0 -3.5 2.5 -6 5.5 -6z"/><path d="M9 12c-3.5 0 -6 -2.5 -6 -5.5c3.5 0 6 2.5 6 5.5z"/></svg>'
draft_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.2"><path d="M12 4v16M8 8l4-4 4 4M8 16l4 4 4-4"/></svg>'
power_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
current_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>'
rul_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 16 14"/></svg>'
date_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'

# --- Metric Cards Row ---
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.markdown(custom_metric_card(fan_icon, "#e0f2fe", "FLOW RATE", f"{flow:,.0f}", "m³/h", "Operational Output"), unsafe_allow_html=True)
m2.markdown(custom_metric_card(draft_icon, "#fef3c7", "FURNACE DRAFT", f"{draft:.1f}", "mmWC", "Suction Pressure"), unsafe_allow_html=True)
m3.markdown(custom_metric_card(power_icon, "#e0f2fe", "MOTOR POWER", f"{power:.1f}", "kW", "Active Load"), unsafe_allow_html=True)
m4.markdown(custom_metric_card(current_icon, "#dcfce7", "CURRENT", f"{current:.1f}", "A", "6.6 kV Line Draw"), unsafe_allow_html=True)
m5.markdown(custom_metric_card(rul_icon, "#dbeafe", "USEFUL LIFE", f"{rul_days}", "Days", "Prognosis RUL"), unsafe_allow_html=True)
m6.markdown(custom_metric_card(date_icon, "#fee2e2", "NEXT MAINT.", next_maint_date.strftime("%b %d"), next_maint_date.strftime("%Y"), "Target Schedule"), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

# --- Tab Layout ---
tab_dashboard, tab_chat = st.tabs(["🖥️ Twin Dashboard & Analytics", "🤖 Ask ID Fan Assistant"])

with tab_dashboard:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("<h3 style='color:#0b2545 !important; font-weight:800; font-size:1.05rem; margin-bottom: 6px;'>🖥️ Digital Twin Schematic Diagram</h3>", unsafe_allow_html=True)
        
        def render_fan_svg(angle, damper_val, vib_val):
            bearing_color = "#16a34a" if vib_val < 4.5 else ("#d97706" if vib_val < 7.1 else "#dc2626")
            damper_angle = (1.0 - (damper_val / 100.0)) * 75
            
            blade_svg = ""
            for i in range(8):
                rad = math.radians(angle + (i * 45))
                x2, y2 = 180 + 72 * math.cos(rad), 175 + 72 * math.sin(rad)
                blade_svg += f'<line x1="180" y1="175" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#0f766e" stroke-width="6" stroke-linecap="round"/>'

            damper_lines = ""
            for y_pos in [120, 145, 175, 205, 230]:
                rad_d = math.radians(damper_angle)
                dx, dy = 20 * math.sin(rad_d), 20 * math.cos(rad_d)
                damper_lines += f'<line x1="{60-dx:.1f}" y1="{y_pos-dy:.1f}" x2="{60+dx:.1f}" y2="{y_pos+dy:.1f}" stroke="#d97706" stroke-width="4"/>'

            return f"""
            <div style="display:flex; justify-content:center; align-items:center; background:#ffffff; border-radius:12px; padding:4px; height: 350px; box-shadow: 0px 4px 12px rgba(11, 37, 69, 0.05);">
            <svg width="100%" height="100%" viewBox="0 0 650 330" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
                <rect x="20" y="95" width="80" height="160" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6 3"/>
                <text x="25" y="82" fill="#0b2545" font-size="13" font-family="sans-serif" font-weight="bold">INLET DUCT</text>
                {damper_lines}
                <path d="M 150 75 C 80 75 80 275 180 275 C 270 275 270 30 380 30 L 380 100 C 230 100 230 200 180 200 C 150 200 150 150 180 130" fill="#f1f5f9" stroke="#0f766e" stroke-width="3"/>
                <circle cx="180" cy="175" r="78" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 4"/>
                {blade_svg}
                <circle cx="180" cy="175" r="20" fill="#94a3b8" stroke="#334155" stroke-width="3"/>
                <rect x="200" y="167" width="180" height="16" fill="#64748b" stroke="#334155"/>
                <rect x="290" y="145" width="50" height="60" rx="4" fill="{bearing_color}" stroke="#ffffff" stroke-width="2"/>
                <text x="293" y="132" fill="#0b2545" font-size="12" font-family="sans-serif" font-weight="bold">BEARING</text>
                <rect x="380" y="125" width="120" height="95" rx="6" fill="#0b2545" stroke="#0f766e" stroke-width="2"/>
                <text x="395" y="177" fill="#ffffff" font-size="13" font-family="sans-serif" font-weight="bold">HV MOTOR</text>
                <rect x="380" y="20" width="230" height="80" fill="none" stroke="#94a3b8" stroke-width="2"/>
                <text x="430" y="60" fill="#0b2545" font-size="13" font-family="sans-serif" font-weight="bold">TO ESP / CHIMNEY</text>
            </svg>
            </div>
            """

        st.components.v1.html(render_fan_svg(st.session_state.rotation_angle, damper_pct, vibration), height=358)

        st.markdown("<h3 style='color:#0b2545 !important; font-weight:800; font-size:1.05rem; margin-bottom: 6px;'>🛠️ Prescriptive Action Plan</h3>", unsafe_allow_html=True)
        act1, act2 = st.columns(2)
        with act1:
            if bearing_health < 50:
                st.error("Bearing: Critical wear. Schedule sleeve replacement.")
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

    with col_right:
        st.markdown("<h3 style='color:#0b2545 !important; font-weight:800; font-size:1.05rem; margin-bottom: 6px;'>📊 Live Telemetry Trends</h3>", unsafe_allow_html=True)
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(6.5, 5.1), sharex=True)
        fig.patch.set_facecolor('#ffffff')

        for ax in (ax1, ax2, ax3):
            ax.set_facecolor('#f8fafc')
            ax.tick_params(colors='#334155', labelsize=8)
            ax.xaxis.label.set_color('#334155')
            ax.yaxis.label.set_color('#334155')
            ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")

        ax1.plot(st.session_state.history["Draft_mmWC"].values, color="#0b2545", lw=2)
        ax1.set_ylabel("Draft (mmWC)", fontsize=9, color="#0b2545", weight="bold")

        ax2.plot(st.session_state.history["Power_kW"].values, color="#0f766e", lw=2)
        ax2.set_ylabel("Power (kW)", fontsize=9, color="#0f766e", weight="bold")

        ax3.plot(st.session_state.history["Vibration_mms"].values, color="#d97706", lw=2)
        ax3.set_ylabel("Vib (mm/s)", fontsize=9, color="#d97706", weight="bold")
        ax3.set_xlabel("Time Step Buffer", fontsize=8, color="#334155")

        plt.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True)

with tab_chat:
    st.markdown("<h3 style='color:#0b2545 !important; font-weight:800; font-size:1.1rem;'>💬 ID Fan AI Technical Assistant</h3>", unsafe_allow_html=True)
    st.caption("Ask contextual questions regarding live telemetry, fault diagnosis, or power plant operating procedures.")

    # Render Chat History
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_prompt := st.chat_input("Ask a question about the ID Fan..."):
        st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        bot_reply = get_ai_response(user_prompt)
        st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})
        with st.chat_message("assistant"):
            st.markdown(bot_reply)

# Sidebar checkbox to toggle live streaming cleanly
st.sidebar.markdown("---")
auto_stream = st.sidebar.checkbox("Auto-Stream Live Telemetry", value=True)
if auto_stream:
    time.sleep(0.4)
    st.rerun()
