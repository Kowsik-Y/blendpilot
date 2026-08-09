import React from 'react';
import Header from '../components/Header';
import PromptPanel from '../components/PromptPanel';
import AgentWorkflow from '../components/AgentWorkflow';
import PreviewPanel from '../components/PreviewPanel';
import GeometryQA from '../components/GeometryQA';
import VisionQA from '../components/VisionQA';
import SceneObjects from '../components/SceneObjects';
import RepairPanel from '../components/RepairPanel';
import ActivityLog from '../components/ActivityLog';
import FeedbackInput from '../components/FeedbackInput';
import { useGeneration } from '../hooks/useGeneration';

const Dashboard = () => {
  const { state, startGeneration, resumeGeneration } = useGeneration();

  return (
    <div className="dashboard-layout">
      <Header status={state.status} error={state.error} />
      
      <div className="dashboard-content">
        {/* Left Column */}
        <div className="left-column scrollable">
          <PromptPanel 
            status={state.status}
            runId={state.runId}
            iteration={state.iteration}
            onStart={(prompt) => startGeneration(prompt)} 
          />
          <GeometryQA qa={state.geometryQA} />
          <VisionQA qa={state.visionQA} />
        </div>

        {/* Center Column */}
        <div className="center-column scrollable">
          <PreviewPanel 
            renderUrl={state.render} 
            status={state.status} 
            projectId={state.projectId}
          />
          <div className="row flex-1">
            <SceneObjects scene={state.sceneState} />
            <RepairPanel 
              repair={state.repair} 
              iteration={state.iteration} 
              maxIterations={state.maxIterations} 
              status={state.status}
              geometryQA={state.geometryQA}
              visionQA={state.visionQA}
            />
          </div>
          <FeedbackInput 
            sessionId={state.runId} 
            status={state.status}
            onFeedbackSubmitted={() => resumeGeneration()}
          />
        </div>

        {/* Right Column */}
        <div className="right-column scrollable">
          <AgentWorkflow 
            currentNode={state.currentNode} 
            status={state.status}
            events={state.activityLog}
          />
          <ActivityLog logs={state.activityLog} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
