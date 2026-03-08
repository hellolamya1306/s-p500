import pandas as pd

df = pd.read_excel("/content/S&P55.xlsx", sheet_name = "7 largest stocks per sector")

df['fcf_yield'] = df['fcf'] / df['market_cap']

df['intrinsic_value'] = df["market_cap"] * (df['fcf_yield'] / 0.06) # damodaran

df['margin_of_safety'] = (df['intrinsic_value'] - df['market_cap']) / df['market_cap']

df

df.describe()

df["sector"].unique()

#bayesian is an overkill, so going with minmaxscaler and 75th percentile as threshold
#'roe', 'net_margin','op_margin', 'gross_margin', 'rev_growth', 'earnings_growth','current_ratio',
#'debt_to_equity', 'fcf', 'eps', 'pe', 'pb', 'ps','peg'

df.select_dtypes(include=['number']).columns

number_columns = ['roe', 'net_margin', 'op_margin', 'gross_margin',
       'rev_growth', 'earnings_growth', 'current_ratio', 'debt_to_equity',
       'fcf', 'eps', 'pe', 'pb', 'ps', 'peg', 'fcf_yield', 'intrinsic_value',
       'margin_of_safety']

from sklearn.preprocessing import MinMaxScaler
minmax = MinMaxScaler()

for i in number_columns:
  minmax.fit(df[[i]])
  df[i] = minmax.transform(df[[i]])

df.describe()

#loading data

def load_yahoo_fundamentals(ticker):
    try:
        row = df[df["ticker"] == ticker]

        if row.empty:
            return None

        row = row.iloc[0]

        return {
            "company_name": row["company_name"],
            "sector": row["sector"],
            "market_cap": row["market_cap"],
            "roe": row["roe"],
            "net_margin": row["net_margin"],
            "op_margin": row["op_margin"],
            "rev_growth": row["rev_growth"],
            "earnings_growth": row["earnings_growth"],
            "current_ratio": row["current_ratio"],
            "debt_to_equity": row["debt_to_equity"],
            "fcf": row["fcf"],
            "eps": row["eps"],
            "pe": row["pe"],
            "pb": row["pb"],
            "ps": row["ps"],
            "fcf_yield": row["fcf_yield"],
            "margin_of_safety": row["margin_of_safety"],
        }

    except Exception as e:
        print(e)
        return None

def load_yahoo_growth_metrics(ticker):
    try:
        row = df[df["ticker"] == ticker]

        if row.empty:
            return None

        row = row.iloc[0]

        return {
            "company_name": row["company_name"],
            "sector": row["sector"],
            "market_cap": row["market_cap"],
            "revenue_growth": row["rev_growth"],
            "earnings_growth": row["earnings_growth"],
            "gross_margin": row["gross_margin"],
            "operating_margin": row["op_margin"],
            "net_margin": row["net_margin"],
            "peg_ratio": row["peg"],
            "ps_ratio": row["ps"],
            "debt_to_equity": row["debt_to_equity"],
            "current_ratio": row["current_ratio"],
            "fcf_yield": row["fcf_yield"],
            "margin_of_safety": row["margin_of_safety"],
        }

    except Exception as e:
        print(e)
        return None

import json
import gradio as gr

def market_cap_bucket(market_cap):
    if market_cap is None:
        return None

    if market_cap >= 250e9:
        return "Above $250B"
    elif 150e9 <= market_cap < 250e9:
        return "$150B–$250B"
    elif 100e9 <= market_cap < 150e9:
        return "$100B–$150B"
    elif 50e9 <= market_cap < 100e9:
        return "$50B–$100B"
    else:
        return "Below $50B"

def analyze_growth_agent(m):
    scores = {}


    # ---------------------------
    # 1. Growth trends
    # ---------------------------
    growth_score = 0
    if m["revenue_growth"] is not None:
        if m["revenue_growth"] >= df['rev_growth'].quantile(0.75):
            growth_score += 0.5
        elif m["revenue_growth"] >= df['rev_growth'].quantile(0.50):
            growth_score += 0.25


    if m["earnings_growth"] is not None:
        if m["earnings_growth"] >= df['earnings_growth'].quantile(0.75):
            growth_score += 0.5
        elif m["earnings_growth"] >= df['earnings_growth'].quantile(0.50):
            growth_score += 0.25


    scores["growth"] = min(growth_score, 1.0)


    # ---------------------------
    # 2. Growth valuation
    # ---------------------------
    valuation_score = 0
    if m["peg_ratio"] is not None:
        if m["peg_ratio"] <= df['peg'].quantile(0.25):
            valuation_score += 0.6
        elif m["peg_ratio"] <= df['peg'].quantile(0.50):
            valuation_score += 0.3


    if m["ps_ratio"] is not None:
        if m["ps_ratio"] <= df['ps'].quantile(0.25):
            valuation_score += 0.4
        elif m["ps_ratio"] <= df['ps'].quantile(0.50):
            valuation_score += 0.2


    scores["valuation"] = min(valuation_score, 1.0)


    # ---------------------------
    # 3. Margin expansion
    # ---------------------------
    margin_score = 0
    if m["gross_margin"] is not None and m["gross_margin"] >= df['gross_margin'].quantile(0.75):
        margin_score += 0.3
    if m["operating_margin"] is not None and m["operating_margin"] >= df['op_margin'].quantile(0.75):
        margin_score += 0.4
    if m["net_margin"] is not None and m["net_margin"] >= df['net_margin'].quantile(0.75):
        margin_score += 0.3


    scores["margins"] = min(margin_score, 1.0)


    # ---------------------------
    # 4. Financial health
    # ---------------------------
    health_score = 0
    if m["debt_to_equity"] is not None and m["debt_to_equity"] <= df['debt_to_equity'].quantile(0.50):
        health_score += 0.5
    if m["current_ratio"] is not None and m["current_ratio"] >= df['current_ratio'].quantile(0.50):
        health_score += 0.5


    scores["health"] = max(health_score, 0.0)


    # ---------------------------
    # Aggregate
    # ---------------------------
    weights = {
        "growth": 0.40,
        "valuation": 0.30,
        "margins": 0.20,
        "health": 0.10,
    }


    weighted_score = sum(scores[k] * weights[k] for k in scores)


    if weighted_score > 0.6:
        signal = "bullish"
    elif weighted_score < 0.4:
        signal = "bearish"
    else:
        signal = "neutral"


    #confidence = round(abs(weighted_score - 0.5) * 2 * 100)


    return signal, round(weighted_score, 2), (
        f"Growth score: {scores['growth']:.2f}, "
        f"Valuation: {scores['valuation']:.2f}, "
        f"Margins: {scores['margins']:.2f}, "
        f"Health: {scores['health']:.2f}"
    )

