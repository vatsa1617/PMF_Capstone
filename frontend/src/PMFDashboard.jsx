import React, { useState, useEffect, useMemo } from 'react';
import './PMFDashboard.css';

/**
 * PMF Heat Map Dashboard
 * 
 * Interactive Market × Technology heat map showing:
 * - PMF Score (0-100) as cell color intensity
 * - Confidence Level (visual indicator)
 * - Drill-down to evidence and score breakdown
 * - Evidence gap analysis
 * - Portfolio decision recommendations
 */

// Color palette and interpretation bands
const COLOR_SCHEME = {
  // PMF Score band colors
  shift: {
    'Major Shift Away': '#d32f2f',      // Red
    'Minor Shift Away': '#f57c00',      // Orange  
    'No Shift': '#fbc02d',              // Yellow
    'Minor Shift Toward': '#689f38',    // Light Green
    'Major Shift Toward': '#2e7d32',    // Dark Green
  },
  
  // Confidence visual indicator
  confidence: {
    high: '★★★',      // High confidence (70-100)
    medium: '★★☆',    // Medium confidence (40-69)
    low: '★☆☆',       // Low confidence (0-39)
  },
  
  // Score bands
  pmfBands: [
    { min: 0, max: 39, label: 'Low', color: '#d32f2f' },
    { min: 40, max: 54, label: 'Medium-Low', color: '#f57c00' },
    { min: 55, max: 65, label: 'Medium', color: '#fbc02d' },
    { min: 66, max: 75, label: 'Medium-High', color: '#689f38' },
    { min: 76, max: 100, label: 'High', color: '#2e7d32' },
  ],
};

// Sample data (in production, this would come from agent4_pmf_matrix.csv)
const SAMPLE_PMF_DATA = [
  { market: 'Food - Frozen & Refrigerated', technology: 'Molded Fiber - Trays', pmf: 72.5, confidence: 82, desirability: 75, feasibility: 70, viability: 68, risk: 5 },
  { market: 'Food - Frozen & Refrigerated', technology: 'Paper-based Flexibles - High barrier', pmf: 68.3, confidence: 65, desirability: 70, feasibility: 65, viability: 60, risk: 15 },
  { market: 'Food - Ready Meals', technology: 'Molded Fiber - Trays', pmf: 61.5, confidence: 45, desirability: 65, feasibility: 55, viability: 50, risk: 20 },
  { market: 'Beverage - Multipacks', technology: 'Paper-based Flexibles - Recyclable coatings', pmf: 58.2, confidence: 72, desirability: 60, feasibility: 58, viability: 55, risk: 10 },
  { market: 'Home Care - Detergent / Pods', technology: 'Molded Fiber - Cups/lids', pmf: 54.0, confidence: 38, desirability: 52, feasibility: 50, viability: 48, risk: 25 },
  { market: 'QSR / Foodservice - To-go', technology: 'Paperboard Cartons - Barrier & grease', pmf: 75.2, confidence: 78, desirability: 78, feasibility: 76, viability: 72, risk: 8 },
  { market: 'E-commerce - SIOC / Protective', technology: 'Paper Canisters', pmf: 45.5, confidence: 52, desirability: 48, feasibility: 42, viability: 40, risk: 35 },
];

// Extract unique markets and technologies
const extractUnique = (data, field) => [...new Set(data.map(item => item[field]))].sort();

/**
 * Individual Cell Component
 */
function PMFCell({ data, selected, onClick }) {
  const getConfidenceBadge = (conf) => {
    if (conf >= 70) return '★★★';
    if (conf >= 40) return '★★☆';
    return '★☆☆';
  };
  
  const getBandColor = (pmf) => {
    for (let band of COLOR_SCHEME.pmfBands) {
      if (pmf >= band.min && pmf <= band.max) {
        return band.color;
      }
    }
    return '#e0e0e0';
  };
  
  if (!data) {
    return <div className="pmf-cell empty" />;
  }
  
  const backgroundColor = getBandColor(data.pmf);
  const opacity = 0.5 + (data.confidence / 100) * 0.5;  // Confidence affects opacity
  
  return (
    <div 
      className={`pmf-cell ${selected ? 'selected' : ''}`}
      style={{ 
        backgroundColor, 
        opacity,
        borderColor: selected ? '#000' : 'transparent',
      }}
      onClick={onClick}
      title={`${data.market} × ${data.technology}\nPMF: ${data.pmf.toFixed(1)}\nConfidence: ${data.confidence.toFixed(0)}%`}
    >
      <div className="cell-pmf">{data.pmf.toFixed(1)}</div>
      <div className="cell-confidence">{getConfidenceBadge(data.confidence)}</div>
    </div>
  );
}

/**
 * Cell Drill-Down View
 */
