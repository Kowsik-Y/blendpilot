import React from 'react';

const RepairPanel = ({ repair, iteration, maxIterations, status, geometryQA, visionQA }) => {
  return (
    <div className="panel flex-1" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>Repair Status</span>
        {iteration > 0 && (
          <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
            Attempt {iteration} / {maxIterations}
          </span>
        )}
      </div>
      
      {!repair || !repair.steps || repair.steps.length === 0 ? (
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          {status === 'IDLE' || status === 'STARTING' ? 'Awaiting generation...' : 'No repair required.'}
        </div>
      ) : (
        <div className="scrollable" style={{ flex: 1, fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {repair.steps.map((step, idx) => (
            <div key={idx} style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '4px' }}>
              <div style={{ marginBottom: '8px' }}>
                <strong style={{ color: 'var(--status-danger)' }}>Problem:</strong>
                <div style={{ marginTop: '2px' }}>{step.problem}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>Object: {step.affected_object}</div>
              </div>
              
              <div style={{ marginBottom: '8px' }}>
                <strong style={{ color: 'var(--accent-primary)' }}>Repair:</strong>
                <div style={{ marginTop: '2px' }}>{step.corrective_operation}</div>
                {step.reason && (
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>Reason: {step.reason}</div>
                )}
              </div>
            </div>
          ))}

          <div style={{ padding: '8px', borderTop: '1px solid var(--border-color)', marginTop: '4px' }}>
            <div style={{ fontWeight: 600, marginBottom: '8px' }}>
              Status:{' '}
              {status === 'RUNNING' ? (
                <span style={{ color: 'var(--status-warning)' }}>Running...</span>
              ) : (status === 'COMPLETED' || status === 'REVIEW_REQUIRED') ? (
                <span style={{ color: 'var(--status-success)' }}>✓ Repair completed</span>
              ) : (
                <span style={{ color: 'var(--text-secondary)' }}>{status}</span>
              )}
            </div>

            {(status === 'COMPLETED' || status === 'REVIEW_REQUIRED') && (
              <div style={{ backgroundColor: 'rgba(0,0,0,0.1)', padding: '8px', borderRadius: '4px' }}>
                <div style={{ fontWeight: 600, marginBottom: '6px' }}>Re-validation:</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span style={{ color: geometryQA?.passed ? 'var(--status-success)' : 'var(--status-danger)' }}>
                      {geometryQA?.passed ? '✓' : '✗'}
                    </span>
                    <span>Geometry QA</span>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span style={{ color: visionQA?.approved ? 'var(--status-success)' : 'var(--status-danger)' }}>
                      {visionQA?.approved ? '✓' : '✗'}
                    </span>
                    <span>Vision QA</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RepairPanel;