def analyze_michael_burry(m):
    score = 0
    reasons = []


    # ---------------------------
    # 1. Free Cash Flow Yield
    # ---------------------------
    if m["fcf_yield"] and m["fcf_yield"] >= df['fcf_yield'].quantile(0.75):
      score += 3
      reasons.append(f"High FCF yield {m['fcf_yield']:.1%}")
    elif m["fcf_yield"] and m["fcf_yield"] >= df['fcf_yield'].quantile(0.50):
      score += 2
      reasons.append(f"Decent FCF yield {m['fcf_yield']:.1%}")
    else:
      reasons.append(f"Low FCF yield {m['fcf_yield']:.1%}")


    # ---------------------------
    # 2. Valuation
    # ---------------------------
    if m["pe"] and m["pe"] <= df['pe'].quantile(0.50):
        score += 2
        reasons.append(f"Low P/E {m['pe']:.1f}")
    elif m["pe"] and m["pe"] <= df['pe'].quantile(0.75):
        score += 1
        reasons.append(f"Moderate P/E {m['pe']:.1f}")


    if m["pb"] and m["pb"] <= df['pb'].quantile(0.50):
        score += 1
        reasons.append(f"Low P/B {m['pb']:.2f}")


    # ---------------------------
    # 3. Balance Sheet
    # ---------------------------
    if m["debt_to_equity"] is not None:
        if m["debt_to_equity"] <= df['debt_to_equity'].quantile(0.25):
            score += 2
            reasons.append(f"Low leverage D/E {m['debt_to_equity']:.2f}")
        elif m["debt_to_equity"] <= df['debt_to_equity'].quantile(0.50):
            score += 1
            reasons.append(f"Acceptable leverage D/E {m['debt_to_equity']:.2f}")
        else:
            reasons.append(f"High leverage D/E {m['debt_to_equity']:.2f}")


    # ---------------------------
    # 4. Contrarian Check
    # ---------------------------
    if m["net_margin"] is not None and m["net_margin"] >= df['net_margin'].quantile(0.50):
        score += 1
        reasons.append("Depressed margins — potential contrarian opportunity")


    # ---------------------------
    # Final Signal
    # ---------------------------
    if score >= 5:
        signal = "bullish"
    elif score <= 2:
        signal = "bearish"
    else:
        signal = "neutral"


    #confidence = min(score / 8 * 100, 100)


    return signal, score, "; ".join(reasons)

def analyze_damodaran(m):
    score = 0
    reasons = []

    # ---------------------------
    # 1. Growth (Revenue proxy)
    # ---------------------------
    if m["rev_growth"] is not None:
        if m["rev_growth"] >= df['rev_growth'].quantile(0.75):
            score += 2
            reasons.append(f"Strong revenue growth {m['rev_growth']:.1%}")
        elif m["rev_growth"] >= df['rev_growth'].quantile(0.50):
            score += 1
            reasons.append(f"Moderate revenue growth {m['rev_growth']:.1%}")
        else:
            reasons.append(f"Weak revenue growth {m['rev_growth']:.1%}")

    # ---------------------------
    # 2. Risk (Balance sheet)
    # ---------------------------
    if m["debt_to_equity"] is not None:
        if m["debt_to_equity"] <= df['debt_to_equity'].quantile(0.25):
            score += 2
            reasons.append(f"Low leverage D/E {m['debt_to_equity']:.2f}")
        elif m["debt_to_equity"] <= df['debt_to_equity'].quantile(0.50):
            score += 1
            reasons.append(f"Moderate leverage D/E {m['debt_to_equity']:.2f}")
        else:
            reasons.append(f"High leverage D/E {m['debt_to_equity']:.2f}")

    # ---------------------------
    # 3. Profitability (ROE proxy)
    # ---------------------------
    if m["roe"] is not None:
        if m["roe"] >= df['roe'].quantile(0.75):
            score += 2
            reasons.append(f"High ROE {m['roe']:.1%}")
        elif m["roe"] >= df['roe'].quantile(0.50):
            score += 1
            reasons.append(f"Acceptable ROE {m['roe']:.1%}")
        else:
            reasons.append(f"Low ROE {m['roe']:.1%}")

    # ---------------------------
    # 4. Intrinsic Value Proxy (FCF Yield)
    # ---------------------------

    if m['margin_of_safety'] is not None:
      if m['margin_of_safety'] >= df['margin_of_safety'].quantile(0.75):
        score += 2
        reasons.append(f"Large margin of safety {m['margin_of_safety'] :.1%}")
      elif m['margin_of_safety']  >= df['margin_of_safety'].quantile(0.50):
        score += 1
        reasons.append(f"Some margin of safety {m['margin_of_safety'] :.1%}")
      else:
        reasons.append(f"Limited margin of safety {m['margin_of_safety'] :.1%}")

    # ---------------------------
    # Final Damodaran Signal
    # ---------------------------
    if score >= 5:
        signal = "bullish"
    elif score <= 3:
        signal = "bearish"
    else:
        signal = "neutral"

    #confidence = min(score / 9 * 100, 100)

    reasoning = "; ".join(reasons)

    return (
        signal,
        score,
        m['margin_of_safety'] ,
        reasoning,
    )

