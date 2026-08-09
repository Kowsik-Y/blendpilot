import React from 'react';
import SystemStatus from './SystemStatus';

const Header = () => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '16px 24px',
      backgroundColor: 'var(--bg-panel)',
      borderBottom: '1px solid var(--border-color)',
    }}>
      <div>
        <h1 style={{ fontSize: '20px', margin: 0, color: 'var(--accent-primary)' }}>BlendPilot AI</h1>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Self-Correcting Agentic AI Copilot for Blender</div>
      </div>
      <SystemStatus />
    </div>
  );
};

export default Header;
