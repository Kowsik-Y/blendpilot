import React from 'react';
import AgentStep from './AgentStep';

const formatDuration = (start, end) => {
  if (!start || !end) return null;
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  const diff = (e - s) / 1000;
  return diff >= 1 ? `${diff.toFixed(1)}s` : '<1s';
};

const mapNodeToDisplayName = (nodeId) => {
  const map = {
    'intent_node': 'UNDERSTAND',
    'planner_node': 'PLAN',
    'generator_node': 'GENERATE',
    'executor_node': 'EXECUTE',
    'scene_state_node': 'INSPECT',
    'geometry_qa_node': 'VALIDATE',
    'vision_critic_node': 'CRITIQUE',
    'decision_node': 'DECIDE',
    'repair_node': 'REPAIR',
    'human_review_node': 'FINAL RESULT',
    'export_node': 'EXPORT'
  };
  return map[nodeId] || nodeId;
};

const AgentWorkflow = ({ events = [], currentNode, status }) => {
  
  if (!events || events.length === 0) {
    return (
      <div className="panel" style={{ flex: 1 }}>
        <div className="panel-header">Agent Workflow</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Awaiting workflow start...</div>
      </div>
    );
  }

  // Deduplicate and group events into chronological stages
  // A new stage begins if the agent_name changes or if it's a repair loop
  const stages = [];
  let currentStage = null;

  events.forEach((evt) => {
    // If we transition to a new agent, create a new stage block
    if (!currentStage || currentStage.nodeId !== evt.agent_name) {
      if (currentStage) {
        stages.push(currentStage);
      }
      currentStage = {
        nodeId: evt.agent_name,
        name: mapNodeToDisplayName(evt.agent_name),
        status: evt.status,
        description: evt.step_description,
        startTime: evt.timestamp,
        endTime: evt.timestamp,
        isRepairLoop: evt.agent_name === 'repair_node' || evt.agent_name === 'decision_node'
      };
    } else {
      // Update existing stage (e.g. going from STARTING to COMPLETED)
      currentStage.status = evt.status;
      if (evt.step_description) currentStage.description = evt.step_description;
      currentStage.endTime = evt.timestamp;
    }
  });

  if (currentStage) {
    stages.push(currentStage);
  }

  // Add the currently active node if it's not the last event (i.e. backend hasn't emitted COMPLETED yet)
  if (currentNode && status === 'RUNNING' && stages.length > 0) {
    const lastStage = stages[stages.length - 1];
    if (lastStage.nodeId !== currentNode && lastStage.status === 'COMPLETED') {
      stages.push({
        nodeId: currentNode,
        name: mapNodeToDisplayName(currentNode),
        status: 'RUNNING',
        description: 'Executing...',
        startTime: new Date().toISOString(),
        endTime: null,
        isRepairLoop: currentNode === 'repair_node' || currentNode === 'decision_node'
      });
    }
  }

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">Agent Workflow</div>
      <div className="scrollable" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {stages.map((stage, idx) => (
          <AgentStep 
            key={`${stage.nodeId}-${idx}`} 
            stage={stage} 
            isLast={idx === stages.length - 1} 
          />
        ))}
      </div>
    </div>
  );
};

export default AgentWorkflow;
