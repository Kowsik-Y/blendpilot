import React, { useState } from 'react';
import { getExportUrl } from '../services/api';

const ExportControls = ({ projectId, isGenerating }) => {
  const [isExporting, setIsExporting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleExport = async () => {
    if (!projectId || isGenerating) return;
    
    setIsExporting(true);
    setError(null);
    setSuccess(false);
    
    try {
      const url = getExportUrl(projectId);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Backend failed to package the asset bundle.');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${projectId}_bundle.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 3000);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
      {success && <span style={{ color: 'var(--status-success)', fontSize: '11px' }}>✓ Exported!</span>}
      {error && <span style={{ color: 'var(--status-danger)', fontSize: '11px' }}>✗ Failed</span>}
      <button 
        style={{ padding: '4px 8px', fontSize: '11px' }} 
        onClick={handleExport} 
        disabled={!projectId || isGenerating || isExporting}
      >
        {isExporting ? 'Downloading...' : 'Export Bundle (.zip)'}
      </button>
    </div>
  );
};

export default ExportControls;
