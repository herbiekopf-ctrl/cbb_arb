import streamlit as st
import pandas as pd
import requests
from thefuzz import fuzz

st.set_page_config(page_title="Top 5 CBB Arbs", layout="wide")

st.title("🏀 Top 5 CBB Arbitrage Opportunities")
st.sidebar.header("Filter Settings")
match_sensitivity = st.sidebar.slider("Name Match Sensitivity", 50, 95, 75)

def get_arb_data():
    # Fetching Data (Same as before)
    poly_url = "https://gamma-api.polymarket.com/events?tag_id=100639&active=true"
    kalshi_url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=100&status=open"
    
    try:
        poly_events = requests.get(poly_url).json()
        kalshi_markets = requests.get(kalshi_url).json().get('markets', [])
    except:
        return []

    found = []
    for p_event in poly_events:
        try:
            p_title = p_event.get('title', "")
            p_price = float(p_event['markets'][0]['outcomePrices'][0])
            
            for k_market in kalshi_markets:
                k_title = k_market.get('title', "")
                score = fuzz.token_set_ratio(p_title, k_title)
                
                if score >= match_sensitivity:
                    k_no_price = k_market.get('no_ask', 0) / 100
                    if k_no_price == 0: continue
                    
                    total_cost = p_price + k_no_price
                    # We calculate profit even if it's negative so we can show "Top 5"
                    profit_raw = 1.00 - total_cost
                    profit_pct = (profit_raw / total_cost) * 100
                    
                    found.append({
                        "Game": p_title,
                        "Poly Yes": p_price,
                        "Kalshi No": k_no_price,
                        "Total Cost": round(total_cost, 2),
                        "Profit %": round(profit_pct, 2),
                        "Is Arb": total_cost < 1.00
                    })
        except: continue
    return found

# Styling function to turn the row green if it's a real Arb
def highlight_arb(row):
    if row['Is Arb']:
        return ['background-color: #d4edda; color: #155724; font-weight: bold'] * len(row)
    return [''] * len(row)

if st.button('🔍 Scan Now'):
    data = get_arb_data()
    if data:
        # 1. Convert to DataFrame
        df = pd.DataFrame(data)
        
        # 2. Sort by Profit % and take only the top 5
        top_5 = df.sort_values(by="Profit %", ascending=False).head(5)
        
        # 3. Apply the Green Highlight
        styled_df = top_5.style.apply(highlight_arb, axis=1)
        
        st.write("### Top 5 Market Comparisons")
        st.table(styled_df) # Use st.table for a clean look or st.dataframe for interactive
    else:
        st.info("No matching games found. Check back later!")

st.divider()
st.caption("Green rows indicate a mathematical arbitrage (Profit % > 0).")
