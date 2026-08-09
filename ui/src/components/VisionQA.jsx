import React from 'react';

const VisionQA = ({ qa }) => {
  if (!qa || !qa.critique_at) {
    return (
      <div className="panel" style={{ flex: 1 }}>
        <div className="panel-header">Vision QA</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Awaiting vision critique...</div>
      </div>
    );
  }

  const {
    approved,
    overall_score = 0,
    aesthetic_score = 0,
    spec_compliance_score = 0,
    strengths = [],
    issues = [],
    suggested_actions = []
  } = qa;

  const overallStatus = approved ? 'PASSED' : 'REPAIR REQUIRED';
  const statusColor = approved ? 'var(--status-success)' : 'var(--status-danger)';
  
  const toPercent = (val) => `${Math.round(val * 100)}%`;

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">Vision QA</div>
      
      <div className="scrollable" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
        
        {/* Scores */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <div style={{ padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginBottom: '2px' }}>Overall Match</div>
            <div style={{ fontWeight: 600, fontSize: '16px' }}>{toPercent(overall_score)}</div>
          </div>
          <div style={{ padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginBottom: '2px' }}>Aesthetics</div>
            <div style={{ fontWeight: 600, fontSize: '16px' }}>{toPercent(aesthetic_score)}</div>
          </div>
          <div style={{ padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px', gridColumn: '1 / span 2' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginBottom: '2px' }}>Spec Compliance</div>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{toPercent(spec_compliance_score)}</div>
          </div>
        </div>

        {/* Issues */}
        {issues.length > 0 && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: '4px', color: 'var(--status-danger)' }}>Issues Detected:</div>
            <ul style={{ margin: 0, paddingLeft: '16px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {issues.map((issue, idx) => (
                <li key={idx}>{issue}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Strengths */}
        {strengths.length > 0 && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: '4px', color: 'var(--status-success)' }}>Strengths:</div>
            <ul style={{ margin: 0, paddingLeft: '16px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {strengths.map((str, idx) => (
                <li key={idx}>{str}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Suggested Actions */}
        {suggested_actions.length > 0 && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: '4px', color: 'var(--status-warning)' }}>Suggested Actions:</div>
            <ul style={{ margin: 0, paddingLeft: '16px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {suggested_actions.map((act, idx) => (
                <li key={idx}>{act}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div style={{ 
        marginTop: '12px', 
        paddingTop: '12px', 
        borderTop: '1px solid var(--border-color)', 
        fontSize: '13px', 
        fontWeight: 600, 
        display: 'flex', 
        justifyContent: 'space-between' 
      }}>
        <span>Status:</span>
        <span style={{ color: statusColor }}>{overallStatus}</span>
      </div>
    </div>
  );
};

export default VisionQA;
