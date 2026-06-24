"""
Agent 4: PMF Scoring Engine

Calculates Product-Market Fit (PMF) and Confidence scores for each Market × Technology cell.
- PMF score (0-100): desirability, feasibility, viability, risk
- Confidence score (0-100): reflects evidence quality, diversity, recency
- Full audit trail for traceability

Usage:
    engine = ScoringEngine('agent4_config.yaml')
    results = engine.score_cells(evidence_df, cell_definitions)
    engine.export_results(results, 'output/')
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path
import json
import yaml
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class EvidenceItem:
    """A single evidence item with full provenance and scoring metadata"""
    evidence_id: str
    source_name: str
    source_locator: str
    date_published: str  # ISO format YYYY-MM-DD
    excerpt: str
    signal_type: str  # A3
    value_chain_role: str  # A4
    mapped_market: str  # A1
    mapped_technology: str  # A2
    mapped_confidence: float  # 0-1, how confident is the cell assignment
    performance_claims: List[str] = field(default_factory=list)  # A5 tags
    conditions_of_use: Dict[str, str] = field(default_factory=dict)  # A6 known/unknown
    
    # Scoring calculation (populated by engine)
    age_days: int = None
    base_weight: float = None
    credibility_multiplier: float = None
    recency_multiplier: float = None
    final_weight: float = None
    recency_flag: str = None  # "stale", "very_stale", etc.


@dataclass
class SubScores:
    """PMF component sub-scores (0-100 each)"""
    desirability: float = 0.0
    feasibility: float = 0.0
    viability: float = 0.0
    risk_penalty: float = 0.0


@dataclass
class PMFCalculation:
    """Complete PMF score with breakdown and audit trail"""
    market: str
    technology: str
    pmf_score: float
    sub_scores: SubScores
    confidence_score: float
    
    # Evidence summary
    num_evidence_items: int
    evidence_ids: List[str] = field(default_factory=list)
    
    # Confidence penalties breakdown
    confidence_penalties: Dict[str, float] = field(default_factory=dict)
    confidence_bonuses: Dict[str, float] = field(default_factory=dict)
    
    # Interpretation
    shift_expectation: str = ""  # "Major Shift Toward", etc.
    confidence_level: str = ""  # "High", "Medium", "Low"
    
    # Audit trail
    calculation_timestamp: str = ""
    detailed_audit: Dict = field(default_factory=dict)


# ============================================================================
# SCORING ENGINE
# ============================================================================

class ScoringEngine:
    """Main scoring engine for Agent 4"""
    
    def __init__(self, config_path: str):
        """Initialize scoring engine with configuration"""
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.logger.info(f"ScoringEngine initialized with config v{self.config['version']}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for audit trail"""
        logger = logging.getLogger('ScoringEngine')
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        return logger
    
    def score_cells(self, evidence_df: pd.DataFrame, cell_definitions: List[Tuple[str, str]]) -> Dict:
        """
        Score all cells given evidence dataframe and cell definitions
        
        Args:
            evidence_df: DataFrame with evidence items (must have all required columns)
            cell_definitions: List of (market, technology) tuples to score
        
        Returns:
            Dict mapping (market, technology) -> PMFCalculation
        """
        self.logger.info(f"Starting scoring for {len(cell_definitions)} cells with {len(evidence_df)} evidence items")
        
        results = {}
        
        for market, technology in cell_definitions:
            # Filter evidence for this cell
            cell_evidence = evidence_df[
                (evidence_df['mapped_market'] == market) & 
                (evidence_df['mapped_technology'] == technology)
            ].copy()
            
            # Score the cell
            calculation = self._score_cell(market, technology, cell_evidence)
            results[(market, technology)] = calculation
            
            self.logger.debug(f"Scored {market} × {technology}: PMF={calculation.pmf_score:.1f}, Conf={calculation.confidence_score:.1f}")
        
        return results
    
    def _score_cell(self, market: str, technology: str, evidence_df: pd.DataFrame) -> PMFCalculation:
        """Score a single cell"""
        
        # Initialize calculation
        calc = PMFCalculation(
            market=market,
            technology=technology,
            pmf_score=0.0,
            sub_scores=SubScores(),
            confidence_score=0.0,
            num_evidence_items=len(evidence_df),
            calculation_timestamp=datetime.utcnow().isoformat()
        )
        
        # Handle empty cell
        if len(evidence_df) == 0:
            calc.confidence_score = 0.0
            calc.shift_expectation = "No Data"
            calc.confidence_level = "No Data"
            return calc
        
        # Calculate age and weights for each evidence item
        evidence_df['age_days'] = (pd.Timestamp(datetime.now().date()) - pd.to_datetime(evidence_df['date_published'])).dt.days
        evidence_df['age_days'] = evidence_df['age_days'].fillna(30)  # Default 30 days if parsing failed
        evidence_df['final_weight'] = evidence_df.apply(
            lambda row: self._calculate_evidence_weight(row),
            axis=1
        )
        
        # Calculate PMF sub-scores
        calc.sub_scores = self._calculate_sub_scores(evidence_df)
        
        # Apply feasibility cap for critical unknowns
        calc.sub_scores.feasibility = self._apply_feasibility_cap(evidence_df, calc.sub_scores.feasibility)
        
        # Calculate composite PMF score
        weights = self.config['pmf_weights']
        calc.pmf_score = (
            weights['desirability'] * calc.sub_scores.desirability +
            weights['feasibility'] * calc.sub_scores.feasibility +
            weights['viability'] * calc.sub_scores.viability +
            weights['risk_penalty'] * (100 - calc.sub_scores.risk_penalty)
        )
        calc.pmf_score = max(0, min(100, calc.pmf_score))  # Clamp 0-100
        
        # Calculate confidence score
        calc.confidence_score = self._calculate_confidence(evidence_df, calc)
        
        # Interpret scores
        calc.shift_expectation = self._get_shift_expectation(calc.pmf_score)
        calc.confidence_level = self._get_confidence_level(calc.confidence_score)
        
        # Store evidence IDs for traceability
        calc.evidence_ids = evidence_df['evidence_id'].tolist()
        
        # Build audit trail
        calc.detailed_audit = self._build_audit_trail(evidence_df, calc)
        
        return calc
    
    def _calculate_evidence_weight(self, row: pd.Series) -> float:
        """Calculate final weight for an evidence item: base × credibility × recency"""
        
        # Get base weight from signal type
        signal_type = row['signal_type']
        signal_config = self.config['signal_type_weights'].get(signal_type, {})
        base_weight = signal_config.get('base', 0)
        
        # Get credibility multiplier from value chain role
        role = row['value_chain_role']
        role_config = self.config['credibility_multipliers'].get(role, {})
        credibility_mult = role_config.get('multiplier', 0.7)
        
        # Get recency multiplier
        age_days = row['age_days']
        recency_mult = self._get_recency_multiplier(age_days)
        
        final_weight = base_weight * credibility_mult * recency_mult
        
        return final_weight
    
    def _get_recency_multiplier(self, age_days: int) -> float:
        """Get recency multiplier based on evidence age"""
        for tier in ['recent', 'moderate', 'old', 'very_old']:
            tier_config = self.config['recency_multipliers'][tier]
            if tier_config['days_min'] <= age_days <= tier_config['days_max']:
                return tier_config['multiplier']
        return 0.3
    
    def _calculate_sub_scores(self, evidence_df: pd.DataFrame) -> SubScores:
        """Calculate desirability, feasibility, viability, risk sub-scores"""
        
        sub_scores = SubScores()
        signal_weights = self.config['signal_type_weights']
        
        # Route weighted evidence to correct sub-score components
        for _, row in evidence_df.iterrows():
            signal_type = row['signal_type']
            final_weight = row['final_weight']
            
            if signal_type not in signal_weights:
                continue
            
            components = signal_weights[signal_type].get('component', [])
            
            if 'desirability' in components:
                sub_scores.desirability += final_weight
            if 'feasibility' in components:
                sub_scores.feasibility += final_weight
            if 'viability' in components:
                sub_scores.viability += final_weight
            if 'risk_penalty' in components:
                # Risk items subtract (penalty model)
                risk_config = self.config['risk_penalties'].get(signal_type, {})
                sub_scores.risk_penalty += risk_config.get('penalty', 0)
        
        # Normalize sub-scores to 0-100 range (cap at 100)
        sub_scores.desirability = min(100, sub_scores.desirability)
        sub_scores.feasibility = min(100, sub_scores.feasibility)
        sub_scores.viability = min(100, sub_scores.viability)
        sub_scores.risk_penalty = min(100, sub_scores.risk_penalty)
        
        return sub_scores
    
    def _apply_feasibility_cap(self, evidence_df: pd.DataFrame, feasibility: float) -> float:
        """Apply feasibility cap for critical A6 unknowns"""
        
        feasibility_cap_config = self.config['feasibility_cap']
        critical_unknowns = feasibility_cap_config['critical_unknowns']
        
        # Count critical unknowns across evidence
        total_critical_unknowns = 0
        for _, row in evidence_df.iterrows():
            conditions = row.get('conditions_of_use', {})
            for unknown_field in critical_unknowns:
                if conditions.get(unknown_field) == 'Unknown':
                    total_critical_unknowns += 1
        
        # Apply cap
        cap_penalty = total_critical_unknowns * feasibility_cap_config['penalty_per_unknown']
        capped_feasibility = max(0, feasibility - cap_penalty)
        
        return capped_feasibility
    
    def _calculate_confidence(self, evidence_df: pd.DataFrame, calc: PMFCalculation) -> float:
        """Calculate confidence score with all penalties and bonuses"""
        
        confidence = self.config['confidence_scoring']['starting_score']
        penalties = self.config['confidence_scoring']['penalties']
        bonuses = self.config['confidence_scoring']['bonuses']
        
        calc.confidence_penalties = {}
        calc.confidence_bonuses = {}
        
        # ===== PENALTIES =====
        
        # Unknown conditions-of-use (A6)
        all_conditions = []
        critical_unknown_count = 0
        non_critical_unknown_count = 0
        for _, row in evidence_df.iterrows():
            conditions = row.get('conditions_of_use', {})
            for field, status in conditions.items():
                if status == 'Unknown':
                    if field in penalties['critical_unknown_conditions'].get('list', []):
                        critical_unknown_count += 1
                    else:
                        non_critical_unknown_count += 1
        
        if non_critical_unknown_count > 0:
            penalty_amt = non_critical_unknown_count * penalties['unknown_conditions_of_use']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['unknowns_non_critical'] = penalty_amt
        
        if critical_unknown_count > 0:
            penalty_amt = critical_unknown_count * penalties['critical_unknown_conditions']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['unknowns_critical'] = penalty_amt
        
        # Evidence sparsity
        num_items = len(evidence_df)
        if num_items < 2:
            penalty_amt = penalties['evidence_sparsity_very_low']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['sparsity'] = penalty_amt
        elif num_items < 5:
            penalty_amt = penalties['evidence_sparsity_low']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['sparsity'] = penalty_amt
        
        # Single source name
        num_unique_sources = evidence_df['source_name'].nunique()
        if num_unique_sources == 1 and penalties['single_source_name']['applicable']:
            penalty_amt = penalties['single_source_name']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['single_source'] = penalty_amt
        
        # Single credibility role
        num_unique_roles = evidence_df['value_chain_role'].nunique()
        if num_unique_roles == 1 and penalties['single_credibility_role']['applicable']:
            penalty_amt = penalties['single_credibility_role']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['single_role'] = penalty_amt
        
        # Staleness
        old_evidence = evidence_df[evidence_df['age_days'] > 365]
        if len(old_evidence) / len(evidence_df) > penalties['staleness_majority']['threshold']:
            penalty_amt = penalties['staleness_majority']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['staleness'] = penalty_amt
        
        # Low mapping confidence
        avg_mapping_conf = evidence_df['mapped_confidence'].mean()
        if avg_mapping_conf < penalties['low_mapping_confidence']['threshold']:
            penalty_amt = penalties['low_mapping_confidence']['penalty']
            confidence += penalty_amt
            calc.confidence_penalties['mapping_uncertainty'] = penalty_amt
        
        # ===== BONUSES =====
        
        # Independent validation
        testing_roles = evidence_df[
            evidence_df['value_chain_role'].isin(['certification_testing_lab', 'regulatory_standards_body'])
        ]
        if len(testing_roles) > 0 and bonuses['independent_validation']['applicable']:
            bonus_amt = bonuses['independent_validation']['bonus']
            confidence += bonus_amt
            calc.confidence_bonuses['independent_validation'] = bonus_amt
        
        # Diversity bonus (3+ different roles)
        if num_unique_roles >= 3:
            bonus_amt = bonuses['diversity_bonus']['bonus']
            confidence += bonus_amt
            calc.confidence_bonuses['diversity'] = bonus_amt
        
        # Recent evidence bonus
        recent_evidence = evidence_df[evidence_df['age_days'] <= 90]
        if len(recent_evidence) / len(evidence_df) > 0.5:
            bonus_amt = bonuses['recent_evidence']['bonus']
            confidence += bonus_amt
            calc.confidence_bonuses['recency'] = bonus_amt
        
        # Clamp to 0-100
        confidence = max(0, min(100, confidence))
        
        return confidence
    
    def _get_shift_expectation(self, pmf_score: float) -> str:
        """Map PMF score to shift expectation label"""
        bands = self.config['pmf_score_bands']
        for band_name, band_config in bands.items():
            if band_config['min'] <= pmf_score <= band_config['max']:
                return band_config['shift_expectation']
        return "Unknown"
    
    def _get_confidence_level(self, confidence_score: float) -> str:
        """Map confidence score to confidence level"""
        bands = self.config['confidence_score_bands']
        for band_name, band_config in bands.items():
            if band_config['min'] <= confidence_score <= band_config['max']:
                return band_config['label']
        return "Unknown"
    
    def _build_audit_trail(self, evidence_df: pd.DataFrame, calc: PMFCalculation) -> Dict:
        """Build detailed audit trail for this cell"""
        audit = {
            'cell': f"{calc.market} × {calc.technology}",
            'timestamp': calc.calculation_timestamp,
            'num_evidence_items': calc.num_evidence_items,
            'pmf_components': asdict(calc.sub_scores),
            'pmf_calculation': {
                'desirability_contribution': self.config['pmf_weights']['desirability'] * calc.sub_scores.desirability,
                'feasibility_contribution': self.config['pmf_weights']['feasibility'] * calc.sub_scores.feasibility,
                'viability_contribution': self.config['pmf_weights']['viability'] * calc.sub_scores.viability,
                'risk_contribution': self.config['pmf_weights']['risk_penalty'] * (100 - calc.sub_scores.risk_penalty),
                'total_pmf': calc.pmf_score,
            },
            'confidence_calculation': {
                'penalties': calc.confidence_penalties,
                'bonuses': calc.confidence_bonuses,
                'total_confidence': calc.confidence_score,
            },
            'evidence_details': [
                {
                    'evidence_id': row['evidence_id'],
                    'source': row['source_name'],
                    'signal_type': row['signal_type'],
                    'role': row['value_chain_role'],
                    'age_days': int(row['age_days']) if pd.notna(row['age_days']) else 0,
                    'final_weight': round(row['final_weight'], 2),
                    'excerpt': row['excerpt'][:100] + '...' if len(row['excerpt']) > 100 else row['excerpt']
                }
                for _, row in evidence_df.iterrows()
            ]
        }
        return audit
    
    def export_results(self, results: Dict[Tuple[str, str], PMFCalculation], output_dir: str):
        """Export scoring results to CSV and JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Main PMF matrix CSV
        matrix_data = []
        for (market, tech), calc in results.items():
            matrix_data.append({
                'Market': market,
                'Technology': tech,
                'PMF_Score': round(calc.pmf_score, 2),
                'Desirability': round(calc.sub_scores.desirability, 2),
                'Feasibility': round(calc.sub_scores.feasibility, 2),
                'Viability': round(calc.sub_scores.viability, 2),
                'Risk_Penalty': round(calc.sub_scores.risk_penalty, 2),
                'Confidence_Score': round(calc.confidence_score, 2),
                'Shift_Expectation': calc.shift_expectation,
                'Confidence_Level': calc.confidence_level,
                'Num_Evidence_Items': calc.num_evidence_items,
            })
        
        matrix_df = pd.DataFrame(matrix_data).sort_values('PMF_Score', ascending=False)
        matrix_df.to_csv(output_path / 'agent4_pmf_matrix.csv', index=False)
        self.logger.info(f"Exported PMF matrix to {output_path / 'agent4_pmf_matrix.csv'}")
        
        # 2. Detailed audit trail JSON
        audit_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'config_version': self.config['version'],
            'num_cells': len(results),
            'cells': {
                f"{market}|{tech}": asdict(calc) if isinstance(calc, PMFCalculation) else calc
                for (market, tech), calc in results.items()
            }
        }
        
        with open(output_path / 'agent4_audit_trail.json', 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)
        self.logger.info(f"Exported audit trail to {output_path / 'agent4_audit_trail.json'}")
        
        # 3. Summary stats
        summary = {
            'total_cells_scored': len(results),
            'avg_pmf_score': round(np.mean([calc.pmf_score for calc in results.values()]), 2),
            'avg_confidence': round(np.mean([calc.confidence_score for calc in results.values()]), 2),
            'high_confidence_cells': sum(1 for calc in results.values() if calc.confidence_score >= 70),
            'high_pmf_cells': sum(1 for calc in results.values() if calc.pmf_score >= 70),
            'export_timestamp': datetime.utcnow().isoformat(),
        }
        
        with open(output_path / 'agent4_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        self.logger.info(f"Export complete. Summary: {summary}")
        
        return matrix_df


if __name__ == '__main__':
    print("Agent 4 Scoring Engine Module")
    print("Import this module and use ScoringEngine class")
