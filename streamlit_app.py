import streamlit as st
import pandas as pd
import requests
from thefuzz import fuzz
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro CBB Arb Scanner", layout="wide")
st.title("🏀 Layered CBB Arb Scanner")
st.caption("Matching by Name, Time, and Odds Fingerprints")

# --- UI Sidebar ---
st.sidebar.header("Matching Sensitivity")
time_buffer = st.sidebar.slider("Start Time Window (Hours)", 1, 24, 4)
odds_tolerance = st.sidebar.slider("Odds Similarity Tolerance (%)", 5, 30, 15)
match_threshold = st.sidebar.slider("Name Sensitivity", 30, 95, 45)

def clean_name(name):
    """Removes common fluff to help Acronym vs Full Name matching."""
    noise = ["University of", "State", "Univ", "The ", "St.", "Saint", "College"]
    name = name.lower()
    for word in noise:
        name = name.replace(word.lower(), "")
    return name.strip()

def get_data():
    poly_url = "https://gamma-api.polymarket.com/events?tag_id=100639&active=true"
    kalshi_url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=100&status=open"
    
    try:
        p_data = requests.get(poly_url).json()
        k_data = requests.get(kalshi_url).json().get('markets', [])
    except:
        return []

    found = []
    for p in p_data:
        try:
            p_title = p['title']
            p_yes = float(p['markets'][0]['outcomePrices'][0])
            # Poly uses ISO timestamps
            p_time = datetime.fromisoformat(p['startDate'].replace('Z', '+00:00'))
            
            for k in k_data:
                k_title = k['title']
                k_yes = (k.get('yes_bid', 0) / 100)
                k_no = (k.get('no_ask', 0) / 100)
                # Kalshi uses close_time
                k_time = datetime.fromisoformat(k['close_time'].replace('Z', '+00:00'))

                # --- LAYER 1: TIME CHECK ---
                time_diff = abs((p_time - k_time).total_seconds() / 3600)
                if time_diff > time_buffer:
                    continue

                # --- LAYER 2: ODDS SYMMETRY ---
                # If the 'Yes' prices are wildly different (e.g., 0.90 vs 0.20), it's a different game
                if abs(p_yes - k_yes) > (odds_tolerance / 100):
                    continue

                # --- LAYER 3: FUZZY NAME ---
                name_score = fuzz.token_set_ratio(clean_name(p_title), clean_name(k_title))
                
                if name_score >= match_threshold:
                    total_cost = p_yes + k_no
                    profit_pct = ((1.00 - total_cost) / total_cost) * 100
                    
                    found.append({
                        "Game": p_title,
                        "Match Score": name_score,
                        "Time Diff (Hrs)": round(time_diff, 1),
                        "Poly Yes": round(p_yes, 2),
                        "Kalshi No": round(k_no, 2),
                        "Profit %": round(profit_pct, 2),
                        "Is Arb": total_cost < 1.00
                    })
        except: continue
    return found

def style_rows(row):
    if row['Is Arb']:
        return ['background-color: #d4edda; color: #155724; font-weight: bold'] * len(row)
    return [''] * len(row)

if st.button('🔍 Scan with Layered Logic'):
    results = get_data()
    if results:
        df = pd.DataFrame(results)
        top_5 = df.sort_values(by="Profit %", ascending=False).head(5)
        st.table(top_5.style.apply(style_rows, axis=1))
    else:
        st.warning("No matches found. Try widening the Time Window or Odds Tolerance.")