def analyze_buffett(m):
    score = 0
    reasons = []

    # 1. Return on Equity (Quality)
    if m["roe"] is not None:
        if m["roe"] >= df['roe'].quantile(0.75):
            score += 2
            reasons.append(f"High ROE {m['roe']:.1%}")
        elif m["roe"] >= df['roe'].quantile(0.50):
            score += 1
            reasons.append(f"Moderate ROE {m['roe']:.1%}")
        else:
            reasons.append(f"Low ROE {m['roe']:.1%}")

    # 2. Debt Discipline
    if m["debt_to_equity"] is not None:
        if m["debt_to_equity"] <= df['debt_to_equity'].quantile(0.25):
            score += 2
            reasons.append("Low debt")
        elif m["debt_to_equity"] <= df['debt_to_equity'].quantile(0.50):
            score += 1
            reasons.append("Acceptable debt")
        else:
            reasons.append("High leverage")

    # 3. Profitability / Moat Proxy
    if m["net_margin"] is not None:
        if m["net_margin"] >= df['net_margin'].quantile(0.75):
            score += 2
            reasons.append("Strong net margins")
        elif m["net_margin"] >= df['net_margin'].quantile(0.50):
            score += 1
            reasons.append("Decent margins")
        else:
            reasons.append("Weak margins")

    # 4. Free Cash Flow Strength
    if m['fcf_yield'] is not None:
      if m['fcf_yield'] >= df['fcf_yield'].quantile(0.75):
        score += 2
        reasons.append(f"Attractive FCF yield {m['fcf_yield']:.1%}")
      elif m['fcf_yield'] >= df['fcf_yield'].quantile(0.50):
        score += 1
        reasons.append(f"Moderate FCF yield {m['fcf_yield']:.1%}")
      else:
        reasons.append("Low FCF yield")

    # 5. Valuation sanity check
    if m["pe"] is not None:
        if m["pe"] <= df['pe'].quantile(0.25):
            score += 2
            reasons.append("Reasonable valuation")
        elif m["pe"] <= df['pe'].quantile(0.50):
            score += 1
            reasons.append("Fair valuation")
        else:
            reasons.append("Expensive valuation")

    # Final signal
    if score >= 6:
        signal = "bullish"
    elif score <= 4:
        signal = "bearish"
    else:
        signal = "neutral"

    #confidence = min(int(score / 10 * 100), 100)

    return signal, score, "; ".join(reasons)

#growth, burry, damodaran, buffett

from tqdm import tqdm

def run_growth_agent(filter_signal, filter_mode, sector_choice, mcap_choice):
    tickers = df['ticker'].to_list()
    rows = []


    for ticker in tqdm(tickers):
        metrics = load_yahoo_growth_metrics(ticker)
        if not metrics:
            continue


        # Filters
        if filter_mode == "Sector":
           if not sector_choice:
              continue
           if metrics["sector"] != sector_choice:
              continue


        if filter_mode == "Market Cap":
           if not mcap_choice:
              continue
           bucket = market_cap_bucket(metrics["market_cap"])
           if bucket != mcap_choice:
              continue


        signal, score, reasoning = analyze_growth_agent(metrics)

        if filter_signal != "All" and signal != filter_signal.lower():

            continue


        rows.append({
            "Ticker": ticker,
            "Company Name": metrics["company_name"],
            "Sector": metrics["sector"],
            "Market Cap ($B)": round(metrics["market_cap"] / 1e9, 1) if metrics["market_cap"] else
None,
            "Growth Signal": signal.capitalize(),
            "Score": score,
            "Reasoning": reasoning,
        })


    if not rows:
        empty_df = pd.DataFrame(columns=[
            "Ticker", "Company Name", "Sector", "Market Cap ($B)", "Growth Signal", "Score", "Reasoning"
        ])
        return empty_df, None, empty_df
    growth_df = pd.DataFrame(rows)

    growth_df = growth_df.sort_values(
    by=["Sector", "Score"],
    ascending=[True, False]
    )

    growth_df = growth_df.groupby("Sector").head(5).reset_index(drop=True)
    growth_df.to_json("growth_agent.json", orient="records", indent=4)


    return growth_df, "growth_agent.json", growth_df

