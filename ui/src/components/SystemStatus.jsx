import React from 'react';

const SystemStatus = () => {
  return (
    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-success)' }}></div>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Backend Connected</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-success)' }}></div>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Blender Connected</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-success)' }}></div>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>AI Ready</span>
      </div>
    </div>
  );
};

export default SystemStatus;
