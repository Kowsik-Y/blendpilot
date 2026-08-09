const BASE_URL = 'http://localhost:8000';

export const generateModel = async (prompt, overrides = {}, enableHumanInterrupt = true) => {
  const response = await fetch(`${BASE_URL}/api/workflow/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_prompt: prompt,
      reference_images: [],
      overrides: overrides,
      enable_human_interrupt: enableHumanInterrupt
    })
  });
  
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to start generation: ${err}`);
  }
  
  return await response.json();
};

export const getRunStatus = async (sessionId) => {
  const response = await fetch(`${BASE_URL}/api/workflow/${sessionId}/status`);
  
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to get run status: ${err}`);
  }
  
  return await response.json();
};

export const submitFeedback = async (sessionId, action, feedbackText = null) => {
  const response = await fetch(`${BASE_URL}/api/workflow/${sessionId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: action,
      feedback_text: feedbackText
    })
  });
  
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to submit feedback: ${err}`);
  }
  
  return await response.json();
};

export const getRenderUrl = (projectId) => {
  if (!projectId) return null;
  return `${BASE_URL}/static/${projectId}/preview.png`;
};

export const getExportUrl = (projectId) => {
  if (!projectId) return null;
  return `${BASE_URL}/api/export/${projectId}/download`;
};

export const getStreamUrl = (sessionId) => {
  if (!sessionId) return null;
  return `${BASE_URL}/api/workflow/${sessionId}/stream`;
};
