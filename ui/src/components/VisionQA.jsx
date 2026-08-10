import React from 'react';

const VisionQA = ({ qa }) => {
  if (!qa || !qa.overall_result) {
    return (
      <div className="panel" style={{ flex: 1 }}>
        <div className="panel-header">Vision QA</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Awaiting vision critique...</div>
      </div>
    );
  }

  const {
    object_presence,
    required_component_presence,
    color_match,
    approximate_shape_match,
    obvious_visual_errors = [],
    confidence = 0,
    overall_result
  } = qa;

  const passed = overall_result === 'PASS';
  const overallStatus = passed ? 'PASSED' : 'REPAIR REQUIRED';
  const statusColor = passed ? 'var(--status-success)' : 'var(--status-danger)';
  
  const toPercent = (val) => `${Math.round(val * 100)}%`;

  const renderCheck = (label, isPassed) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
      <span style={{ color: 'var(--text-primary)' }}>{label}</span>
      <span style={{ color: isPassed ? 'var(--status-success)' : 'var(--status-danger)', fontWeight: 600 }}>
        {isPassed ? '✓' : '✗'}
      </span>
    </div>
  );

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">Vision QA</div>
      
      <div className="scrollable" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
        
        {/* Scores */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
          <div style={{ padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginBottom: '2px' }}>Confidence Score</div>
            <div style={{ fontWeight: 600, fontSize: '16px' }}>{toPercent(confidence)}</div>
          </div>
        </div>

        {/* Checks */}
        <div style={{ padding: '12px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px' }}>
          {renderCheck('Object Presence', object_presence)}
          {renderCheck('Components Match', required_component_presence)}
          {renderCheck('Color Match', color_match)}
          {renderCheck('Shape Match', approximate_shape_match)}
        </div>

        {/* Issues */}
        {obvious_visual_errors.length > 0 && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: '4px', color: 'var(--status-danger)' }}>Issues Detected:</div>
            <ul style={{ margin: 0, paddingLeft: '16px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {obvious_visual_errors.map((issue, idx) => (
                <li key={idx}>{issue}</li>
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
