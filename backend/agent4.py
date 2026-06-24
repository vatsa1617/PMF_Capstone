"""
Agent 4: Score & Publish
Consolidates evidence from Agents 1-3, scores all Market×Technology cells,
and produces the PMF heat map with full audit trails.

Input:
  - evidence_items.csv (consolidated evidence from all sources)
  - cell_definitions.csv (market/technology pairs to score)
  
Output:
  - agent4_pmf_matrix.csv (main heat map data)
  - agent4_audit_trail.json (full calculation details)
  - agent4_summary.json (summary statistics)
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import json

# Import our scoring engine
from agent4_scoring_engine import ScoringEngine, EvidenceItem


def load_evidence_items(evidence_csv: str) -> pd.DataFrame:
    """Load and validate evidence items"""
    print(f"Loading evidence from {evidence_csv}...")
    df = pd.read_csv(evidence_csv)
    
    # Validate required columns
    required_cols = [
        'evidence_id', 'source_name', 'source_locator', 'date_published',
        'excerpt', 'signal_type', 'value_chain_role', 'mapped_market',
        'mapped_technology', 'mapped_confidence'
    ]
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    print(f"✓ Loaded {len(df)} evidence items")
    return df


def load_cell_definitions(cells_csv: str = None, evidence_df: pd.DataFrame = None) -> list:
    """
    Load cell definitions from CSV, or derive from evidence data

    Args:
        cells_csv: Path to CSV with 'market' and 'technology' columns
        evidence_df: Alternative: derive cells from evidence data

    Returns:
        List of (market, technology) tuples
    """

    if cells_csv and Path(cells_csv).exists():
        print(f"Loading cell definitions from {cells_csv}...")
        df = pd.read_csv(cells_csv)
        cells = list(zip(df['market'], df['technology']))
        print(f"✓ Loaded {len(cells)} cell definitions")
    elif evidence_df is not None:
        print("Deriving cell definitions from evidence data...")
        # Handle both naming conventions
        market_col = None
        tech_col = None

        for col in evidence_df.columns:
            if 'mapped_market' in col.lower() and '_a1_1' in col.lower():
                market_col = col
            if 'mapped_tech' in col.lower() and '_a2_1' in col.lower():
                tech_col = col

        if market_col is None or tech_col is None:
            # Fallback to any mapped columns
            market_col = [c for c in evidence_df.columns if 'market' in c.lower()][0] if any('market' in c.lower() for c in evidence_df.columns) else None
            tech_col = [c for c in evidence_df.columns if 'tech' in c.lower()][0] if any('tech' in c.lower() for c in evidence_df.columns) else None

        if market_col and tech_col:
            cells = evidence_df[[market_col, tech_col]].drop_duplicates().values.tolist()
            cells = [(market, tech) for market, tech in cells if pd.notna(market) and pd.notna(tech)]
        else:
            print(f"Available columns: {evidence_df.columns.tolist()}")
            raise ValueError(f"Could not find market/technology columns. Market: {market_col}, Tech: {tech_col}")

        print(f"✓ Derived {len(cells)} unique cells from evidence")
    else:
        raise ValueError("Must provide either cells_csv or evidence_df")

    return cells


def generate_cell_definitions_csv(evidence_df: pd.DataFrame, output_path: str):
    """Generate a cell definitions CSV for reference"""
    # Find the right columns
    market_col = None
    tech_col = None

    for col in evidence_df.columns:
        if 'mapped_market' in col.lower() and '_a1_1' in col.lower():
            market_col = col
        if 'mapped_tech' in col.lower() and '_a2_1' in col.lower():
            tech_col = col

    if market_col and tech_col:
        cells = evidence_df[[market_col, tech_col]].drop_duplicates()
        cells.columns = ['market', 'technology']
        cells = cells.sort_values(['market', 'technology'])
        cells.to_csv(output_path, index=False)
        print(f"✓ Generated cell definitions template: {output_path}")


def consolidate_agent_outputs(
    agent1_evidence_csv: str,
    agent2_sec_csv: str = None,
    agent3_esg_csv: str = None,
    output_csv: str = "output/evidence_items_consolidated.csv"
) -> pd.DataFrame:
    """
    Consolidate evidence from all three agents into a single dataset.
    This represents the "Normalize" stage output.
    """
    
    print("\n=== CONSOLIDATING EVIDENCE FROM ALL AGENTS ===")
    
    # Agent 1 evidence (GDELT news)
    print(f"Loading Agent 1 evidence from {agent1_evidence_csv}...")
    agent1_df = pd.read_csv(agent1_evidence_csv)
    
    # Add required columns if missing
    if 'signal_type' not in agent1_df.columns:
        agent1_df['signal_type'] = 'material_performance_claim'  # Default
    
    if 'value_chain_role' not in agent1_df.columns:
        agent1_df['value_chain_role'] = 'industry_publication_analyst'  # GDELT source role
    
    agent1_df['agent_source'] = 'agent1_gdelt'
    print(f"  ✓ {len(agent1_df)} evidence items from Agent 1")
    
    # Agent 2 evidence (SEC filings) - optional
    agent2_df = None
    if agent2_sec_csv and Path(agent2_sec_csv).exists():
        print(f"Loading Agent 2 evidence from {agent2_sec_csv}...")
        agent2_df = pd.read_csv(agent2_sec_csv)
        agent2_df['agent_source'] = 'agent2_sec'
        print(f"  ✓ {len(agent2_df)} evidence items from Agent 2")
    else:
        print("  (Agent 2 data not provided, skipping)")
    
    # Agent 3 evidence (ESG reports) - optional
    agent3_df = None
    if agent3_esg_csv and Path(agent3_esg_csv).exists():
        print(f"Loading Agent 3 evidence from {agent3_esg_csv}...")
        agent3_df = pd.read_csv(agent3_esg_csv)
        agent3_df['agent_source'] = 'agent3_esg'
        print(f"  ✓ {len(agent3_df)} evidence items from Agent 3")
    else:
        print("  (Agent 3 data not provided, skipping)")
    
    # Combine all
    all_dfs = [agent1_df]
    if agent2_df is not None:
        all_dfs.append(agent2_df)
    if agent3_df is not None:
        all_dfs.append(agent3_df)
    
    consolidated = pd.concat(all_dfs, ignore_index=True)
    
    # Map columns to standard evidence schema
    # Handle variations in column names
    column_mapping = {
        'url': 'source_locator',
        'source_url': 'source_locator',
        'matched_term': 'excerpt',
        'ticker': 'entity',
        'company': 'entity',
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in consolidated.columns and new_col not in consolidated.columns:
            consolidated[new_col] = consolidated[old_col]
    
    # Add missing required columns with defaults
    if 'evidence_id' not in consolidated.columns:
        consolidated['evidence_id'] = consolidated.index.astype(str).str.zfill(6)
    
    if 'mapped_market' not in consolidated.columns:
        consolidated['mapped_market'] = 'Unknown'
    
    if 'mapped_technology' not in consolidated.columns:
        consolidated['mapped_technology'] = 'Unknown'
    
    if 'mapped_confidence' not in consolidated.columns:
        consolidated['mapped_confidence'] = 0.7
    
    # Select core columns
    core_cols = [
        'evidence_id', 'source_name', 'source_locator', 'date_published',
        'excerpt', 'signal_type', 'value_chain_role', 'mapped_market',
        'mapped_technology', 'mapped_confidence', 'agent_source'
    ]
    
    # Only keep columns that exist
    keep_cols = [col for col in core_cols if col in consolidated.columns]
    consolidated = consolidated[keep_cols]
    
    # Save
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    consolidated.to_csv(output_csv, index=False)
    
    print(f"\n✓ CONSOLIDATED {len(consolidated)} total evidence items")
    print(f"  Sources: {consolidated['source_name'].nunique()} unique sources")
    print(f"  Markets: {consolidated['mapped_market'].nunique()} unique markets")
    print(f"  Technologies: {consolidated['mapped_technology'].nunique()} unique technologies")
    print(f"  Saved to: {output_csv}\n")
    
    return consolidated


def main(args=None):
    """Main execution flow"""
    
    print("=" * 80)
    print("AGENT 4: SCORE & PUBLISH")
    print("=" * 80)
    
    # Default paths (can be overridden via args)
    agent1_evidence = "output/agent1_evidence.csv"
    agent2_sec = "output/agent2_sec_packaging_pressure_hits.csv"
    agent3_esg = "output/agent3_esg_packaging_hits.csv"
    config_path = "agent4_config.yaml"
    output_dir = "output/"
    
    # Allow command-line override
    if args:
        if len(args) > 0:
            agent1_evidence = args[0]
        if len(args) > 1:
            agent2_sec = args[1]
        if len(args) > 2:
            agent3_esg = args[2]
        if len(args) > 3:
            output_dir = args[3]
    
    # Check input paths
    if not Path(agent1_evidence).exists():
        print(f"ERROR: Agent 1 evidence file not found: {agent1_evidence}")
        print("Please run Agent 1 first to generate evidence data")
        return False
    
    if not Path(config_path).exists():
        print(f"ERROR: Config file not found: {config_path}")
        return False
    
    # ===== CONSOLIDATE EVIDENCE =====
    consolidated_path = f"{output_dir}/evidence_items_consolidated.csv"

    # Check if consolidated evidence already exists
    if Path(consolidated_path).exists():
        print(f"\n✓ Using existing consolidated evidence: {consolidated_path}")
        evidence_df = pd.read_csv(consolidated_path)
        print(f"✓ Loaded {len(evidence_df)} evidence items")
    else:
        evidence_df = consolidate_agent_outputs(
            agent1_evidence,
            agent2_sec,
            agent3_esg,
            consolidated_path
        )

    # ===== PREPROCESS COLUMNS =====
    # Rename columns to match scoring engine expectations
    rename_map = {}
    for col in evidence_df.columns:
        col_lower = col.lower()
        if 'mapped_market' in col_lower and '_a1_1' in col_lower:
            rename_map[col] = 'mapped_market'
        elif 'mapped_tech' in col_lower and '_a2_1' in col_lower:
            rename_map[col] = 'mapped_technology'
        elif col_lower in ['mapping_confidence', 'mapped_confidence_score']:
            rename_map[col] = 'mapped_confidence'
        elif 'date_published' in col_lower:
            rename_map[col] = 'date_published'
        elif 'signal_type' in col_lower and '_a3' in col_lower:
            rename_map[col] = 'signal_type'
        elif 'value_chain_role' in col_lower and '_a4' in col_lower:
            rename_map[col] = 'value_chain_role'
        elif 'conditions_of_use' in col_lower and '_a6' in col_lower:
            rename_map[col] = 'conditions_of_use'

    if rename_map:
        evidence_df = evidence_df.rename(columns=rename_map)
        print(f"✓ Renamed {len(rename_map)} columns")

    # Ensure required columns exist
    if 'mapped_confidence' not in evidence_df.columns:
        evidence_df['mapped_confidence'] = 0.75
        print("✓ Added default mapped_confidence column")

    # Convert date column to datetime
    if 'date_published' in evidence_df.columns:
        evidence_df['date_published'] = pd.to_datetime(evidence_df['date_published'], errors='coerce')

    # Fill NaN values in key columns
    if 'signal_type' in evidence_df.columns:
        evidence_df['signal_type'] = evidence_df['signal_type'].fillna('unknown')
    else:
        evidence_df['signal_type'] = 'unknown'

    if 'value_chain_role' in evidence_df.columns:
        evidence_df['value_chain_role'] = evidence_df['value_chain_role'].fillna('unknown')
    else:
        evidence_df['value_chain_role'] = 'unknown'

    if 'source_name' in evidence_df.columns:
        evidence_df['source_name'] = evidence_df['source_name'].fillna('unknown')
    else:
        evidence_df['source_name'] = 'unknown'

    # conditions_of_use should be a dict per row; for now use empty dict
    evidence_df['conditions_of_use'] = evidence_df.apply(lambda row: {}, axis=1)

    # Ensure text columns are strings
    if 'excerpt' in evidence_df.columns:
        evidence_df['excerpt'] = evidence_df['excerpt'].fillna('').astype(str)
    else:
        evidence_df['excerpt'] = ''
    
    # ===== DEFINE CELLS =====
    cell_defs = load_cell_definitions(evidence_df=evidence_df)
    
    # Generate template for reference
    generate_cell_definitions_csv(evidence_df, f"{output_dir}/cell_definitions_template.csv")
    
    # ===== INITIALIZE SCORING ENGINE =====
    print("\n=== INITIALIZING SCORING ENGINE ===")
    engine = ScoringEngine(config_path)
    print("✓ Scoring engine initialized")
    
    # ===== SCORE ALL CELLS =====
    print("\n=== SCORING ALL CELLS ===")
    results = engine.score_cells(evidence_df, cell_defs)
    print(f"✓ Scored {len(results)} cells")
    
    # ===== EXPORT RESULTS =====
    print("\n=== EXPORTING RESULTS ===")
    matrix_df = engine.export_results(results, output_dir)
    
    # ===== SUMMARY STATISTICS =====
    print("\n=== SCORING SUMMARY ===")
    print(f"Total cells scored: {len(matrix_df)}")
    print(f"Average PMF score: {matrix_df['PMF_Score'].mean():.1f}")
    print(f"Average confidence: {matrix_df['Confidence_Score'].mean():.1f}")
    print(f"High-confidence cells (70+): {(matrix_df['Confidence_Score'] >= 70).sum()}")
    print(f"High-PMF cells (70+): {(matrix_df['PMF_Score'] >= 70).sum()}")
    
    print("\n=== TOP OPPORTUNITIES (by PMF Score) ===")
    print(matrix_df[['Market', 'Technology', 'PMF_Score', 'Confidence_Score', 'Shift_Expectation']].head(10).to_string(index=False))
    
    print("\n=== HIGH POTENTIAL / LOW CONFIDENCE (need more evidence) ===")
    interesting = matrix_df[(matrix_df['PMF_Score'] >= 60) & (matrix_df['Confidence_Score'] < 50)]
    if len(interesting) > 0:
        print(interesting[['Market', 'Technology', 'PMF_Score', 'Confidence_Score']].head(10).to_string(index=False))
    else:
        print("(None)")
    
    print("\n" + "=" * 80)
    print("✓ AGENT 4 COMPLETE")
    print(f"Outputs saved to: {output_dir}")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    import sys
    success = main(sys.argv[1:])
    sys.exit(0 if success else 1)
