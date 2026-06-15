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
    mass_flow = drag * MASS_FLOW_FACTOR
    return mass_flow * time_s

def calculate_emission(fuel_kg):
    return fuel_kg * CO2_FACTOR

def get_valid_altitude(min_alt, max_alt, segment_name="Segment"):
    while True:
        try:
            alt = float(input(f"Enter cruising altitude for {segment_name} (m, between {min_alt}–{max_alt}): ").strip())
            if min_alt <= alt <= max_alt:
                return alt
            else:
                print(f"Error: Altitude must be between {min_alt} and {max_alt} m. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a numeric value.")

def run_segment(segment_name, csv_file, min_alt, max_alt, segment_dist_m):
    try:
        # Altitude validation
        current_alt = get_valid_altitude(min_alt, max_alt, segment_name)

        current_rho = float(input("Enter current air density (kg/m^3): ").strip())
        current_wind_kmh = float(input("Enter current wind speed (km/h) (positive = tailwind): ").strip())
        v_aircraft_kmh = float(input("Enter current aircraft speed (km/h) (true airspeed): ").strip())

        # Convert to m/s
        current_wind_ms = current_wind_kmh * KMH_TO_MS
        v_aircraft_ms = v_aircraft_kmh * KMH_TO_MS

        current_v_rel = v_aircraft_ms + current_wind_ms
        current_drag = calculate_drag(current_rho, current_v_rel)

        # Read CSV
        df = pd.read_csv(csv_file)
        required_cols = {'altitude(m)', 'rho(kg/m^3)', 'headwind(km/h)'}
        if not required_cols.issubset(set(df.columns)):
            missing = required_cols - set(df.columns)
            raise KeyError(f"CSV missing required columns: {missing}")

        # Compute relative speed
        df['headwind_ms'] = df['headwind(km/h)'] * KMH_TO_MS
        df['V_relative_ms'] = v_aircraft_ms + df['headwind_ms']
        df.loc[df['V_relative_ms'] <= 0, 'V_relative_ms'] = np.nan

        # Drag, time, fuel, CO2
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

        # Save results
        df.to_csv(f"{segment_name.lower().replace(' ', '_')}_calculated.csv", index=False)

        # Optimal rows
        min_fuel_idx = df['fuel_used_kg'].idxmin()
        optimal_altitude_fuel = df.loc[min_fuel_idx, 'altitude(m)']
        min_fuel_value = df.loc[min_fuel_idx, 'fuel_used_kg']
        min_co2_value = df.loc[min_fuel_idx, 'CO2_emissions_kg']

        # Current condition estimates
        current_time_s = segment_dist_m / current_v_rel if current_v_rel > 0 else np.nan
        current_fuel = calculate_fuel(current_drag, current_time_s) if not np.isnan(current_time_s) else np.nan
        current_co2 = calculate_emission(current_fuel) if not np.isnan(current_fuel) else np.nan

        # Print summary
        print(f"\n--- {segment_name} Results ---")
        print(f"Current conditions: altitude={current_alt:.0f} m, v_rel={current_v_rel:.2f} m/s")
        print(f"Estimated fuel (unoptimized): {current_fuel:.2f} kg")
        print(f"Estimated CO2 (unoptimized): {current_co2:.2f} kg\n")
        print("Optimal (min fuel) altitude:", optimal_altitude_fuel)
        print(f"Fuel at optimal altitude: {min_fuel_value:.2f} kg")
        print(f"CO2 at optimal altitude: {min_co2_value:.2f} kg")

        return {
            'unoptimized': {'fuel_kg': current_fuel, 'co2_kg': current_co2},
            'optimized': {'fuel_kg': min_fuel_value, 'co2_kg': min_co2_value}
        }

    except FileNotFoundError:
        print(f"File '{csv_file}' not found.")
        return None
    except Exception as e:
        print("Unexpected error:", e)
        return None

if __name__ == "__main__":
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

    for seg in segments:
        result = run_segment(*seg)
        if result:
            total_unopt_fuel += result['unoptimized']['fuel_kg']
            total_unopt_co2 += result['unoptimized']['co2_kg']
            total_opt_fuel += result['optimized']['fuel_kg']
            total_opt_co2 += result['optimized']['co2_kg']

    print("\n=== TOTAL RESULTS ACROSS ALL SEGMENTS ===")
    print(f"Unoptimized Route: Fuel = {total_unopt_fuel:.2f} kg, CO2 = {total_unopt_co2:.2f} kg")
    print(f"Optimized Route:   Fuel = {total_opt_fuel:.2f} kg, CO2 = {total_opt_co2:.2f} kg")
    print(f"Fuel Saved = {total_unopt_fuel - total_opt_fuel:.2f} kg")
    print(f"CO2 Reduced = {total_unopt_co2 - total_opt_co2:.2f} kg")
