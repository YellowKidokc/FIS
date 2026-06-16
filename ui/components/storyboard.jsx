export function StoryboardView({ storyboard, onApprove, onEdit, onSkip, onDefer }) {
  if (!storyboard) return <div className="storyboard-card">Build a storyboard to preview River's recommendation.</div>;
  const safety = storyboard.safety || {};
  return (
    <section className="storyboard-card">
      <p className="eyebrow">Story Mode</p>
      <h2>{storyboard.title}</h2>
      <p>{storyboard.subtitle}</p>
      <ol className="story-progress">
        {(storyboard.story_steps || []).map(step => <li key={step.step_id}><b>{step.title}</b> — {step.sentence}</li>)}
      </ol>
      <div className="story-safety"><b>Safety:</b> {safety.risk || storyboard.risk}</div>
      <div className="story-actions">
        <button onClick={() => onApprove?.(storyboard)}>Approve plan</button>
        <button className="ghost" onClick={() => onEdit?.(storyboard)}>Edit plan</button>
        <button className="ghost" onClick={() => onSkip?.(storyboard)}>Skip</button>
        <button className="ghost" onClick={() => onDefer?.(storyboard)}>Defer</button>
      </div>
    </section>
  );
}