def run_michael_burry_agent(filter_signal, filter_mode, sector_choice, mcap_choice):
    tickers = df['ticker'].to_list()
    rows = []


    for ticker in tqdm(tickers):
        m = load_yahoo_fundamentals(ticker)
        if not m:
            continue


        # Filters
        if filter_mode == "Sector":
            if not sector_choice or m["sector"] != sector_choice:
                continue


        if filter_mode == "Market Cap":
            if not mcap_choice:
                continue
            if market_cap_bucket(m["market_cap"]) != mcap_choice:
                continue


        signal, score, reasoning = analyze_michael_burry(m)

        if filter_signal != "All" and signal != filter_signal.lower():

            continue

        rows.append({
            "Ticker": ticker,
            "Company Name": m["company_name"],
            "Sector": m["sector"],
            "Market Cap ($B)": round(m["market_cap"] / 1e9, 1) if m["market_cap"] else None,
            "Burry Signal": signal.capitalize(),
            "Score": score,
            "Reasoning": reasoning,
        })


    if not rows:
        empty_df =  pd.DataFrame(columns=[
            "Ticker", "Company Name", "Sector","Market Cap ($B)",
            "Burry Signal","Score","Reasoning"
        ])
        return empty_df, None, empty_df


    burry_df = pd.DataFrame(rows)

    burry_df = burry_df.sort_values(
    by=["Sector", "Score"],
    ascending=[True, False]
    )
    burry_df = burry_df.groupby("Sector").head(5).reset_index(drop=True)
    burry_df.to_json("burry.json", orient="records", indent=4)


    return burry_df, "burry.json", burry_df

def run_damodaran_agent(filter_signal, filter_mode, sector_choice, mcap_choice):
    tickers = df['ticker'].to_list()
    rows = []

    for ticker in tqdm(tickers):
        m = load_yahoo_fundamentals(ticker)
        if not m:
            continue

        # Filters
        if filter_mode == "Sector":
            if not sector_choice or m["sector"] != sector_choice:
                continue

        if filter_mode == "Market Cap":
            if not mcap_choice:
                continue
            if market_cap_bucket(m["market_cap"]) != mcap_choice:
                continue

        signal, score, mos, reasoning = analyze_damodaran(m)

        if filter_signal != "All" and signal != filter_signal.lower():
            continue

        rows.append({
            "Ticker": ticker,
            "Company Name": m["company_name"],
            "Sector": m["sector"],
            "Market Cap ($B)": round(m["market_cap"] / 1e9, 1) if m["market_cap"] else None,
            "Damodaran Signal": signal.capitalize(),
            "Score": score,
            "Margin of Safety": round(mos * 100, 1) if mos is not None else None,
            "Reasoning": reasoning,
        })

    if not rows:
        empty_df = pd.DataFrame(columns=[
            "Ticker","Company Name","Sector","Market Cap ($B)",
            "Damodaran Signal","Score","Margin of Safety","Reasoning"
        ])
        return empty_df, None, empty_df

    damodaran_df = pd.DataFrame(rows)

    damodaran_df = damodaran_df.sort_values(
    by=["Sector", "Score"],
    ascending=[True, False])

    damodaran_df = damodaran_df.groupby("Sector").head(5).reset_index(drop=True)

    damodaran_df.to_json("damodaran.json", orient="records", indent=4)

    return damodaran_df, "damodaran.json", damodaran_df

def run_buffett_agent(filter_signal, filter_mode, sector_choice, mcap_choice):
    tickers = df['ticker'].to_list()
    rows = []

    for ticker in tqdm(tickers):
        m = load_yahoo_fundamentals(ticker)
        if not m:
            continue

        # Filters
        if filter_mode == "Sector":
            if not sector_choice or m["sector"] != sector_choice:
                continue

        if filter_mode == "Market Cap":
            if not mcap_choice:
                continue
            if market_cap_bucket(m["market_cap"]) != mcap_choice:
                continue

        signal, score, reasoning = analyze_buffett(m)

        if filter_signal != "All" and signal != filter_signal.lower():
            continue

        rows.append({
            "Ticker": ticker,
            "Company Name": m["company_name"],
            "Sector": m["sector"],
            "Market Cap ($B)": round(m["market_cap"] / 1e9, 1) if m["market_cap"] else None,
            "Buffett Signal": signal.capitalize(),
            "Score": score,
            "Reasoning": reasoning,
        })

    if not rows:
        empty_df = pd.DataFrame(columns=[
            "Ticker","Company Name","Sector","Market Cap ($B)",
            "Buffett Signal","Score","Reasoning"
        ])
        return empty_df, None, empty_df

    buffett_df = pd.DataFrame(rows)

    buffett_df = buffett_df.sort_values(
    by=["Sector", "Score"],
    ascending=[True, False]
    )

    buffett_df = buffett_df.groupby("Sector").head(5).reset_index(drop=True)

    buffett_df.to_json("buffett.json", orient="records", indent=4)

    return buffett_df, "buffett.json", buffett_df

def analyze_consensus(m_fundamental, m_growth):
    bullish_count = 0
    bullish_agents = []

    # Growth
    if m_growth:
        sig, _, _ = analyze_growth_agent(m_growth)
        if sig == "bullish":
            bullish_count += 1
            bullish_agents.append("Growth")

    # Burry
    sig, _, _ = analyze_michael_burry(m_fundamental)
    if sig == "bullish":
        bullish_count += 1
        bullish_agents.append("Burry")

    # Damodaran
    sig, _, _, _ = analyze_damodaran(m_fundamental)
    if sig == "bullish":
        bullish_count += 1
        bullish_agents.append("Damodaran")


    # Buffett
    sig, _, _ = analyze_buffett(m_fundamental)
    if sig == "bullish":
        bullish_count += 1
        bullish_agents.append("Buffett")


    # Star logic
    if bullish_count > 2:
        signal = "Long"
    elif bullish_count < 2:
        signal = "Short"
    else:
        signal = "Neutral"


    return bullish_count, signal, ", ".join(bullish_agents)

