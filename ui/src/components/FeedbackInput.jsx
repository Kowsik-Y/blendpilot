import React, { useState } from 'react';
import { submitFeedback } from '../services/api';

const FeedbackInput = ({ sessionId, status, onFeedbackSubmitted }) => {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // We only allow feedback when the workflow is explicitly paused for review
  const canSubmit = status === 'REVIEW_REQUIRED' && sessionId != null;

  const handleSubmit = async () => {
    if (!feedback.trim()) return;
    
    setIsSubmitting(true);
    setError(null);
    try {
      await submitFeedback(sessionId, 'REQUEST_CHANGE', feedback);
      setFeedback('');
      if (onFeedbackSubmitted) onFeedbackSubmitted();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      await submitFeedback(sessionId, 'APPROVE');
      setFeedback('');
      if (onFeedbackSubmitted) onFeedbackSubmitted();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="panel" style={{ marginTop: 'auto' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Refine Your Model</span>
        {status === 'REVIEW_REQUIRED' && (
          <span className="badge badge-warning">Awaiting Your Review</span>
        )}
      </div>
      
      {error && (
        <div style={{ color: 'var(--accent-danger)', fontSize: '12px', marginBottom: '8px' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: '8px', opacity: canSubmit ? 1 : 0.5 }}>
        <input 
          type="text" 
          placeholder="e.g. Make the table taller and change the material to blue."
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          disabled={!canSubmit || isSubmitting}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSubmit();
          }}
        />
        <button 
          className="primary" 
          onClick={handleSubmit}
          disabled={!canSubmit || !feedback.trim() || isSubmitting}
        >
          Apply Change
        </button>
        <button 
          onClick={handleApprove}
          disabled={!canSubmit || isSubmitting}
        >
          Approve
        </button>
      </div>
    </div>
  );
};

export default FeedbackInput;
