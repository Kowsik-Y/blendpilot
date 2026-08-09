import React, { useState } from 'react';

const SceneObjects = ({ scene }) => {
  const [expanded, setExpanded] = useState({});

  if (!scene) {
    return (
      <div className="panel flex-1">
        <div className="panel-header">Scene Objects</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>No scene data...</div>
      </div>
    );
  }

  const objects = scene.objects || [];

  const toggleExpand = (idx) => {
    setExpanded(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  const formatVec3 = (vec) => {
    if (!vec) return 'N/A';
    // Handle array or object
    if (Array.isArray(vec)) {
      return `[${vec.map(v => v.toFixed(2)).join(', ')}]`;
    }
    return `[${(vec.x || 0).toFixed(2)}, ${(vec.y || 0).toFixed(2)}, ${(vec.z || 0).toFixed(2)}]`;
  };

  return (
    <div className="panel flex-1" style={{ minHeight: '200px', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">Scene Objects</div>
      <div className="scrollable" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {objects.map((obj, idx) => {
          const isExpanded = !!expanded[idx];
          
          return (
            <div key={idx} style={{ padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px', fontSize: '13px' }}>
              <div 
                style={{ fontWeight: 600, marginBottom: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                onClick={() => toggleExpand(idx)}
              >
                <span style={{ display: 'inline-block', width: '16px' }}>{isExpanded ? '▾' : '▸'}</span>
                <span>{obj.name || 'Unnamed Object'}</span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-secondary)', fontSize: '11px', backgroundColor: 'var(--bg-primary)', padding: '2px 6px', borderRadius: '4px' }}>
                  {obj.type || 'UNKNOWN'}
                </span>
              </div>
              
              {isExpanded && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', color: 'var(--text-secondary)', fontSize: '12px', paddingLeft: '16px', marginTop: '8px' }}>
                  {obj.polygon_count !== undefined && (
                    <div><strong>Polygons:</strong> {obj.polygon_count}</div>
                  )}
                  {obj.materials && obj.materials.length > 0 && (
                    <div><strong>Materials:</strong> {obj.materials.join(', ')}</div>
                  )}
                  {obj.dimensions && (
                    <div><strong>Dimensions:</strong> {formatVec3(obj.dimensions)}</div>
                  )}
                  {obj.position && (
                    <div><strong>Location:</strong> {formatVec3(obj.position)}</div>
                  )}
                  {obj.rotation && (
                    <div><strong>Rotation:</strong> {formatVec3(obj.rotation)}</div>
                  )}
                  {obj.scale && (
                    <div><strong>Scale:</strong> {formatVec3(obj.scale)}</div>
                  )}
                  {obj.modifiers && obj.modifiers.length > 0 && (
                    <div><strong>Modifiers:</strong> {obj.modifiers.map(m => (typeof m === 'string' ? m : m.name)).join(', ')}</div>
                  )}
                  {obj.validation_status && (
                    <div><strong>Status:</strong> {obj.validation_status}</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {objects.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Scene is empty.</div>
        )}
      </div>
    </div>
  );
};

export default SceneObjects;
