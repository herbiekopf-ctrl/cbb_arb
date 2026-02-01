import streamlit as st
import pandas as pd
import requests
from thefuzz import fuzz, process
from datetime import datetime

# --- CONFIG ---
# 10470 is the active 2025-2026 CBB Tag for Polymarket Gamma
POLY_TAG = "10470" 
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

def get_poly_data():
    """Fetches active CBB games from Polymarket."""
    url = f"https://gamma-api.polymarket.com/events?tag_id={POLY_TAG}&active=true&closed=false&limit=100"
    try:
        data = requests.get(url).json()
        rows = []
        for event in data:
            # Polymarket titles are usually "Team A vs Team B"
            title = event.get('title', '')
            for m in event.get('markets', []):
                # We only want the 'Winner' markets (usually the first one)
                if "Winner" in m.get('group_id', '') or len(event.get('markets')) == 1:
                    prices = m.get('outcomePrices', ["0", "0"])
                    rows.append({
                        "Event": title,
                        "Poly_Yes": round(float(prices[0]) * 100, 1),
                        "Poly_No": round(float(prices[1]) * 100, 1)
                    })
                    break # Grab only the main market per game
        return rows
    except Exception as e:
        st.error(f"Poly API Error: {e}")
        return []

def get_kalshi_data():
    """Fetches active CBB games from Kalshi."""
    # We query open markets and filter by title keywords
    url = f"{KALSHI_BASE}/markets?limit=200&status=open"
    try:
        resp = requests.get(url).json()
        markets = resp.get('markets', [])
        rows = []
        for m in markets:
            title = m.get('title', '')
            # Filter for College Basketball keywords
            if any(word in title.upper() for word in ["CBB", "NCAA", "BASKETBALL"]):
                # Clean "Will [Team] win..." into "[Team]"
                clean_title = title.replace("Will ", "").replace(" win?", "").strip()
                rows.append({
                    "Event": clean_title,
                    "Kalshi_Yes": m.get('yes_bid', 0),
                    "Kalshi_No": (100 - m.get('yes_ask', 100)) # Cost to bet AGAINST
                })
        return rows
    except Exception as e:
        st.error(f"Kalshi API Error: {e}")
        return []

# --- STREAMLIT UI ---
st.set_page_config(page_title="CBB Arb Hunter 2026", layout="wide")
st.title("🏀 CBB Arb Hunter (Live Feb 1, 2026)")

if st.button('🔄 Refresh Data'):
    st.rerun()

col1, col2 = st.columns(2)

with st.spinner('Fetching markets...'):
    p_data = get_poly_data()
    k_data = get_kalshi_data()

with col1:
    st.subheader("Polymarket Games")
    st.dataframe(pd.DataFrame(p_data))

with col2:
    st.subheader("Kalshi Games")
    st.dataframe(pd.DataFrame(k_data))

# --- ARBITRAGE CALCULATION ---
st.divider()
st.header("🎯 Potential Arbitrage")

if p_data and k_data:
    matches = []
    k_df = pd.DataFrame(k_data)
    
    for p_row in p_data:
        # Find the best match in Kalshi for the Polymarket game title
        match = process.extractOne(p_row['Event'], k_df['Event'], scorer=fuzz.token_set_ratio)
        
        if match and match[1] > 65: # 65% confidence threshold
            k_match_row = k_df[k_df['Event'] == match[0]].iloc[0]
            
            # Arb = 100 - (Price to buy YES on Poly + Price to buy NO on Kalshi)
            cost = p_row['Poly_Yes'] + k_match_row['Kalshi_No']
            profit = 100 - cost
            
            matches.append({
                "Game Match": f"{p_row['Event']} (Poly) ≈ {k_match_row['Event']} (Kalshi)",
                "Poly Yes": f"{p_row['Poly_Yes']}¢",
                "Kalshi No": f"{k_match_row['Kalshi_No']}¢",
                "Total Cost": f"{cost}¢",
                "Profit": f"{profit:.1f}%" if profit > 0 else "No Arb"
            })
    
    if matches:
        res_df = pd.DataFrame(matches)
        def highlight_profit(val):
            if isinstance(val, str) and "%" in val:
                return 'background-color: #d4edda; color: #155724; font-weight: bold'
            return ''

        st.table(res_df.style.applymap(highlight_profit, subset=['Profit']))
    else:
        st.info("No matching games found between exchanges right now.")
else:
    st.warning("Could not find data on one or both exchanges. Check if games have started (API filters out live games).")
