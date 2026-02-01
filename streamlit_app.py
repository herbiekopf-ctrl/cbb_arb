import streamlit as st
import pandas as pd
import requests
from thefuzz import fuzz
from datetime import datetime

st.set_page_config(page_title="Pro CBB Scanner", layout="wide")

# --- UI Sidebar ---
st.sidebar.header("Matching Sensitivity")
time_buffer = st.sidebar.slider("Start Time Window (Hours)", 1, 48, 12)
odds_tolerance = st.sidebar.slider("Odds Similarity Tolerance (%)", 5, 40, 20)
match_threshold = st.sidebar.slider("Name Sensitivity", 10, 95, 35)

def get_name_variants(name):
    name = name.lower()
    noise = ["university of", "university", "state", "univ", "the ", "st.", "saint", "college", "mens", "basketball"]
    clean_base = name
    for word in noise:
        clean_base = clean_base.replace(word, "")
    clean_base = clean_base.strip()
    words = clean_base.split()
    variants = [clean_base]
    if len(words) > 1:
        variants.append("".join([w[0] for w in words])) # Acronym
    return list(set(variants))

# Helper to fetch data once per run
def fetch_raw_data():
    poly_url = "https://gamma-api.polymarket.com/events?tag_id=100639&active=true"
    kalshi_url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&status=open"
    try:
        p_raw = requests.get(poly_url).json()
        k_raw = requests.get(kalshi_url).json().get('markets', [])
        return p_raw, k_raw
    except Exception as e:
        st.error(f"API Error: {e}")
        return [], []

# --- MAIN UI ---
st.title("🏀 CBB Arbitrage Dashboard")

# Create Tabs
tab1, tab2 = st.tabs(["🔍 Arb Scanner", "📊 Raw Odds Audit"])

p_raw, k_raw = fetch_raw_data()

with tab1:
    st.subheader("Potential Arbitrage Opportunities")
    if st.button('🔍 Run Scan'):
        found = []
        for p in p_raw:
            try:
                p_title = p['title']
                p_yes = float(p['markets'][0]['outcomePrices'][0])
                p_time = datetime.fromisoformat(p['startDate'].replace('Z', '+00:00'))
                
                for k in k_raw:
                    k_title = k['title']
                    k_yes = (k.get('yes_bid', 0) / 100)
                    k_no = (k.get('no_ask', 0) / 100)
                    if k_no == 0: continue
                    k_time = datetime.fromisoformat(k['close_time'].replace('Z', '+00:00'))

                    # Time & Odds Filtering
                    time_diff = abs((p_time - k_time).total_seconds() / 3600)
                    if time_diff > time_buffer: continue
                    
                    # Name Matching
                    p_variants = get_name_variants(p_title)
                    k_variants = get_name_variants(k_title)
                    highest_match = max([fuzz.token_set_ratio(pv, kv) for pv in p_variants for kv in k_variants])

                    if highest_match >= match_threshold:
                        total_cost = p_yes + k_no
                        profit_pct = ((1.00 - total_cost) / total_cost) * 100
                        
                        found.append({
                            "Game": p_title,
                            "Match": highest_match,
                            "Poly Yes": p_yes,
                            "Kalshi No": k_no,
                            "Profit %": round(profit_pct, 2),
                            "Is Arb": total_cost < 1.00
                        })
            except: continue
        
        if found:
            df = pd.DataFrame(found).sort_values(by="Profit %", ascending=False).head(5)
            st.table(df)
        else:
            st.warning("No matches found. Check the 'Raw Odds Audit' tab to see if data is loading.")

with tab2:
    st.subheader("Raw Data Feed (Debug)")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Polymarket Raw (First 10)**")
        if p_raw:
            p_list = [{"Title": x.get('title'), "Price": x['markets'][0]['outcomePrices'][0]} for x in p_raw[:10]]
            st.dataframe(pd.DataFrame(p_list))
        else:
            st.error("No data from Polymarket")

    with col2:
        st.write("**Kalshi Raw (First 10)**")
        if k_raw:
            k_list = [{"Title": x.get('title'), "Yes Bid": x.get('yes_bid')} for x in k_raw[:10]]
            st.dataframe(pd.DataFrame(k_list))
        else:
            st.error("No data from Kalshi")
