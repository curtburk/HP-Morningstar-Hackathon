#!/usr/bin/env python3
"""
HP + Morningstar AI Hackathon — Data Preparation Script
========================================================

Run this on any internet-connected machine BEFORE the hackathon.
It pulls real financial data from free APIs and generates all the
sample files needed for the ZGX Nano.

Output: ./hackathon_data/ directory containing:
  - portfolios/           → 5 sample portfolio JSON files
  - filings/              → 10-K full-text files (raw .txt — chunking left to participants)
  - compliance/           → restricted_list.csv, compliance_rules.yaml
  - benchmark/            → benchmark_questions.json
  - metadata/             → sector_map.json, data_manifest.json

Requirements:
  pip install yfinance edgartools pyyaml

Usage:
  python prep_hackathon_data.py

After running, copy the entire ./hackathon_data/ directory to the ZGX Nano.

NOTE: edgartools requires you to set an identity (email) for SEC rate
limiting compliance. Set the EDGAR_IDENTITY env var or it will use
a placeholder. SEC asks that you use a real email so they can contact
you if your requests cause issues — be a good citizen.
"""

import json
import csv
import os
import sys
import random
import datetime
import traceback
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────
OUTPUT_DIR = Path("./hackathon_data")
EDGAR_IDENTITY = os.environ.get("EDGAR_IDENTITY", "hackathon-prep@example.com")

# Companies to pull filings from (large, well-known, public filings are rich)
FILING_COMPANIES = ["AAPL", "MSFT", "JPM", "JNJ", "XOM", "PG", "UNH", "MA", "NVDA", "KO"]

# Tickers to use for building sample portfolios
PORTFOLIO_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "JPM", "V", "MA", "PG", "HD", "XOM", "CVX", "MRK",
    "ABBV", "PFE", "KO", "PEP", "COST", "WMT", "MCD", "DIS", "NFLX",
    "CRM", "ADBE", "INTC", "AMD", "QCOM", "TXN", "NEE", "DUK", "SO",
    "LMT", "RTX", "BA", "GE", "CAT", "MMM", "GS", "MS", "BLK", "SCHW",
    "USB", "WFC", "C", "AXP"
]

# ── Helpers ────────────────────────────────────────────────────────
def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)

def save_json(data, filepath):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  ✓ Saved {filepath}")

def save_text(text, filepath):
    with open(filepath, "w") as f:
        f.write(text)
    print(f"  ✓ Saved {filepath}")

def save_csv(rows, filepath, fieldnames):
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ Saved {filepath}")


# ── Step 1: Pull Sector/Industry Data via yfinance ─────────────────
def pull_ticker_metadata():
    """Pull sector, industry, and company name for each ticker."""
    import yfinance as yf

    print("\n📊 Step 1: Pulling ticker metadata from Yahoo Finance...")
    metadata = {}
    failed = []

    for ticker in PORTFOLIO_UNIVERSE:
        try:
            info = yf.Ticker(ticker).info
            metadata[ticker] = {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName", ticker),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "market_cap": info.get("marketCap", 0),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
            }
            print(f"  ✓ {ticker}: {metadata[ticker]['name']} ({metadata[ticker]['sector']})")
        except Exception as e:
            print(f"  ✗ {ticker}: {e}")
            failed.append(ticker)
            # Provide a fallback so portfolio generation still works
            metadata[ticker] = {
                "ticker": ticker,
                "name": ticker,
                "sector": "Unknown",
                "industry": "Unknown",
                "market_cap": 0,
                "current_price": 100.0,
            }

    if failed:
        print(f"\n  ⚠ {len(failed)} tickers failed — using fallback data for: {', '.join(failed)}")

    save_json(metadata, OUTPUT_DIR / "metadata" / "sector_map.json")
    return metadata


