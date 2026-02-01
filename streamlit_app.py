import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION ---
# Polymarket Tag for NCAA Men's Basketball: 100148
POLY_CBB_TAG = "100148"
# Kalshi often uses series prefixes like 'KXMARMAD' (March Madness) or 'KXCBB'
KALSHI_CBB_PREFIX = "KXCBB" 

def fetch_cbb_data():
    # Targeted Polymarket CBB fetch
    poly_url = f"https://gamma-api.polymarket.com/events?tag_id={POLY_CBB_TAG}&active=true&closed=false"
    # Targeted Kalshi market fetch
    kalshi_url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&status=open"
    
    try:
        p_data = requests.get(poly_url).json()
        k_data = requests.get(kalshi_url).json().get('markets', [])
        
        # Filter Kalshi specifically for College Basketball strings if no direct tag is available
        k_cbb = [m for m in k_data if "College Basketball" in m.get('title', '') or KALSHI_CBB_PREFIX in m.get('ticker', '')]
        return p_data, k_cbb
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return [], []

st.title("🏀 CBB Precision Scanner")
tab1, tab2 = st.tabs(["🔍 Arb Scanner", "📊 Raw Data Audit"])

p_raw, k_raw = fetch_cbb_data()

with tab1:
    st.subheader("Targeted NCAA Matches")
    # (Existing matching logic goes here, now pre-filtered for CBB)
    st.info(f"Scanning {len(p_raw)} Polymarket CBB events vs {len(k_raw)} Kalshi CBB markets.")

with tab2:
    st.subheader("Live Price Audit")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### Polymarket (Yes Prices)")
        if p_raw:
            p_audit = []
            for event in p_raw:
                for m in event.get('markets', []):
                    # outcomePrices[0] is typically the 'Yes' price
                    price = m.get('outcomePrices', [0, 0])[0]
                    p_audit.append({"Game": event['title'], "Yes Price": f"{float(price)*100:.1f}¢"})
            st.dataframe(pd.DataFrame(p_audit), use_container_width=True)
        else:
            st.warning("No CBB data found on Polymarket.")

    with c2:
        st.markdown("### Kalshi (Order Book)")
        if k_raw:
            k_audit = []
            for m in k_raw:
                # Kalshi uses cents (0-100)
                k_audit.append({
                    "Market": m.get('title'),
                    "Yes Bid": f"{m.get('yes_bid', 0)}¢",
                    "No Ask": f"{m.get('no_ask', 0)}¢"
                })
            st.dataframe(pd.DataFrame(k_audit), use_container_width=True)
        else:
            st.warning("No CBB data found on Kalshi.")
