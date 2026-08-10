import React, { useEffect, useRef } from 'react';

const ActivityLog = ({ logs = [] }) => {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="panel flex-1" style={{ minHeight: '200px' }}>
      <div className="panel-header">Activity Log</div>
      <div className="scrollable" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {logs.map((log, idx) => {
          // Map backend event fields and format the timestamp
          const timeStr = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : log.time;
          const agentName = log.agent_name || log.agent;
          const message = log.step_description || log.msg;

          return (
            <div key={idx} style={{ fontSize: '12px', paddingBottom: '8px', borderBottom: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--text-secondary)', marginBottom: '2px' }}>{timeStr}</div>
              <div style={{ fontWeight: 600, color: 'var(--accent-primary)', marginBottom: '2px' }}>{agentName}</div>
              <div style={{ color: 'var(--text-primary)' }}>{message}</div>
            </div>
          );
        })}
        {logs.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '12px', fontStyle: 'italic' }}>
            System idle...
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
};

export default ActivityLog;
