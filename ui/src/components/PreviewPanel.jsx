import React from 'react';
import { getExportUrl } from '../services/api';
import ExportControls from './ExportControls';

const PreviewPanel = ({ renderUrl, status, projectId }) => {
  const isGenerating = status === 'STARTING' || status === 'RUNNING';
  
  const getRenderState = () => {
    if (status === 'FAILED') return 'FAILED';
    if (renderUrl) return 'AVAILABLE';
    if (isGenerating) return 'LOADING';
    return 'NO_RENDER';
  };

  const renderState = getRenderState();

  return (
    <div className="panel" style={{ minHeight: '300px' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>3D Preview</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button style={{ padding: '4px 8px', fontSize: '11px' }} disabled={!projectId || isGenerating}>Regenerate</button>
          <ExportControls projectId={projectId} isGenerating={isGenerating} />
        </div>
      </div>
      <div style={{ 
        flex: 1, 
        backgroundColor: 'var(--bg-primary)', 
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-secondary)',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {renderState === 'AVAILABLE' && (
          <img 
            src={renderUrl} 
            alt="Blender Render" 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
          />
        )}
        
        {renderState === 'LOADING' && <span>Rendering in progress...</span>}
        
        {renderState === 'NO_RENDER' && <span>No model generated</span>}
        
        {renderState === 'FAILED' && <span style={{ color: 'var(--accent-danger)' }}>Render Failed</span>}
      </div>
    </div>
  );
};

export default PreviewPanel;
