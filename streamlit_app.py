import streamlit as st
import pandas as pd
import requests
from thefuzz import fuzz
from thefuzz import process

# --- CONFIG ---
POLY_CBB_TAG = "100148"
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

def get_poly_cbb():
    url = f"https://gamma-api.polymarket.com/events?tag_id={POLY_CBB_TAG}&active=true&closed=false"
    try:
        data = requests.get(url).json()
        rows = []
        for event in data:
            for m in event.get('markets', []):
                prices = m.get('outcomePrices', ["0", "0"])
                rows.append({
                    "Event": event.get('title'),
                    "Poly_Yes": round(float(prices[0]) * 100, 1),
                    "Poly_No": round(float(prices[1]) * 100, 1)
                })
        return rows
    except: return []

def get_kalshi_cbb():
    url = f"{KALSHI_BASE}/markets?limit=200&status=open"
    try:
        data = requests.get(url).json().get('markets', [])
        rows = []
        for m in data:
            title = m.get('title', '')
            if any(x in title for x in ["CBB", "NCAA", "College Basketball"]):
                # Cleaning Kalshi titles which often look like "Will [Team] win..."
                clean_title = title.replace("Will ", "").replace(" win?", "").strip()
                rows.append({
                    "Event": clean_title,
                    "Kalshi_Yes": m.get('yes_bid', 0),
                    "Kalshi_No": (100 - m.get('yes_ask', 100)) # Implied No price
                })
        return rows
    except: return []

# --- UI ---
st.set_page_config(page_title="CBB Arb Hunter", layout="wide")
st.title("🏀 CBB Cross-Exchange Arbitrage")

p_raw = get_poly_cbb()
k_raw = get_kalshi_cbb()

if not p_raw or not k_raw:
    st.warning("One or more APIs returned no data. Markets might be closed or keys/tags changed.")
else:
    # --- FUZZY MATCHING LOGIC ---
    matches = []
    poly_df = pd.DataFrame(p_raw)
    kalshi_df = pd.DataFrame(k_raw)

    for _, p_row in poly_df.iterrows():
        # Find best name match in Kalshi list
        match_result = process.extractOne(p_row['Event'], kalshi_df['Event'], scorer=fuzz.token_set_ratio)
        
        if match_result and match_result[1] > 70:  # 70% confidence threshold
            k_row = kalshi_df[kalshi_df['Event'] == match_result[0]].iloc[0]
            
            # Arb Calculation: If (Poly Yes + Kalshi No) < 100
            arb_opp = 100 - (p_row['Poly_Yes'] + k_row['Kalshi_No'])
            
            matches.append({
                "Game": p_row['Event'],
                "Polymarket Yes": f"{p_row['Poly_Yes']}¢",
                "Kalshi No": f"{k_row['Kalshi_No']}¢",
                "Total Cost": p_row['Poly_Yes'] + k_row['Kalshi_No'],
                "Profit Margin": f"{arb_opp:.1f}%" if arb_opp > 0 else "None"
            })

    # --- DISPLAY ---
    st.subheader("Detected Matches & Potential Arbitrage")
    if matches:
        res_df = pd.DataFrame(matches)
        
        # Highlight green if profit exists
        def highlight_arb(s):
            return ['background-color: #90ee90' if (isinstance(val, str) and "%" in val and float(val.replace('%','')) > 0) else '' for val in s]
        
        st.table(res_df.style.apply(highlight_arb, axis=1))
    else:
        st.info("No close naming matches found between the two exchanges.")

st.divider()
st.caption("Note: 'Total Cost' below 100 indicates a theoretical arbitrage opportunity.")