def run_consensus_agent(filter_mode, sector_choice, mcap_choice):
    growth_df, _, _ = run_growth_agent("All", "None", None, None)
    burry_df, _, _ = run_michael_burry_agent("All", "None", None, None)
    damodaran_df, _, _ = run_damodaran_agent("All", "None", None, None)
    buffett_df, _, _ = run_buffett_agent("All", "None", None, None)
    final_df = pd.concat([growth_df, burry_df, damodaran_df, buffett_df])

    final_df = (
        final_df[['Ticker']]
        .drop_duplicates()
        .reset_index(drop=True))

    tickers = final_df['Ticker'].to_list()
    rows = []

    for ticker in tqdm(tickers):
        m_fundamental = load_yahoo_fundamentals(ticker)
        m_growth = load_yahoo_growth_metrics(ticker)

        if not m_fundamental:
            continue

        # Filters
        if filter_mode == "Sector":
            if not sector_choice or m_fundamental["sector"] != sector_choice:
                continue

        if filter_mode == "Market Cap":
            if not mcap_choice:
                continue
            if market_cap_bucket(m_fundamental["market_cap"]) != mcap_choice:
                continue

        bullish_count, signal, agents = analyze_consensus(
            m_fundamental,
            m_growth
        )

        rows.append({
            "Ticker": ticker,
            "Company Name": m_fundamental["company_name"],
            "Sector": m_fundamental["sector"],
            "Market Cap ($B)": round(m_fundamental["market_cap"] / 1e9, 1)
                if m_fundamental["market_cap"] else None,
            "Bullish Count": bullish_count,
            "Signal": signal,
            "Agents": agents,
        })

    consensus_df = pd.DataFrame(rows).sort_values(
        ["Bullish Count", "Market Cap ($B)"],
        ascending=[False, False]
    )

    return consensus_df

growth_df, _, _ = run_growth_agent("All", "None", None, None)
burry_df, _, _ = run_michael_burry_agent("All", "None", None, None)
damodaran_df, _, _ = run_damodaran_agent("All", "None", None, None)
buffett_df, _, _ = run_buffett_agent("All", "None", None, None)
consensus_df = run_consensus_agent("None", None, None)

tickers_g = growth_df['Ticker'].unique().tolist()
tickers_b = burry_df['Ticker'].unique().tolist()
tickers_d = damodaran_df['Ticker'].unique().tolist()
tickers_ff = buffett_df['Ticker'].unique().tolist()
tickers_c = consensus_df['Ticker'].unique().tolist()

"""META, BRK-B, BKNG, GOOGL, AVGO, V, MA, HD, UNH, NEM, MO, EOG, NVDA, AAPL, AMZN, LLY, XOM, JNJ, MU, COST, ABBV, CVX, CAT, NFLX, PM, RTX, TMUS, LIN, VZ, AMGN, ABT, BA, DE, UNP, LOW, APP, COP, PLD, FCX, AMT, ECL, CRH, MNST, SLB, SPG, APD, SRE, O, VST, TSLA, WMT, JPM, ORCL, BAC, PG, GE, AMD, PLTR, MRK, GS, T, NEE, TJX, HON, WELL, CEG, SO, DUK, NKE, SHW, WMB, CL, KMI, AEP, DLR"""

with gr.Blocks(title="S&P 500 Screener",
              css="""
              .agent-btn {
              width: 320px;
              height: 55px;
              font-size: 16px;
              font-weight: 600;
              }
              """
              ) as demo:
    gr.Markdown("##  S&P 500 Fundamental Analysis Dashboard")
    gr.Markdown("Hedge fund agents for S&P500 stocks")


    with gr.Row():
        with gr.Column(scale=3):
          filter_signal = gr.Radio(
                choices=["All", "Bullish", "Bearish", "Neutral"],
                value="All",
                label="Filter by Signal"
            )
          filter_mode = gr.Radio(
                choices=["None", "Sector", "Market Cap"],
                value="None",
                label="Filter Mode"
            )

          sector_dropdown = gr.Radio(
                choices=df['sector'].unique().tolist(),
                value=None,
                visible=False,
                label="Select Sector"
            )

          mcap_dropdown = gr.Radio(
                choices=[
                    "Above $250B", "$150B–$250B", "$100B–$150B",
                    "$50B–$100B", "Below $50B"
                ],
                value=None,
                visible=False,
                label="Select Market Cap Range"
            )

        with gr.Column(scale=1):
            run_growth_btn = gr.Button("Run Growth Agent", elem_classes="agent-btn")
            burry_btn = gr.Button("Run Michael Burry Agent", elem_classes="agent-btn")
            damodaran_btn = gr.Button("Run Damodaran Agent", elem_classes="agent-btn")
            buffett_btn = gr.Button("Run Buffett Agent", elem_classes="agent-btn")


    growth_state = gr.State()
    burry_state = gr.State()
    damodaran_state = gr.State()
    buffett_state = gr.State()


    gr.Markdown("### Growth Agent Analysis")
    growth_output_table = gr.Dataframe(
        headers=["Ticker", "Company Name", "Sector", "Market Cap ($B)", "Growth Signal", "Score", "Reasoning"],
        interactive=False
    )
    growth_download = gr.File(label="Download Growth JSON")

    gr.Markdown("### Burry Agent Analysis")
    burry_table = gr.Dataframe(
        headers=["Ticker","Company Name", "Sector","Market Cap ($B)","Burry Signal","Score","Reasoning"],
        interactive=False
    )
    burry_download = gr.File(label="Download Burry JSON")

    gr.Markdown("### Damodaran Agent Analysis")
    damodaran_table = gr.Dataframe(
        headers=["Ticker","Company Name","Sector","Market Cap ($B)","Damodaran Signal","Score","Margin of Safety","Reasoning"],
        interactive=False
    )
    damodaran_download = gr.File(label="Download Damodaran JSON")


    gr.Markdown("### Buffett Agent Analysis")
    buffett_table = gr.Dataframe(
        headers=[
            "Ticker","Company Name","Sector","Market Cap ($B)","Buffett Signal","Score","Reasoning"],
        interactive=False
    )
    buffett_download = gr.File(label="Download Buffett JSON")


    gr.Markdown("### 🔥 Consensus Picks")
    consensus_btn = gr.Button("Show Consensus", elem_classes="agent-btn")
    consensus_table = gr.Dataframe(
        headers=[
            "Ticker","Company Name","Sector","Market Cap ($B)",
            "Bullish Count","Signal","Agents"
        ],
        interactive=False
    )


    # ---------------------------
    # Dynamic UI logic
    # ---------------------------
    def toggle_filters(mode):
        return (
           gr.update(
               visible=mode == "Sector",
               value=None          #to reset the value
           ),
           gr.update(
               visible=mode == "Market Cap",
               value=None          # to reset the value
           )
        )


    filter_mode.change(
        toggle_filters,
        inputs=filter_mode,
        outputs=[sector_dropdown, mcap_dropdown]
    )


    run_growth_btn.click(
         run_growth_agent,
         inputs=[filter_signal, filter_mode, sector_dropdown, mcap_dropdown],
         outputs=[growth_output_table, growth_download, growth_state]
    )


    burry_btn.click(
        run_michael_burry_agent,
        inputs=[filter_signal, filter_mode, sector_dropdown, mcap_dropdown],
        outputs=[burry_table, burry_download, burry_state]
    )


    damodaran_btn.click(
        run_damodaran_agent,
        inputs=[filter_signal, filter_mode, sector_dropdown, mcap_dropdown],
        outputs=[damodaran_table, damodaran_download, damodaran_state]
    )



    buffett_btn.click(
        run_buffett_agent,
        inputs=[filter_signal, filter_mode, sector_dropdown, mcap_dropdown],
        outputs=[buffett_table, buffett_download, buffett_state]
    )

    consensus_btn.click(
        run_consensus_agent,
        inputs=[filter_mode, sector_dropdown, mcap_dropdown],
        outputs=consensus_table
    )