function DrillDownPanel({ data, onClose }) {
  if (!data) return null;
  
  return (
    <div className="drill-down-overlay">
      <div className="drill-down-panel">
        <button className="close-btn" onClick={onClose}>✕</button>
        
        <h2>{data.market}</h2>
        <h3>{data.technology}</h3>
        
        <div className="drill-down-content">
          {/* PMF Score Breakdown */}
          <section className="score-breakdown">
            <h4>PMF Score: {data.pmf.toFixed(1)}/100</h4>
            <div className="component-scores">
              <div className="component">
                <label>Desirability (30%)</label>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{ width: `${data.desirability}%`, backgroundColor: '#4caf50' }}
                  />
                </div>
                <span>{data.desirability.toFixed(0)}</span>
              </div>
              
              <div className="component">
                <label>Feasibility (30%)</label>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{ width: `${data.feasibility}%`, backgroundColor: '#2196f3' }}
                  />
                </div>
                <span>{data.feasibility.toFixed(0)}</span>
              </div>
              
              <div className="component">
                <label>Viability (25%)</label>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{ width: `${data.viability}%`, backgroundColor: '#ff9800' }}
                  />
                </div>
                <span>{data.viability.toFixed(0)}</span>
              </div>
              
              <div className="component">
                <label>Risk Penalty (15%)</label>
                <div className="score-bar">
                  <div 
                    className="score-fill" 
                    style={{ width: `${data.risk}%`, backgroundColor: '#f44336' }}
                  />
                </div>
                <span>{data.risk.toFixed(0)}</span>
              </div>
            </div>
          </section>
          
          {/* Confidence & Recommendation */}
          <section className="confidence-section">
            <h4>Confidence: {data.confidence.toFixed(0)}%</h4>
            <p className="recommendation">
              {data.confidence >= 70 && "High confidence - suitable for resource allocation"}
              {data.confidence < 70 && data.confidence >= 40 && "Medium confidence - usable with caveats, refine with targeted evidence"}
              {data.confidence < 40 && "Low confidence - highly uncertain, prioritize evidence acquisition"}
            </p>
          </section>
          
          {/* Evidence Summary */}
          <section className="evidence-section">
            <h4>Evidence Summary</h4>
            <p className="evidence-note">
              Evidence would be loaded from agent4_audit_trail.json in production.
              Example evidence items would appear here with source, date, and contribution.
            </p>
          </section>
          
          {/* Action Items */}
          <section className="actions">
            <h4>Recommended Action</h4>
            <div className="action-buttons">
              <button className="action-btn invest">Invest</button>
              <button className="action-btn accelerate">Accelerate</button>
              <button className="action-btn monitor">Monitor</button>
              <button className="action-btn pause">Pause</button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

/**
 * Summary Statistics
 */
function SummaryStats({ data }) {
  const highPMF = data.filter(d => d.pmf >= 70).length;
  const highConfidence = data.filter(d => d.confidence >= 70).length;
  const avgPMF = (data.reduce((sum, d) => sum + d.pmf, 0) / data.length).toFixed(1);
  const avgConfidence = (data.reduce((sum, d) => sum + d.confidence, 0) / data.length).toFixed(1);
  const interesting = data.filter(d => d.pmf >= 60 && d.confidence < 50).length;
  
  return (
    <div className="summary-stats">
      <div className="stat">
        <div className="stat-value">{highPMF}</div>
        <div className="stat-label">High PMF (70+)</div>
      </div>
      <div className="stat">
        <div className="stat-value">{highConfidence}</div>
        <div className="stat-label">High Confidence (70+)</div>
      </div>
      <div className="stat">
        <div className="stat-value">{avgPMF}</div>
        <div className="stat-label">Average PMF</div>
      </div>
      <div className="stat">
        <div className="stat-value">{avgConfidence}</div>
        <div className="stat-label">Average Confidence</div>
      </div>
      <div className="stat highlight">
        <div className="stat-value">{interesting}</div>
        <div className="stat-label">High Potential / Low Confidence</div>
      </div>
    </div>
  );
}

/**
 * Main Dashboard Component
 */
