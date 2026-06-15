import streamlit as st
import numpy as np
import pandas as pd

# Constants
CD = 0.027
AREA = 122.6
MASS_FLOW_FACTOR = 0.000015
CO2_FACTOR = 3.16
KMH_TO_MS = 1000.0 / 3600.0

def calculate_drag(rho, v_rel):
    return 0.5 * rho * (v_rel ** 2) * CD * AREA

def calculate_fuel(drag, time_s):
    return drag * MASS_FLOW_FACTOR * time_s

def calculate_emission(fuel_kg):
    return fuel_kg * CO2_FACTOR

def run_segment(segment_name, csv_file, min_alt, max_alt, segment_dist_m,
                current_alt, current_rho, current_wind_kmh, v_aircraft_kmh):
    if not (min_alt <= current_alt <= max_alt):
        st.error(f"{segment_name}: Altitude must be between {min_alt} and {max_alt} m.")
        return None

    # Convert to m/s
    current_wind_ms = current_wind_kmh * KMH_TO_MS
    v_aircraft_ms = v_aircraft_kmh * KMH_TO_MS
    current_v_rel = v_aircraft_ms + current_wind_ms
    current_drag = calculate_drag(current_rho, current_v_rel)

    try:
        df = pd.read_csv(csv_file)
        df['headwind_ms'] = df['headwind(km/h)'] * KMH_TO_MS
        df['V_relative_ms'] = v_aircraft_ms + df['headwind_ms']
        df.loc[df['V_relative_ms'] <= 0, 'V_relative_ms'] = np.nan

        df['drag_N'] = df.apply(
            lambda r: calculate_drag(r['rho(kg/m^3)'], r['V_relative_ms']) if not np.isnan(r['V_relative_ms']) else np.nan,
            axis=1
        )
        df['time_s'] = segment_dist_m / df['V_relative_ms']
        df['fuel_used_kg'] = df.apply(
            lambda r: calculate_fuel(r['drag_N'], r['time_s']) if not np.isnan(r['time_s']) else np.nan,
            axis=1
        )
        df['CO2_emissions_kg'] = df['fuel_used_kg'].apply(lambda x: calculate_emission(x) if not pd.isna(x) else np.nan)

        min_fuel_idx = df['fuel_used_kg'].idxmin()
        optimal_altitude_fuel = df.loc[min_fuel_idx, 'altitude(m)']
        min_fuel_value = df.loc[min_fuel_idx, 'fuel_used_kg']
        min_co2_value = df.loc[min_fuel_idx, 'CO2_emissions_kg']

        current_time_s = segment_dist_m / current_v_rel if current_v_rel > 0 else np.nan
        current_fuel = calculate_fuel(current_drag, current_time_s) if not np.isnan(current_time_s) else np.nan
        current_co2 = calculate_emission(current_fuel) if not np.isnan(current_fuel) else np.nan

        st.subheader(f"{segment_name} Results")
        st.write(f"Unoptimized fuel: {current_fuel:.2f} kg, CO₂: {current_co2:.2f} kg")
        st.write(f"Optimal altitude: {optimal_altitude_fuel} m")
        st.write(f"Optimized fuel: {min_fuel_value:.2f} kg, CO₂: {min_co2_value:.2f} kg")

        return {
            'unoptimized': {'fuel_kg': current_fuel, 'co2_kg': current_co2},
            'optimized': {'fuel_kg': min_fuel_value, 'co2_kg': min_co2_value}
        }

    except FileNotFoundError:
        st.error(f"CSV file {csv_file} not found.")
        return None

# --- Streamlit UI ---
st.title("Green Flight Route Optimizer")

segments = [
    ("Segment 1", "segment1_data.csv", 6000, 8000, 170000.0),
    ("Segment 2", "segment2n3_data.csv", 8000, 10700, 170000.0),
    ("Segment 3", "segment2n3_data.csv", 8000, 10700, 170000.0),
    ("Segment 4", "segment4_data.csv", 7500, 9000, 170000.0),
    ("Segment 5", "segment5_data.csv", 3000, 7500, 170000.0),
]

total_unopt_fuel = 0.0
total_unopt_co2 = 0.0
total_opt_fuel = 0.0
total_opt_co2 = 0.0

st.sidebar.header("Input Parameters")
results = []

for seg in segments:
    seg_name, csv_file, min_alt, max_alt, dist = seg
    st.sidebar.subheader(seg_name)
    alt = st.sidebar.number_input(f"{seg_name} Altitude (m)", min_value=min_alt, max_value=max_alt, value=min_alt)
    rho = st.sidebar.number_input(f"{seg_name} Air density (kg/m³)", value=1.225)
    wind = st.sidebar.number_input(f"{seg_name} Wind speed (km/h)", value=0.0)
    speed = st.sidebar.number_input(f"{seg_name} Aircraft speed (km/h)", value=800.0)

    if st.sidebar.button(f"Run {seg_name}"):
        result = run_segment(seg_name, csv_file, min_alt, max_alt, dist, alt, rho, wind, speed)
        if result:
            total_unopt_fuel += result['unoptimized']['fuel_kg']
            total_unopt_co2 += result['unoptimized']['co2_kg']
            total_opt_fuel += result['optimized']['fuel_kg']
            total_opt_co2 += result['optimized']['co2_kg']
            results.append(result)

# Show totals after all segments
if results:
    st.header("Total Route Results")
    st.write(f"Unoptimized Route: Fuel = {total_unopt_fuel:.2f} kg, CO₂ = {total_unopt_co2:.2f} kg")
    st.write(f"Optimized Route: Fuel = {total_opt_fuel:.2f} kg, CO₂ = {total_opt_co2:.2f} kg")
    st.success(f"Fuel Saved = {total_unopt_fuel - total_opt_fuel:.2f} kg, CO₂ Reduced = {total_unopt_co2 - total_opt_co})
