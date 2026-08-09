import React from 'react';

const formatDuration = (start, end) => {
  if (!start || !end || start === end) return null;
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  const diff = (e - s) / 1000;
  return diff >= 1 ? `${diff.toFixed(1)}s` : '<1s';
};

const AgentStep = ({ stage, isLast }) => {
  const isCompleted = stage.status === 'COMPLETED' || stage.status === 'REVIEW_REQUIRED';
  const isFailed = stage.status === 'FAILED';
  const isRunning = stage.status === 'RUNNING' || stage.status === 'STARTING';
  const isRepair = stage.isRepairLoop;

  let icon = '○';
  let color = 'var(--text-secondary)';
  if (isCompleted) {
    icon = '✓';
    color = 'var(--status-success)';
  } else if (isFailed) {
    icon = '✗';
    color = 'var(--status-danger)';
  } else if (isRunning) {
    icon = '⟳';
    color = 'var(--accent-primary)';
  }

  // Make repair loop distinct
  const bgColor = isRepair ? 'rgba(255, 170, 0, 0.05)' : 'transparent';
  const borderColor = isRepair ? 'rgba(255, 170, 0, 0.2)' : 'transparent';

  const duration = formatDuration(stage.startTime, stage.endTime);

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      
      {/* Step Box */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-start', 
        gap: '12px', 
        padding: '10px', 
        backgroundColor: bgColor,
        border: `1px solid ${borderColor}`,
        borderRadius: '6px'
      }}>
        <div style={{ width: '20px', textAlign: 'center', fontSize: '16px', color, marginTop: '2px' }}>
          {icon}
        </div>
        
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{stage.name}</span>
            {duration && (
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{duration}</span>
            )}
          </div>
          
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {stage.description || (isRunning ? 'Processing...' : 'Completed')}
          </div>
        </div>
      </div>

      {/* Down Arrow */}
      {!isLast && (
        <div style={{ 
          height: '20px', 
          marginLeft: '20px',
          borderLeft: `2px dashed ${isRepair ? 'var(--status-warning)' : 'var(--border-color)'}`,
          opacity: 0.5
        }} />
      )}
    </div>
  );
};

export default AgentStep;
