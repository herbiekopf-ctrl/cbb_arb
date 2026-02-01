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
time_buffer = st.sidebar.slider("Start Time Window (Hours)", 1, 48, 12) # Expanded default
odds_tolerance = st.sidebar.slider("Odds Similarity Tolerance (%)", 5, 40, 20)
match_threshold = st.sidebar.slider("Name Sensitivity", 10, 95, 35) # Lowered default for acronyms

def get_name_variants(name):
    """
    Condenses long names into acronyms and stretches short names into possibilities.
    Returns a list of variations to check against.
    """
    name = name.lower()
    # Remove fluff
    noise = ["university of", "university", "state", "univ", "the ", "st.", "saint", "college", "mens", "basketball"]
    clean_base = name
    for word in noise:
        clean_base = clean_base.replace(word, "")
    
    clean_base = clean_base.strip()
    words = clean_base.split()
    
    variants = [clean_base]
    
    # 1. Create Acronym (e.g., 'north carolina' -> 'unc')
    if len(words) > 1:
        acronym = "".join([w[0] for w in words])
        variants.append(acronym)
        # Special case: Many schools use 'u' prefix (UConn, UMich)
        variants.append("u" + words[0])
    
    # 2. Add 'State' back to common acronyms
    if "st" in clean_base:
        variants.append(clean_base.replace("st", "state"))

    return list(set(variants))

def get_data():
    # Tag 100639 = CBB Game Winners
    poly_url = "https://gamma-api.polymarket.com/events?tag_id=100639&active=true"
    kalshi_url = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&status=open"
    
    try:
        p_data = requests.get(poly_url).json()
        k_data = requests.get(kalshi_url).json().get('markets', [])
    except:
        return []

    found = []
    for p in p_data:
        try:
            p_title = p['title']
            # Better Odds Logic: Poly Yes vs Poly No
            # Usually we compare Poly Yes to Kalshi No
            p_yes = float(p['markets'][0]['outcomePrices'][0])
            p_no = float(p['markets'][0]['outcomePrices'][1])
            
            p_time = datetime.fromisoformat(p['startDate'].replace('Z', '+00:00'))
            
            for k in k_data:
                k_title = k['title']
                
                # Fetch Kalshi Yes/No
                k_yes = (k.get('yes_bid', 0) / 100)
                k_no = (k.get('no_ask', 0) / 100)
                if k_no == 0: continue
                
                k_time = datetime.fromisoformat(k['close_time'].replace('Z', '+00:00'))

                # --- LAYER 1: TIME CHECK ---
                time_diff = abs((p_time - k_time).total_seconds() / 3600)
                if time_diff > time_buffer:
                    continue

                # --- LAYER 2: BETTER ODDS SELECTION ---
                # We want the cheapest way to buy 'Outcome A' and 'Not Outcome A'
                # Poly_Yes + Kalshi_No is the standard Arb path.
                total_cost = p_yes + k_no
                
                # --- LAYER 3: ADVANCED NAME MATCHING ---
                p_variants = get_name_variants(p_title)
                k_variants = get_name_variants(k_title)
                
                highest_match = 0
                for pv in p_variants:
                    for kv in k_variants:
                        score = fuzz.token_set_ratio(pv, kv)
                        if score > highest_match:
                            highest_match = score

                if highest_match >= match_threshold:
                    # Final Arb Calculation
                    profit_pct = ((1.00 - total_cost) / total_cost) * 100
                    
                    # Only odds-gate it if it's NOT a potential Arb
                    # If it IS an arb, we want to see it even if prices are weird
                    if total_cost > 1.00 and abs(p_yes - k_yes) > (odds_tolerance / 100):
                        continue

                    found.append({
                        "Game": f"{p_title} / {k_title}",
                        "Match Score": highest_match,
                        "Poly Yes": round(p_yes, 2),
                        "Kalshi No": round(k_no, 2),
                        "Total Cost": round(total_cost, 2),
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
        # Sort by Profitability
        top_5 = df.sort_values(by="Profit %", ascending=False).head(5)
        st.write("### Top 5 Market Comparisons")
        st.table(top_5.style.apply(style_rows, axis=1))
    else:
        st.warning("No matches found. Try lowering 'Name Sensitivity' to 20 or widening 'Time Window'.")

st.divider()
st.caption("Note: This scanner uses fuzzy logic. Always verify the team names on the actual exchange before placing trades.")
