import React from 'react';

const GeometryQA = ({ qa }) => {
  if (!qa) {
    return (
      <div className="panel" style={{ flex: 1 }}>
        <div className="panel-header">Geometry QA</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Awaiting validation...</div>
      </div>
    );
  }

  const { passed, checks = [] } = qa;
  const overallStatus = passed ? 'PASSED' : 'REPAIR REQUIRED';
  const statusColor = passed ? 'var(--status-success)' : 'var(--status-danger)';

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">Geometry QA</div>
      
      <div className="scrollable" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {checks.map((check, idx) => {
          const isCheckPassed = check.passed;
          const isWarning = !isCheckPassed && check.severity === 'WARNING';
          
          let icon = '✓';
          let color = 'var(--status-success)';
          
          if (!isCheckPassed) {
            if (isWarning) {
              icon = '⚠';
              color = 'var(--status-warning)';
            } else {
              icon = '✗';
              color = 'var(--status-danger)';
            }
          }

          return (
            <div key={idx} style={{ 
              padding: '8px', 
              backgroundColor: 'var(--bg-secondary)', 
              borderRadius: '4px', 
              fontSize: '13px',
              borderLeft: `3px solid ${color}`
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--text-primary)' }}>
                <span style={{ color }}>{icon}</span>
                <span>{check.check_name}</span>
              </div>
              
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px', paddingLeft: '20px' }}>
                {check.message}
              </div>
              
              {check.affected_objects && check.affected_objects.length > 0 && (
                <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginTop: '4px', paddingLeft: '20px' }}>
                  <strong>Affected Object(s):</strong> {check.affected_objects.join(', ')}
                </div>
              )}
            </div>
          );
        })}

        {checks.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>No checks reported.</div>
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
        <span>Overall:</span>
        <span style={{ color: statusColor }}>{overallStatus}</span>
      </div>
    </div>
  );
};

export default GeometryQA;
