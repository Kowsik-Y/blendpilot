import { useState, useEffect } from 'react';
import { generateModel, getStreamUrl } from '../services/api';

export const useGeneration = () => {
  const [state, setState] = useState({
    status: 'IDLE', // IDLE, STARTING, RUNNING, COMPLETED, FAILED, REVIEW_REQUIRED
    runId: null,
    projectId: null,
    prompt: '',
    error: null,
    geometryQA: null,
    visionQA: null,
    sceneState: null,
    repair: null,
    activityLog: [],
    currentNode: null,
    render: null,
    iteration: 0,
    maxIterations: 3
  });

  const startGeneration = async (promptText) => {
    if (!promptText || !promptText.trim()) return;

    setState(prev => ({
      ...prev,
      status: 'STARTING',
      error: null,
      prompt: promptText,
      runId: null,
      projectId: null,
      activityLog: [],
      currentNode: null,
    }));

    try {
      const result = await generateModel(promptText);
      setState(prev => ({
        ...prev,
        status: 'RUNNING',
        runId: result.session_id,
        projectId: result.project_id
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        status: 'FAILED',
        error: err.message
      }));
    }
  };

  const resumeGeneration = () => {
    setState(prev => ({
      ...prev,
      status: 'RUNNING',
      error: null
    }));
  };

  useEffect(() => {
    if (state.status !== 'RUNNING' || !state.runId) return;

    const url = getStreamUrl(state.runId);
    const sse = new EventSource(url);

    sse.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        setState(prev => {
          const nextState = { ...prev };
          
          if (data.node && data.node !== prev.currentNode) {
            nextState.currentNode = data.node;
          }

          if (data.state) {
            if (data.state.events) {
              nextState.activityLog = data.state.events;
            }
            if (data.state.status && data.state.status !== 'UNKNOWN') {
              nextState.status = data.state.status;
            }
            
            if (data.state.preview_image_path) {
              const urlPath = data.state.preview_image_path.replace('output/', 'static/');
              // Append timestamp to break browser cache if repair loop regenerates image
              nextState.render = `http://localhost:8000/${urlPath}?t=${Date.now()}`;
            }

            if (data.state.scene_summary) {
              nextState.sceneState = data.state.scene_summary;
            }

            if (data.state.validation_report) {
              nextState.geometryQA = data.state.validation_report;
            }

            if (data.state.vision_report) {
              nextState.visionQA = data.state.vision_report;
            }

            if (data.state.repair_plan) {
              nextState.repair = data.state.repair_plan;
            }
            
            if (data.state.iteration_count !== undefined) {
              nextState.iteration = data.state.iteration_count;
            }
          }
          
          return nextState;
        });

        // Close on terminal states
        if (data.state && ['COMPLETED', 'FAILED', 'REVIEW_REQUIRED'].includes(data.state.status)) {
          sse.close();
        }
      } catch (err) {
        console.error('Error parsing SSE event', err);
      }
    };

    sse.onerror = (err) => {
      console.error('SSE Error:', err);
      sse.close();
    };

    return () => {
      sse.close();
    };
  }, [state.runId, state.status]);

  return { state, startGeneration, resumeGeneration };
};
