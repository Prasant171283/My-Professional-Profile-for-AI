# Refined Knowledge Engine for Exact & Relevant Responses
    def get_ai_response(query):
        q = query.lower()
        
        # 1. Specific Query: Motor Current (Amperes / Amps)
        if any(w in q for w in ["current", "ampere", "amp", "amps", "amperage"]) and not any(w in q for w in ["telemetry", "summary", "status"]):
            return f"⚡ **Motor Current Draw:** The current motor current draw is **{current:.1f} A** (operating on a 6.6 kV line)."
        
        # 2. Specific Query: Motor Power / Load (kW)
        elif any(w in q for w in ["power", "kw", "kilowatt", "load", "energy"]):
            return f"🔌 **Motor Power Draw:** The fan motor is currently drawing **{power:.1f} kW** of power at **{current:.1f} A**."
            
        # 3. Specific Query: Speed / RPM
        elif any(w in q for w in ["speed", "rpm", "rotation"]):
            return f"🔄 **Fan Speed:** The ID Fan is currently rotating at **{speed_rpm:.0f} RPM**."

        # 4. Specific Query: Temperature
        elif any(w in q for w in ["temp", "temperature", "heat", "celsius"]):
            return f"🌡️ **Flue Gas Temperature:** The flue gas inlet temperature is **{flue_gas_temp:.0f} °C**."

        # 5. Vibration & Bearing Condition
        elif any(w in q for w in ["vibration", "bearing", "noise", "shake"]):
            status = "CRITICAL 🚨" if vibration > 7.1 else ("WARNING ⚠️" if vibration > 4.5 else "NORMAL ✅")
            action = (
                "Execute emergency shutdown & sleeve bearing replacement immediately." if vibration > 7.1 
                else ("Schedule lube oil flushing and dynamic shaft re-alignment." if vibration > 4.5 
                else "Bearing vibration is within nominal limits (< 4.5 mm/s).")
            )
            return (
                f"**Bearing & Vibration Analysis:**\n"
                f"* Current Vibration RMS: **{vibration:.2f} mm/s** ({status})\n"
                f"* Bearing Health Condition: **{bearing_health:.0f}%**\n"
                f"* **Prescriptive Action:** {action}"
            )

        # 6. Draft, Flow & Damper Opening
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

        # 8. Complete Telemetry / Status Summary
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

        # 9. General Question Fallback
        else:
            return (
                f"For your question **\"{query}\"**:\n\n"
                f"The ID Fan is running at **{speed_rpm:.0f} RPM**, drawing **{current:.1f} A** ({power:.1f} kW) "
                f"and maintaining **{draft:.1f} mmWC** furnace suction. "
                f"Current bearing vibration is **{vibration:.2f} mm/s**."
            )