demo.launch(share=True)

########################################
######################################

"""## **BACKTESTING**"""

!pip install backtesting yfinance

from backtesting import Backtest, Strategy
import yfinance as yf
import numpy as np

START_DATE = "2014-01-01"
END_DATE   = "2024-12-31"
SINGLE_TICKER = "NFLX"

#single ticker data
data = yf.download(SINGLE_TICKER, start=START_DATE, end=END_DATE)

data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
data.dropna(inplace=True)
data.columns = data.columns.droplevel(1)
data

def growth_signal_for_ticker(ticker):
    df, _, _ = run_growth_agent("All", "None", None, None)

    row = df[df["Ticker"] == ticker]
    if row.empty:
        return 0

    signal = row.iloc[0]["Growth Signal"]

    if signal == "Bullish":
        return 1
    elif signal == "Bearish":
        return -1
    else:
        return 0

def burry_signal_for_ticker(ticker):
    df, _, _ = run_michael_burry_agent("All", "None", None, None)

    row = df[df["Ticker"] == ticker]
    if row.empty:
        return 0

    signal = row.iloc[0]["Burry Signal"]

    if signal == "Bullish":
        return 1
    elif signal == "Bearish":
        return -1
    else:
        return 0

def damodaran_signal_for_ticker(ticker):
    df, _, _ = run_damodaran_agent("All", "None", None, None)

    row = df[df["Ticker"] == ticker]
    if row.empty:
        return 0

    signal = row.iloc[0]["Damodaran Signal"]

    if signal == "Bullish":
        return 1
    elif signal == "Bearish":
        return -1
    else:
        return 0

def buffett_signal_for_ticker(ticker):
    df, _, _ = run_buffett_agent("All", "None", None, None)

    row = df[df["Ticker"] == ticker]
    if row.empty:
        return 0

    signal = row.iloc[0]["Buffett Signal"]

    if signal == "Bullish":
        return 1 #1 = Bullish now
    elif signal == "Bearish":
        return -1 #
    else:
        return 0

def consensus_signal_for_ticker(ticker):
    consensus_df = run_consensus_agent("None", None, None)

    row = consensus_df[consensus_df["Ticker"] == ticker]
    if row.empty:
        return 0

    signal = row.iloc[0]["Signal"]

    if signal == "Long":
        return 1
    elif signal == "Short":
        return -1
    else:
        return 0

class GrowthStrategy(Strategy):

    def init(self):
        self.signal = growth_signal_for_ticker(TICKER)

    def next(self):

        if self.signal == 1:
            if not self.position:
                self.buy()

        elif self.signal == -1:
            if not self.position:
                self.sell()

        else:
            # Neutral → close any open positions
            if self.position:
                self.position.close()

class BurryStrategy(Strategy):

    def init(self):
        self.signal = burry_signal_for_ticker(TICKER)

    def next(self):

        if self.signal == 1:
            if not self.position:
                self.buy()

        elif self.signal == -1:
            if not self.position:
                self.sell()

        else:
            # Neutral → close any open positions
            if self.position:
                self.position.close()

class DamodaranStrategy(Strategy):

    def init(self):
        self.signal = damodaran_signal_for_ticker(TICKER)

    def next(self):

        if self.signal == 1:
            if not self.position:
                self.buy()

        elif self.signal == -1:
            if not self.position:
                self.sell()

        else:
            # Neutral → close any open positions
            if self.position:
                self.position.close()