export default function PMFDashboard({ onLogout }) {
  const [pmfData, setPmfData] = useState(SAMPLE_PMF_DATA);
  const [selectedCell, setSelectedCell] = useState(null);
  const [filterConfidence, setFilterConfidence] = useState('all');
  const [filterPMF, setFilterPMF] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load data from backend API
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const token = localStorage.getItem('authToken');
        const response = await fetch('http://localhost:5001/api/pmf/scores', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to load PMF data from backend');
        }

        const result = await response.json();

        if (result.data && result.data.length > 0) {
          // Use backend data
          setPmfData(result.data);
          console.log(`Loaded ${result.data.length} PMF scores from backend`);
        } else {
          console.log('Using sample data (backend returned empty)');
        }
      } catch (err) {
        console.warn('Could not load from backend, using sample data:', err.message);
        setError(err.message);
        // Keep using sample data if backend is not available
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);
  
  // Extract unique markets and techs
  const markets = useMemo(() => extractUnique(pmfData, 'market'), [pmfData]);
  const technologies = useMemo(() => extractUnique(pmfData, 'technology'), [pmfData]);
  
  // Build data lookup
  const dataLookup = useMemo(() => {
    const lookup = {};
    pmfData.forEach(item => {
      lookup[`${item.market}|${item.technology}`] = item;
    });
    return lookup;
  }, [pmfData]);
  
  // Apply filters
  const getFilteredData = () => {
    return pmfData.filter(item => {
      if (filterConfidence !== 'all') {
        if (filterConfidence === 'high' && item.confidence < 70) return false;
        if (filterConfidence === 'medium' && (item.confidence < 40 || item.confidence >= 70)) return false;
        if (filterConfidence === 'low' && item.confidence >= 40) return false;
      }
      
      if (filterPMF !== 'all') {
        if (filterPMF === 'high' && item.pmf < 70) return false;
        if (filterPMF === 'medium' && (item.pmf < 55 || item.pmf >= 70)) return false;
        if (filterPMF === 'low' && item.pmf >= 55) return false;
      }
      
      return true;
    });
  };
  
  const filteredData = useMemo(() => getFilteredData(), [pmfData, filterConfidence, filterPMF]);
  
  return (
    <div className="pmf-dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Product-Market Fit Heat Map</h1>
          <p>Sustainable Packaging Innovation Portfolio (US & Canada)</p>
          <p className="timestamp">Last Updated: {new Date().toLocaleDateString()} at {new Date().toLocaleTimeString()}</p>
        </div>
        {onLogout && (
          <button
            className="logout-button"
            onClick={onLogout}
            title="Logout from the dashboard"
          >
            🚪 Logout
          </button>
        )}
      </header>
      
      {/* Summary Statistics */}
      <SummaryStats data={pmfData} />
      
      {/* Filters */}
      <div className="filters">
        <div className="filter-group">
          <label>Filter by PMF Score:</label>
          <select value={filterPMF} onChange={(e) => setFilterPMF(e.target.value)}>
            <option value="all">All</option>
            <option value="high">High (70+)</option>
            <option value="medium">Medium (55-70)</option>
            <option value="low">Low (0-55)</option>
          </select>
        </div>
        
        <div className="filter-group">
          <label>Filter by Confidence:</label>
          <select value={filterConfidence} onChange={(e) => setFilterConfidence(e.target.value)}>
            <option value="all">All</option>
            <option value="high">High (70+)</option>
            <option value="medium">Medium (40-70)</option>
            <option value="low">Low (0-40)</option>
          </select>
        </div>
      </div>
      
      {/* Heat Map Legend */}
      <div className="legend">
        <div className="legend-section">
          <h4>PMF Score (Color)</h4>
          <div className="legend-items">
            {COLOR_SCHEME.pmfBands.map(band => (
              <div key={band.label} className="legend-item">
                <div 
                  className="legend-color" 
                  style={{ backgroundColor: band.color }}
                />
                <span>{band.label}: {band.min}-{band.max}</span>
              </div>
            ))}
          </div>
        </div>
        
        <div className="legend-section">
          <h4>Confidence Level (Opacity & Stars)</h4>
          <div className="legend-items">
            <div className="legend-item">
              <span>★★★ High Confidence (70-100)</span>
            </div>
            <div className="legend-item">
              <span>★★☆ Medium Confidence (40-70)</span>
            </div>
            <div className="legend-item">
              <span>★☆☆ Low Confidence (0-40)</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Heat Map Matrix */}
      <div className="heat-map-container">
        <div className="heat-map">
          {/* Column Headers (Technologies) */}
          <div className="header-row">
            <div className="header-cell corner" />
            {technologies.map(tech => (
              <div key={tech} className="header-cell tech-header">
                {tech}
              </div>
            ))}
          </div>
          
          {/* Rows (Markets) */}
          {markets.map(market => (
            <div key={market} className="data-row">
              <div className="row-header market-header">{market}</div>
              
              {technologies.map(tech => {
                const data = dataLookup[`${market}|${tech}`];
                const show = !filteredData || filteredData.some(d => d.market === market && d.technology === tech);
                
                return (
                  <div 
                    key={`${market}|${tech}`}
                    className={show ? '' : 'hidden'}
                  >
                    <PMFCell 
                      data={data}
                      selected={selectedCell?.market === market && selectedCell?.technology === tech}
                      onClick={() => setSelectedCell(data)}
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      
      {/* High Potential / Low Confidence Section */}
      <section className="interesting-opportunities">
        <h3>⚡ High Potential / Low Confidence Cells (Need More Evidence)</h3>
        <p>These cells show promise (PMF 60+) but lack sufficient evidence. These are priority targets for evidence acquisition.</p>
        <div className="opportunity-list">
          {pmfData
            .filter(d => d.pmf >= 60 && d.confidence < 50)
            .sort((a, b) => b.pmf - a.pmf)
            .map(item => (
              <div key={`${item.market}|${item.technology}`} className="opportunity-card">
                <h4>{item.market}</h4>
                <p className="tech-name">{item.technology}</p>
                <div className="opportunity-scores">
                  <span className="pmf">PMF: {item.pmf.toFixed(1)}</span>
                  <span className="confidence">Confidence: {item.confidence.toFixed(0)}%</span>
                </div>
                <p className="action">→ Acquire more evidence</p>
              </div>
            ))}
        </div>
      </section>
      
      {/* Drill-Down Panel */}
      <DrillDownPanel 
        data={selectedCell}
        onClose={() => setSelectedCell(null)}
      />
    </div>
  );
}
