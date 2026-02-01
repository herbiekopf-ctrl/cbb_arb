import streamlit as st
import pandas as pd
import requests
from thefuzz import fuzz

st.set_page_config(page_title="CBB Arb Scanner", layout="wide")

# --- UI Sidebar Settings ---
st.sidebar.header("⚙️ Strategy Settings")
bankroll = st.sidebar.number_input("Total Bankroll ($)", value=1000, step=100)
kelly_fraction = st.sidebar.slider("Kelly Fraction (0.5 = Half Kelly)", 0.1, 1.0, 0.5)
match_threshold = st.sidebar.slider("Fuzzy Match Sensitivity", 50, 95, 70)

st.title("🏀 No-Key CBB Arbitrage Scanner")
st.caption("Using RapidFuzz for name matching & Public APIs for data")

def get_data():
    # 1. Get Polymarket CBB Data (Public Gamma API)
    poly_url = "https://gamma-api.polymarket.com/events?tag_id=100639&active=true"
    poly_data = requests.get(poly_url).json()
    
    # 2. Get Kalshi CBB Data (Public V2 API)
    kalshi_url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=100&status=open"
    kalshi_data = requests.get(kalshi_url).json().get('markets', [])
    
    opportunities = []

    for p_event in poly_data:
        p_title = p_event['title']
        # Extract prices safely
        try:
            p_yes = float(p_event['markets'][0]['outcomePrices'][0])
            p_no = float(p_event['markets'][0]['outcomePrices'][1])
        except: continue
        
        for k_market in kalshi_data:
            k_title = k_market['title']
            
            # --- FUZZY MATCHING LOGIC ---
            # token_set_ratio ignores word order (Duke vs UNC == UNC @ Duke)
            score = fuzz.token_set_ratio(p_title, k_title)
            
            if score >= match_threshold:
                k_yes = k_market.get('yes_bid', 0) / 100
                k_no = k_market.get('no_bid', 0) / 100
                
                # Check Arb: Buy Poly YES ($p_yes) + Kalshi NO ($k_no)
                cost = p_yes + k_no
                if 0 < cost < 0.99:
                    profit_pct = (1 - cost) * 100
                    
                    # Kelly Criterion: f = (bp - q) / b
                    b = (1 / cost) - 1  # Odds
                    p = 0.5             # Conservative win prob
                    f_star = ((p * b) - (1 - p)) / b
                    bet_amount = max(0, f_star * bankroll * kelly_fraction)

                    opportunities.append({
                        "Match Score": score,
                        "Game": f"{p_title} (Poly) vs {k_title} (Kalshi)",
                        "Strategy": "Buy Poly YES / Kalshi NO",
                        "Total Cost": f"${round(cost, 2)}",
                        "Profit": f"{round(profit_pct, 1)}%",
                        "Kelly Bet": f"${round(bet_amount, 2)}"
                    })

    return opportunities

if st.button('🚀 Scan for Arbitrage'):
    results = get_data()
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.warning("No arbs found. High-frequency bots usually take these in seconds.")

st.info("Note: This uses public data. Execution requires a separate script with API Keys.")