class BuffettStrategy(Strategy):

    def init(self):
        self.signal = buffett_signal_for_ticker(TICKER)

    def next(self):

        if self.signal == 1:
            if not self.position:
                self.buy()

        elif self.signal == -1:
            if not self.position:
                self.sell()

        else:
            # Neutral → close any open positions
            if self.position:
                self.position.close()

class ConsensusStrategy(Strategy):

    def init(self):
        self.signal = consensus_signal_for_ticker(TICKER)

    def next(self):

        if self.signal == 1:
            if not self.position:
                self.buy()

        elif self.signal == -1:
            if not self.position:
                self.sell()

        else:
            # Neutral → close any open positions
            if self.position:
                self.position.close()

#single ticker first for seeing if code works

TICKER = SINGLE_TICKER
initialcash = 100_000
bt = Backtest(
    data,
    ConsensusStrategy,
    cash=initialcash,
    commission=0.002,
    exclusive_orders=True
)

stats = bt.run()
print(stats)
bt.plot()

#for multiple tickers

data_g = yf.download(tickers_g, start=START_DATE, end=END_DATE)["Close"]
data_g = data_g.dropna(how="all")
data_b = yf.download(tickers_b, start=START_DATE, end=END_DATE)["Close"]
data_b = data_b.dropna(how="all")
data_d = yf.download(tickers_d, start=START_DATE, end=END_DATE)["Close"]
data_d = data_d.dropna(how="all")
data_ff = yf.download(tickers_ff, start=START_DATE, end=END_DATE)["Close"]
data_ff = data_ff.dropna(how="all")
data_c = yf.download(tickers_c, start=START_DATE, end=END_DATE)["Close"]
data_c = data_c.dropna(how="all")

price_data_g = yf.download(tickers_g, start=START_DATE, end=END_DATE)["Close"]
price_data_g = price_data_g.dropna(how="all")

price_data_b = yf.download(tickers_b, start=START_DATE, end=END_DATE)["Close"]
price_data_b = price_data_b.dropna(how="all")

price_data_d = yf.download(tickers_d, start=START_DATE, end=END_DATE)["Close"]
price_data_d = price_data_d.dropna(how="all")

price_data_ff = yf.download(tickers_ff, start=START_DATE, end=END_DATE)["Close"]
price_data_ff = price_data_ff.dropna(how="all")

price_data_c = yf.download(tickers_c, start=START_DATE, end=END_DATE)["Close"]
price_data_c = price_data_c.dropna(how="all")

from tqdm.notebook import tqdm

signal_map_growth = {}

for ticker in tqdm(tickers_g, desc="Progress"):
    signal_map_growth[ticker] = growth_signal_for_ticker(ticker)

signal_map_burry = {}

for ticker in tqdm(tickers_b, desc="Progress"):
    signal_map_burry[ticker] = burry_signal_for_ticker(ticker)

signal_map_damodaran = {}

for ticker in tqdm(tickers_d, desc="Progress"):
    signal_map_damodaran[ticker] = damodaran_signal_for_ticker(ticker)

signal_map_buffett = {}

for ticker in tqdm(tickers_ff, desc="Progress"):
    signal_map_buffett[ticker] = buffett_signal_for_ticker(ticker)

signal_map_consensus = {}

for ticker in tqdm(tickers_c, desc="Progress"):
    signal_map_consensus[ticker] = consensus_signal_for_ticker(ticker)

# function for agent results

def agent_results(agent_tickers, price_data, signal_map):
  tickers = agent_tickers
  INITIAL_CASH = 100_000
  cash = INITIAL_CASH
  positions = {ticker: 0 for ticker in tickers}
  portfolio_value = []
  trade_count = 0 #to count no. of trades that took place
  for date in tqdm(price_data.index, desc="Backtesting progress"):

    daily_prices = price_data.loc[date]

    for ticker in tickers:

        price = daily_prices[ticker]
        if np.isnan(price):
            continue

        ma = price_data[ticker].rolling(100).mean().loc[date]

        if signal_map[ticker] == 1 and daily_prices[ticker] > ma:
          signal = 1
        else:
          signal = 0

        # BUY
        if signal == 1 and positions[ticker] == 0:
            allocation = cash / len(tickers)
            shares = allocation / price

            if cash >= allocation:
                positions[ticker] = shares
                cash -= allocation
                trade_count += 1

        # SELL
        elif signal != 1 and positions[ticker] > 0:
            cash += positions[ticker] * price
            positions[ticker] = 0
            trade_count += 1

    # Calculate total portfolio value
    total_equity = cash
    for ticker in tickers:
        if positions[ticker] > 0:
            total_equity += positions[ticker] * daily_prices[ticker]

    portfolio_value.append(total_equity)

  equity_curve = pd.Series(portfolio_value, index=price_data.index)
  equity_curve_plot = equity_curve.plot(title="Portfolio Equity Curve")

  final_value = equity_curve.iloc[-1]
  total_return = (final_value - INITIAL_CASH) / INITIAL_CASH
  print("Final Value:", round(final_value, 2))
  print("Total Return %:", round(total_return * 100, 2))
  print("Total Trades:", trade_count)
  return equity_curve_plot

agent_results(tickers_g, price_data_g, signal_map_growth)

agent_results(tickers_b, price_data_b, signal_map_burry)

agent_results(tickers_d, price_data_d, signal_map_damodaran)

agent_results(tickers_ff, price_data_ff, signal_map_buffett)

agent_results(tickers_c, price_data_c, signal_map_consensus)