# ── Step 2: Generate Sample Portfolios ─────────────────────────────
def generate_portfolios(metadata):
    """
    Generate 5 realistic sample portfolios with different characteristics.
    Each portfolio is designed to trigger interesting compliance scenarios.
    """
    print("\n📁 Step 2: Generating sample portfolios...")

    portfolio_configs = [
        {
            "name": "Alpha Growth Fund",
            "description": "Aggressive growth portfolio with heavy tech concentration",
            "style": "growth",
            "bias_sector": "Technology",
            "bias_weight": 0.45,  # Intentionally over 30% to trigger compliance flag
            "num_holdings": 25,
        },
        {
            "name": "Beta Value Fund",
            "description": "Diversified value portfolio across sectors",
            "style": "value",
            "bias_sector": None,
            "bias_weight": 0,
            "num_holdings": 30,
        },
        {
            "name": "Gamma Income Fund",
            "description": "Income-focused portfolio with healthcare and utilities",
            "style": "income",
            "bias_sector": "Healthcare",
            "bias_weight": 0.35,  # Also over 30% for compliance testing
            "num_holdings": 20,
        },
        {
            "name": "Delta Balanced Fund",
            "description": "Balanced allocation across growth and value",
            "style": "balanced",
            "bias_sector": None,
            "bias_weight": 0,
            "num_holdings": 35,
        },
        {
            "name": "Epsilon Concentrated Fund",
            "description": "High-conviction concentrated portfolio",
            "style": "concentrated",
            "bias_sector": "Financial Services",
            "bias_weight": 0.40,
            "num_holdings": 15,
        },
    ]

    all_tickers = list(metadata.keys())
    portfolios = []

    for config in portfolio_configs:
        random.seed(hash(config["name"]))  # Reproducible randomness
        holdings = []

        # Select tickers
        if config["bias_sector"]:
            # Pick biased tickers from the target sector
            sector_tickers = [t for t in all_tickers if metadata[t]["sector"] == config["bias_sector"]]
            other_tickers = [t for t in all_tickers if metadata[t]["sector"] != config["bias_sector"]]

            n_biased = min(len(sector_tickers), config["num_holdings"] // 2)
            n_other = config["num_holdings"] - n_biased

            selected = random.sample(sector_tickers, n_biased) + random.sample(other_tickers, min(n_other, len(other_tickers)))
        else:
            selected = random.sample(all_tickers, min(config["num_holdings"], len(all_tickers)))

        # Assign weights
        raw_weights = [random.uniform(0.5, 5.0) for _ in selected]

        # If biased, inflate the sector weights
        if config["bias_sector"] and config["bias_weight"] > 0:
            for i, ticker in enumerate(selected):
                if metadata[ticker]["sector"] == config["bias_sector"]:
                    raw_weights[i] *= 3.0  # Inflate sector-biased holdings

        total = sum(raw_weights)
        weights = [w / total for w in raw_weights]

        for ticker, weight in zip(selected, weights):
            price = metadata[ticker]["current_price"] or 100.0
            market_value = round(weight * 10_000_000, 2)  # $10M portfolio
            shares = round(market_value / price, 2) if price > 0 else 0

            holdings.append({
                "ticker": ticker,
                "company_name": metadata[ticker]["name"],
                "sector": metadata[ticker]["sector"],
                "industry": metadata[ticker]["industry"],
                "weight": round(weight, 6),
                "shares": shares,
                "market_value": market_value,
                "price": round(price, 2),
            })

        # Sort by weight descending
        holdings.sort(key=lambda h: h["weight"], reverse=True)

        portfolio = {
            "portfolio_name": config["name"],
            "description": config["description"],
            "style": config["style"],
            "as_of_date": datetime.date.today().isoformat(),
            "total_market_value": sum(h["market_value"] for h in holdings),
            "num_holdings": len(holdings),
            "holdings": holdings,
        }

        filename = config["name"].lower().replace(" ", "_") + ".json"
        save_json(portfolio, OUTPUT_DIR / "portfolios" / filename)
        portfolios.append(portfolio)

    return portfolios


# ── Step 3: Pull SEC Filing Full Text via edgartools ───────────────
def pull_filing_excerpts():
    """
    Pull 10-K filing full text for RAG ingestion.
    Saves raw text as .txt files — chunking is left to the participants
    so they can experiment with chunk size, overlap, and splitting strategy.
    """
    print("\n📄 Step 3: Pulling SEC 10-K filings (full text) via edgartools...")

    try:
        from edgar import Company, set_identity
        set_identity(EDGAR_IDENTITY)
    except ImportError:
        print("  ⚠ edgartools not installed. Generating synthetic filing text instead.")
        return generate_synthetic_filings()

    filings_dir = OUTPUT_DIR / "filings"
    filing_manifest = []

    for ticker in FILING_COMPANIES:
        try:
            print(f"  Fetching 10-K for {ticker}...")
            company = Company(ticker)
            filings = company.get_filings(form="10-K")

            if not filings or len(filings) == 0:
                print(f"    ✗ No 10-K filings found for {ticker}")
                continue

            filing = filings[0]  # Most recent
            print(f"    Found: {filing.company} filed {filing.filing_date}")

            # Try to get markdown (preserves structure), fall back to plain text
            content = None
            content_format = None
            try:
                content = filing.markdown()
                content_format = "markdown"
            except Exception:
                try:
                    content = filing.text()
                    content_format = "text"
                except Exception as e:
                    print(f"    ✗ Could not extract text for {ticker}: {e}")
                    continue

            if not content or len(content) < 500:
                print(f"    ✗ Content too short for {ticker}, skipping")
                continue

            # Save the raw full text as a .txt file
            txt_filename = f"{ticker.lower()}_10k.txt"
            save_text(content, filings_dir / txt_filename)

            char_count = len(content)
            print(f"    {char_count:,} characters saved ({content_format})")

            filing_manifest.append({
                "ticker": ticker,
                "company": str(filing.company),
                "file": txt_filename,
                "filing_date": str(filing.filing_date),
                "format": content_format,
                "characters": char_count,
            })

        except Exception as e:
            print(f"    ✗ Error processing {ticker}: {e}")
            traceback.print_exc()

    if not filing_manifest:
        print("  ⚠ No filings were pulled successfully. Generating synthetic filings as fallback.")
        return generate_synthetic_filings()

    save_json(filing_manifest, OUTPUT_DIR / "metadata" / "filing_manifest.json")
    print(f"\n  ✓ Pulled {len(filing_manifest)} filing(s) successfully")
    return filing_manifest


def generate_synthetic_filings():
    """Fallback: generate realistic-looking synthetic filing full text."""
    print("\n📄 Step 3 (fallback): Generating synthetic filing text...")

    filings_dir = OUTPUT_DIR / "filings"
    manifest = []

    synthetic_data = [
        {
            "ticker": "ACME",
            "company": "Acme Technology Corp",
            "text": """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549
FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended September 30, 2025
ACME TECHNOLOGY CORP

ITEM 1. BUSINESS

Acme Technology Corp reported total revenues of $42.3 billion for fiscal year 2025, representing a 12% increase over the prior year. The growth was primarily driven by strong demand in our cloud computing and enterprise software segments, which together accounted for 68% of total revenue. Our cloud services segment saw particularly robust growth of 24% year-over-year, reflecting continued enterprise adoption of our platform solutions.

We operate in three reportable segments: Cloud Services ($18.2B revenue), Enterprise Software ($10.5B revenue), and Hardware Solutions ($13.6B revenue). Our cloud platform serves over 42,000 enterprise customers across 85 countries, with a net retention rate of 127% for the fiscal year.

ITEM 1A. RISK FACTORS

Our business is subject to numerous risks and uncertainties. Competition in the technology sector remains intense, with both established players and emerging startups competing for market share. Changes in customer spending patterns, particularly among enterprise clients, could materially impact our revenue projections. Additionally, evolving data privacy regulations across jurisdictions present compliance challenges that require ongoing investment.

Cybersecurity threats continue to increase in sophistication and frequency. A significant breach of our systems or our customers' data could result in material financial losses, regulatory penalties, and reputational damage. We invest approximately $1.2 billion annually in security infrastructure and employ over 3,000 security professionals globally.

Macroeconomic conditions, including inflation, interest rate fluctuations, and geopolitical tensions, could adversely affect customer spending on technology solutions. Currency exchange rate fluctuations also impact our reported results, as approximately 45% of our revenue is generated outside the United States.

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

We maintain a diversified investment portfolio with a total fair value of $18.7 billion as of September 30, 2025. Our portfolio consists primarily of U.S. government securities ($8.2B), corporate debt securities ($6.1B), and equity investments ($4.4B). The weighted average maturity of our fixed-income holdings is approximately 3.2 years. During fiscal year 2025, we recognized net unrealized gains of $1.2 billion on our equity portfolio.

Capital expenditures totaled $7.8 billion for the fiscal year, primarily directed toward data center expansion ($4.2B), research and development facilities ($1.9B), and equipment upgrades ($1.7B). We expect capital expenditure levels to remain elevated in fiscal year 2026 as we continue investing in AI infrastructure to support growing computational demands from our customers.

Operating cash flow was $16.4 billion, an increase of 15% from the prior year. Free cash flow was $8.6 billion after capital expenditures. We returned $6.2 billion to shareholders through dividends ($2.8B) and share repurchases ($3.4B) during the fiscal year.

Our effective tax rate for fiscal year 2025 was 18.3%, compared to 17.9% in the prior year. The increase was primarily attributable to changes in the geographic mix of earnings and the implementation of the OECD Pillar Two global minimum tax framework in several jurisdictions where we operate. We maintain tax reserves of approximately $3.4 billion for uncertain tax positions across multiple jurisdictions.

ITEM 8. FINANCIAL STATEMENTS

Revenue by geography: United States $23.3B (55%), Europe $10.6B (25%), Asia-Pacific $5.9B (14%), Rest of World $2.5B (6%). Total headcount was approximately 148,000 employees as of September 30, 2025, an increase of 8% from the prior year, primarily in engineering and cloud operations roles.""",
        },
        {
            "ticker": "GLOBFIN",
            "company": "Global Financial Holdings Inc",
            "text": """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549
FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended December 31, 2025
GLOBAL FINANCIAL HOLDINGS INC

ITEM 1. BUSINESS

Global Financial Holdings is a diversified financial services company providing banking, wealth management, investment banking, and asset management services to consumers, businesses, and institutional clients worldwide. We operate through four reportable segments: Consumer Banking, Commercial Banking, Wealth Management, and Investment Banking & Markets.

Global Financial Holdings reported net interest income of $28.6 billion for the twelve months ended December 31, 2025, an increase of 8% compared to the prior year period. The improvement reflects higher average interest-earning asset balances and an expanded net interest margin of 2.84%, up from 2.71% in the prior year. Total loans and leases outstanding were $892 billion at year-end.

ITEM 1A. RISK FACTORS

Credit risk is inherent in our lending activities. An economic downturn, rising unemployment, or disruptions in specific sectors such as commercial real estate could lead to increased loan defaults and higher credit losses. We manage credit risk through diversified lending practices, rigorous underwriting standards, and ongoing portfolio monitoring.

Regulatory and compliance risk remains a significant concern. We are subject to extensive regulation by federal and state banking agencies, including the Federal Reserve, OCC, FDIC, and CFPB. Changes in regulatory requirements, enforcement actions, or failures in our compliance infrastructure could result in material fines, restrictions on our business activities, or reputational harm.

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS

Credit quality metrics remained stable during fiscal year 2025. Net charge-offs were $4.8 billion, or 0.54% of average loans, compared to 0.51% in the prior year. The allowance for credit losses was $14.2 billion, representing 1.59% of total loans. We believe our reserves are adequate given the current economic outlook, though we continue to monitor commercial real estate and consumer credit portfolios closely.

Our wealth management division generated $12.4 billion in revenue, driven by higher asset-based fees reflecting favorable market conditions and net client flows of $78 billion. Total client assets under management reached $3.8 trillion. Our financial advisors maintained an average production rate of $1.2 million per advisor, a 9% improvement over the prior year.

Regulatory capital ratios remained well above minimum requirements. Our Common Equity Tier 1 ratio was 12.8% as of December 31, 2025, compared to the regulatory minimum of 4.5% plus applicable buffers. Total capital ratio was 16.2%. During the year, we returned $18 billion to shareholders through dividends ($8.4B) and share repurchases ($9.6B).

Non-interest expense was $48.2 billion, reflecting continued investment in technology transformation ($4.8B) and regulatory compliance infrastructure ($2.1B). Our efficiency ratio improved to 58.3% from 60.1% in the prior year, driven by revenue growth and ongoing operational efficiency initiatives. We employed approximately 215,000 people across 35 countries at year-end.""",
        },
        {
            "ticker": "MEDPHR",
            "company": "MedPharma International Ltd",
            "text": """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549
FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended December 31, 2025
MEDPHARMA INTERNATIONAL LTD

ITEM 1. BUSINESS

MedPharma International is a global healthcare company engaged in the research, development, manufacture, and marketing of pharmaceutical products and medical devices. We are committed to addressing unmet medical needs through innovative therapies across immunology, oncology, neuroscience, cardiovascular, and infectious disease.

MedPharma International reported total revenues of $56.1 billion for fiscal year 2025, with pharmaceutical segment revenues of $41.8 billion and medical devices segment revenues of $14.3 billion. Our pharmaceutical portfolio includes 12 products with annual sales exceeding $1 billion each, led by our immunology franchise which generated $15.2 billion in combined revenues.

ITEM 1A. RISK FACTORS

Our business depends on the successful development and commercialization of new products. Drug development is inherently uncertain, and clinical trials may fail to demonstrate adequate safety or efficacy. We cannot guarantee that any of our pipeline candidates will receive regulatory approval or achieve commercial success.

We face significant patent expiration risk. Products representing approximately $8.5 billion in current annual revenue face patent expirations over the next three fiscal years. Biosimilar and generic competition following patent expirations typically results in rapid and substantial revenue declines for affected products.

Pricing and reimbursement pressures from government healthcare programs, private insurers, and pharmacy benefit managers continue to intensify. Legislative or regulatory changes that impose price controls or mandatory rebates could materially impact our revenue and profitability.

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS

Research and development expenses were $11.3 billion, representing 20.1% of total revenues. Our pipeline includes 85 compounds in clinical development, with 15 in Phase III or registration stage. Key regulatory milestones expected in fiscal year 2026 include FDA decisions on our novel oncology combination therapy (PDUFA date: March 2026) and our first-in-class cardiovascular agent (PDUFA date: July 2026).

We recorded goodwill impairment charges of $2.8 billion related to our 2023 acquisition of BioGenesis Therapeutics, reflecting revised commercial projections for the acquired gene therapy platform. Despite this non-cash charge, we believe the long-term strategic value of the gene therapy technology remains significant, with three programs advancing toward clinical proof-of-concept.

Geographic revenue distribution: United States 52%, Europe 24%, Asia-Pacific 15%, Rest of World 9%. Our biosimilar defense strategy includes lifecycle management programs, authorized generics, and next-generation formulations designed to retain significant market share post-exclusivity.

ITEM 8. LEGAL PROCEEDINGS

The Company is subject to various pending lawsuits and regulatory proceedings. We have established litigation reserves of $4.2 billion as of December 31, 2025, primarily related to product liability claims ($2.8B), antitrust matters ($0.9B), and pricing litigation ($0.5B). While we believe these reserves are adequate, actual outcomes may differ materially from current estimates.""",
        },
    ]

    for company_data in synthetic_data:
        txt_filename = f"{company_data['ticker'].lower()}_10k.txt"
        save_text(company_data["text"].strip(), filings_dir / txt_filename)
        manifest.append({
            "ticker": company_data["ticker"],
            "company": company_data["company"],
            "file": txt_filename,
            "filing_date": "2025-11-15",
            "format": "text",
            "characters": len(company_data["text"]),
            "synthetic": True,
        })

    save_json(manifest, OUTPUT_DIR / "metadata" / "filing_manifest.json")
    return manifest


# ── Step 4: Generate Compliance Data ───────────────────────────────
def generate_compliance_data(metadata):
    """Generate the restricted securities list and compliance rules."""
    print("\n🔒 Step 4: Generating compliance data...")

    # ── Restricted Securities List ──
    # Pick a subset of real tickers plus some synthetic ones
    real_restricted = random.sample(PORTFOLIO_UNIVERSE, 8)
    synthetic_restricted = ["XYZQ", "BADCO", "FLAGD", "NOGO", "WATCHIT", "HALTD", "SUSP"]

    reasons = [
        "Material non-public information — pending merger announcement",
        "Insider trading investigation — SEC enforcement action pending",
        "Trading window closed — quarterly earnings blackout period",
        "Regulatory hold — OFAC sanctions review",
        "Research restriction — analyst coverage initiation pending",
        "Compliance hold — related party transaction review",
        "Legal hold — pending litigation disclosure",
        "Risk committee restriction — concentration limit breach",
    ]

    restricted_rows = []
    for i, ticker in enumerate(real_restricted + synthetic_restricted):
        name = metadata.get(ticker, {}).get("name", f"{ticker} Corp")
        restricted_rows.append({
            "ticker": ticker,
            "company_name": name,
            "restriction_type": random.choice(["hard_block", "soft_flag", "watch_list"]),
            "reason": reasons[i % len(reasons)],
            "effective_date": (datetime.date.today() - datetime.timedelta(days=random.randint(1, 90))).isoformat(),
            "expiry_date": (datetime.date.today() + datetime.timedelta(days=random.randint(30, 180))).isoformat(),
            "added_by": random.choice(["Compliance Team", "Legal Dept", "Risk Committee", "Chief Compliance Officer"]),
        })

    save_csv(
        restricted_rows,
        OUTPUT_DIR / "compliance" / "restricted_list.csv",
        fieldnames=["ticker", "company_name", "restriction_type", "reason", "effective_date", "expiry_date", "added_by"],
    )

    # ── Compliance Policy Rules (YAML) ──
    rules_yaml = """# Compliance Policy Rules
# Used by the agent to check portfolio compliance programmatically

concentration_limits:
  single_sector_max: 0.30          # No single sector above 30%
  single_holding_max: 0.05         # No single holding above 5%
  top_5_holdings_max: 0.35         # Top 5 holdings combined cannot exceed 35%
  single_issuer_debt_max: 0.10     # No single issuer debt above 10% (fixed income)

restricted_securities:
  source: "restricted_list.csv"
  action_on_match: "flag_and_report"
  hard_block_action: "reject_trade"
  soft_flag_action: "require_approval"
  watch_list_action: "log_and_monitor"

risk_metrics:
  herfindahl_threshold: 0.15       # HHI above 0.15 = concentrated
  max_tracking_error: 0.05         # Max 5% tracking error vs benchmark
  min_holdings: 15                 # Minimum 15 holdings required
  max_cash_allocation: 0.10        # Max 10% in cash

reporting:
  format: "markdown"
  include_timestamps: true
  include_data_sources: true
  compliance_officer_email: "compliance@example.com"
  escalation_threshold: "hard_block"

audit_trail:
  log_all_tool_calls: true
  log_agent_reasoning: true
  retention_days: 365
  storage: "local_json"
"""
    save_text(rules_yaml, OUTPUT_DIR / "compliance" / "compliance_rules.yaml")

    return restricted_rows


# ── Step 5: Generate Benchmark Questions ───────────────────────────
def generate_benchmark_questions(portfolios, restricted_rows):
    """
    Generate benchmark questions with known answers that the agent
    should be able to handle. These are used in Sprint 3 for evaluation.
    """
    print("\n📝 Step 5: Generating benchmark questions...")

    # Get some real data from the portfolios for ground-truth answers
    alpha = next((p for p in portfolios if "Alpha" in p["portfolio_name"]), portfolios[0])
    beta = next((p for p in portfolios if "Beta" in p["portfolio_name"]), portfolios[1] if len(portfolios) > 1 else portfolios[0])

    # Calculate actual sector exposure for Alpha
    sector_weights = {}
    for h in alpha["holdings"]:
        sector = h["sector"]
        sector_weights[sector] = sector_weights.get(sector, 0) + h["weight"]

    top_sector = max(sector_weights, key=sector_weights.get)
    top_sector_weight = sector_weights[top_sector]

    # Get restricted tickers that appear in Alpha
    alpha_tickers = {h["ticker"] for h in alpha["holdings"]}
    restricted_tickers = {r["ticker"] for r in restricted_rows}
    flagged_in_alpha = alpha_tickers & restricted_tickers

    questions = [
        {
            "id": "BQ-001",
            "question": f"What is the {top_sector} sector exposure in the {alpha['portfolio_name']}? Does it exceed the 30% concentration limit?",
            "expected_tools": ["lookup_portfolio", "get_sector_exposure"],
            "expected_answer_contains": [top_sector, str(round(top_sector_weight * 100, 1))],
            "compliance_violation": top_sector_weight > 0.30,
            "difficulty": "easy",
        },
        {
            "id": "BQ-002",
            "question": f"Check whether any holdings in the {alpha['portfolio_name']} appear on the restricted securities list.",
            "expected_tools": ["lookup_portfolio", "check_restricted_list"],
            "expected_answer_contains": list(flagged_in_alpha) if flagged_in_alpha else ["no restricted"],
            "compliance_violation": len(flagged_in_alpha) > 0,
            "difficulty": "easy",
        },
        {
            "id": "BQ-003",
            "question": f"Calculate the Herfindahl concentration index for the {alpha['portfolio_name']} and determine if it exceeds the 0.15 threshold.",
            "expected_tools": ["lookup_portfolio", "calculate_risk_metric"],
            "expected_answer_contains": ["herfindahl"],
            "compliance_violation": None,  # Depends on calculation
            "difficulty": "medium",
        },
        {
            "id": "BQ-004",
            "question": f"Does the {alpha['portfolio_name']} have any single holding exceeding the 5% weight limit? If so, which ones?",
            "expected_tools": ["lookup_portfolio"],
            "expected_answer_contains": [h["ticker"] for h in alpha["holdings"] if h["weight"] > 0.05],
            "compliance_violation": any(h["weight"] > 0.05 for h in alpha["holdings"]),
            "difficulty": "easy",
        },
        {
            "id": "BQ-005",
            "question": f"Run a full compliance review of the {alpha['portfolio_name']}: check sector concentration limits, single-holding limits, restricted list violations, and concentration index. Produce a compliance memo.",
            "expected_tools": ["lookup_portfolio", "get_sector_exposure", "check_restricted_list", "calculate_risk_metric", "generate_memo"],
            "expected_answer_contains": ["compliance", "memo"],
            "compliance_violation": True,
            "difficulty": "hard",
        },
        {
            "id": "BQ-006",
            "question": f"Compare the sector diversification of the {alpha['portfolio_name']} versus the {beta['portfolio_name']}. Which is better diversified?",
            "expected_tools": ["lookup_portfolio", "get_sector_exposure", "calculate_risk_metric"],
            "expected_answer_contains": [alpha["portfolio_name"], beta["portfolio_name"]],
            "compliance_violation": None,
            "difficulty": "medium",
        },
        {
            "id": "BQ-007",
            "question": "Search the SEC filings for any discussion of revenue guidance or forward-looking revenue projections.",
            "expected_tools": ["search_filings"],
            "expected_answer_contains": ["revenue"],
            "compliance_violation": None,
            "difficulty": "easy",
        },
        {
            "id": "BQ-008",
            "question": "Find any risk factors related to regulatory compliance or data privacy mentioned in the available SEC filings.",
            "expected_tools": ["search_filings"],
            "expected_answer_contains": ["risk", "regulatory"],
            "compliance_violation": None,
            "difficulty": "easy",
        },
        {
            "id": "BQ-009",
            "question": f"I want to add 500 shares of {list(restricted_tickers)[0]} to the {alpha['portfolio_name']}. Is this trade allowed?",
            "expected_tools": ["check_restricted_list"],
            "expected_answer_contains": ["restricted", "blocked", "not allowed"],
            "compliance_violation": True,
            "difficulty": "medium",
        },
        {
            "id": "BQ-010",
            "question": f"Generate a comprehensive compliance report for all five portfolios. Flag any violations across concentration limits, restricted securities, and minimum holding requirements.",
            "expected_tools": ["lookup_portfolio", "get_sector_exposure", "check_restricted_list", "calculate_risk_metric", "generate_memo"],
            "expected_answer_contains": ["compliance", "report"],
            "compliance_violation": True,
            "difficulty": "hard",
        },
    ]

    save_json(questions, OUTPUT_DIR / "benchmark" / "benchmark_questions.json")
    return questions


# ── Step 6: Generate Data Manifest ─────────────────────────────────
def generate_manifest():
    """Create a manifest documenting everything in the data directory."""
    print("\n📋 Step 6: Generating data manifest...")

    manifest = {
        "generated_at": datetime.datetime.now().isoformat(),
        "description": "HP + Morningstar AI Hackathon sample data",
        "generator_script": "prep_hackathon_data.py",
        "directories": {
            "portfolios/": "5 sample portfolio JSON files with holdings, weights, and sector data",
            "filings/": "SEC 10-K full-text files (.txt) — chunking strategy is left to participants",
            "compliance/": "restricted_list.csv and compliance_rules.yaml",
            "benchmark/": "benchmark_questions.json with 10 test queries and expected answers",
            "metadata/": "sector_map.json and filing_manifest.json",
        },
        "data_sources": {
            "ticker_metadata": "Yahoo Finance via yfinance (free, no API key)",
            "sec_filings": "SEC EDGAR via edgartools (free, no API key)",
            "portfolios": "Synthetically generated using real ticker/sector data",
            "restricted_list": "Synthetically generated for hackathon use",
            "compliance_rules": "Synthetically generated — realistic but fictional policy",
        },
        "usage_notes": [
            "Copy entire hackathon_data/ directory to the ZGX Nano",
            "All data is self-contained — no internet access needed during hackathon",
            "Filings are raw full text — participants choose their own chunking strategy",
            "Portfolios are designed to trigger compliance violations for demo purposes",
            "Benchmark questions have known answers for evaluation in Sprint 3",
        ],
    }

    save_json(manifest, OUTPUT_DIR / "metadata" / "data_manifest.json")


# ── Main ───────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  HP + MORNINGSTAR AI HACKATHON — DATA PREPARATION")
    print("=" * 70)
    print(f"\n  Output directory: {OUTPUT_DIR.resolve()}")
    print(f"  EDGAR identity:  {EDGAR_IDENTITY}")

    # Create directory structure
    for subdir in ["portfolios", "filings", "compliance", "benchmark", "metadata"]:
        ensure_dir(OUTPUT_DIR / subdir)

    # Check dependencies
    missing = []
    try:
        import yfinance
    except ImportError:
        missing.append("yfinance")
    try:
        import yaml
    except ImportError:
        missing.append("pyyaml")

    # edgartools is optional — we have a synthetic fallback
    has_edgartools = True
    try:
        import edgar
    except ImportError:
        has_edgartools = False
        print("\n  ⚠ edgartools not installed — will use synthetic filing data")
        print("    To pull real SEC filings: pip install edgartools")

    if missing:
        print(f"\n  ✗ Missing required packages: {', '.join(missing)}")
        print(f"    Install with: pip install {' '.join(missing)}")
        sys.exit(1)

    # Run all steps
    random.seed(42)  # Global seed for reproducibility

    metadata = pull_ticker_metadata()
    portfolios = generate_portfolios(metadata)

    if has_edgartools:
        pull_filing_excerpts()
    else:
        generate_synthetic_filings()

    restricted = generate_compliance_data(metadata)
    generate_benchmark_questions(portfolios, restricted)
    generate_manifest()

    # Summary
    print("\n" + "=" * 70)
    print("  ✅ DATA PREPARATION COMPLETE")
    print("=" * 70)

    portfolio_count = len(list((OUTPUT_DIR / "portfolios").glob("*.json")))
    filing_count = len(list((OUTPUT_DIR / "filings").glob("*.txt")) + list((OUTPUT_DIR / "filings").glob("*.json")))

    print(f"""
  Output:  {OUTPUT_DIR.resolve()}

  📁 {portfolio_count} portfolios          → portfolios/
  📄 {filing_count} filings (full text) → filings/
  🔒 restricted_list.csv    → compliance/
  📏 compliance_rules.yaml  → compliance/
  📝 benchmark_questions    → benchmark/
  📋 manifests & metadata   → metadata/

  Next steps:
  1. Review the data in {OUTPUT_DIR}/
  2. Copy the entire directory to the ZGX Nano
  3. Test the benchmark questions against your reference implementation
""")


if __name__ == "__main__":
    main()