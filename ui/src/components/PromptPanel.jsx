import React, { useState } from 'react';

const PromptPanel = ({ status, runId, iteration = 0, onStart }) => {
  const [prompt, setPrompt] = useState('');

  const isStarting = status === 'STARTING';
  const isRunning = status === 'RUN_STARTED';
  const isGenerating = isStarting || isRunning;
  
  const handleGenerate = () => {
    if (!prompt.trim()) return;
    onStart(prompt);
  };

  return (
    <div className="panel">
      <div className="panel-header">Prompt / Project</div>
      <textarea
        placeholder="Describe the 3D model you want to create..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={5}
        style={{ marginBottom: '12px', width: '100%', boxSizing: 'border-box' }}
        disabled={isGenerating}
      />
      <button 
        className="primary"
        onClick={handleGenerate}
        disabled={isGenerating || !prompt.trim()}
        style={{ width: '100%' }}
      >
        {isStarting ? 'Starting Workflow...' : isRunning ? (iteration > 0 ? 'Modifying existing scene...' : 'Workflow Running...') : 'Generate Model'}
      </button>

      {runId && (
        <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          Active Run ID: <span style={{ fontFamily: 'monospace' }}>{runId}</span>
        </div>
      )}
    </div>
  );
};

export default PromptPanel;