"""**BEST AGENT/STRATEGY IS GROWTH**

Backtesting results of GROWTH agent/strategy:
Final Value: 148350.07
Total Return %: 48.35
Total Trades: 1126
"""

#######################################################################
####################################################################

# FREEZE UNIVERSE AS OF DEC 31, 2024
TRAIN_END = "2024-12-31"

newdf, _, _ = run_growth_agent("All", "None", None, None)

ticker_universe = newdf["Ticker"].tolist()

print("Frozen Ticker Universe (Dec 31, 2024):")
print(ticker_universe)

"""### **FORWARD TESTING**"""

tickers8 = ticker_universe
INITIAL_CAPITAL = 100_000

signal_map_ft = {}

for ticker in tqdm(tickers8, desc="Progress"):
    signal_map_ft[ticker] = growth_signal_for_ticker(ticker)

def forward_results(agent_tickers, start_date, end_date, signal_map):

    price_data = yf.download(agent_tickers, start=start_date, end=end_date)["Close"]
    price_data = price_data.dropna(how="all")

    return agent_results(agent_tickers, price_data, signal_map)

forward_results(
    tickers8,
    "2025-04-01",
    "2026-02-20",
    signal_map_ft
)

"""Final Value: 105692.03
Total Return %: 5.69
Total Trades: 77
"""

#comparing with s&p
start = "2025-04-01"
end = "2026-02-20"
sp = yf.download("^GSPC", start=start, end=end)
sp_return = (sp["Close"].iloc[-1] - sp["Close"].iloc[0]) / sp["Close"].iloc[0] * 100
print("S&P Return %:", round(sp_return, 2))

#######################################################################
####################################################################

# Commented out IPython magic to ensure Python compatibility.
#incase you want to import talib oackage later
!wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
!tar -xzf ta-lib-0.4.0-src.tar.gz
# %cd ta-lib
!./configure --prefix=/usr
!make
!make install
# %cd ..

!pip install TA-Lib

"""# GARCH"""

#GARCH model for modeling stocks' volatility

!pip install arch
from arch import arch_model

# GARCH done only for NEM, FCX, ECL, APD, CRH for demonstration purposes

data1 = bt.get('NEM', start='2023-01-01', end='2025-03-31')
data2 = bt.get('FCX', start='2023-01-01', end='2025-03-31')
data3 = bt.get('ECL', start='2023-01-01', end='2025-03-31')
data4 = bt.get('APD', start='2023-01-01', end='2025-03-31')
data5 = bt.get('CRH', start='2023-01-01', end='2025-03-31')

data1 = data1.resample('D').asfreq()
data2 = data2.resample('D').asfreq()
data3 = data3.resample('D').asfreq()
data4 = data4.resample('D').asfreq()
data5 = data5.resample('D').asfreq()

data1 = data1.resample('M').mean()
data2 = data2.resample('M').mean()
data3 = data3.resample('M').mean()
data4 = data4.resample('M').mean()
data5 = data5.resample('M').mean()

data1

data1['return'] =  100 * (data1['acgl'].pct_change())
data2['return'] =  100 * (data2['aapl'].pct_change())
data3['return'] =  100 * (data3['abbv'].pct_change())
data4['return'] =  100 * (data4['aiz'].pct_change())
data5['return'] =  100 * (data5['acn'].pct_change())

# GARCH (1,1) model assumptions
basic_gm = arch_model(data1['return'].dropna(), p = 1, q = 1, mean = 'constant', vol = 'GARCH', dist = 'normal')
gm_result = basic_gm.fit(update_freq = 4)

basic_gm2 = arch_model(data2['return'].dropna(), p = 1, q = 1, mean = 'constant', vol = 'GARCH', dist = 'normal')
gm_result2 = basic_gm2.fit(update_freq = 4)

basic_gm3 = arch_model(data3['return'].dropna(), p = 1, q = 1, mean = 'constant', vol = 'GARCH', dist = 'normal')
gm_result3 = basic_gm3.fit(update_freq = 4)

basic_gm4 = arch_model(data4['return'].dropna(), p = 1, q = 1, mean = 'constant', vol = 'GARCH', dist = 'normal')
gm_result4 = basic_gm4.fit(update_freq = 4)

basic_gm5 = arch_model(data5['return'].dropna(), p = 1, q = 1, mean = 'constant', vol = 'GARCH', dist = 'normal')
gm_result5 = basic_gm5.fit(update_freq = 4)

# Display model fitting summary
print(gm_result.summary())
gm_result.plot()
plt.show()
# 5-period ahead forecast of the volatility
gm_forecast = gm_result.forecast(horizon = 5)
print(gm_forecast.variance[-1:])

# Display model fitting summary
print(gm_result2.summary())
gm_result2.plot()
plt.show()
# 5-period ahead forecast of the volatility
gm_forecast2 = gm_result2.forecast(horizon = 5)
print(gm_forecast2.variance[-1:])

# Display model fitting summary
print(gm_result3.summary())
gm_result3.plot()
plt.show()
# 5-period ahead forecast of the volatility
gm_forecast3 = gm_result3.forecast(horizon = 5)
print(gm_forecast3.variance[-1:])

# Display model fitting summary
print(gm_result4.summary())
gm_result4.plot()
plt.show()
# 5-period ahead forecast of the volatility
gm_forecast4 = gm_result4.forecast(horizon = 5)
print(gm_forecast4.variance[-1:])

# Display model fitting summary
print(gm_result5.summary())
gm_result5.plot()
plt.show()
# 5-period ahead forecast of the volatility
gm_forecast5 = gm_result5.forecast(horizon = 5)
print(gm_forecast5.variance[-1:])
