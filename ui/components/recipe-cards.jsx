export function RecipeCard({ recipe, onBuild, onSkip }) {
  if (!recipe) return <div className="story-recipe-card muted">No recommendation yet.</div>;
  return (
    <article className="story-recipe-card">
      <p className="eyebrow">Recommended Next Action</p>
      <h3>{recipe.title}</h3>
      <p>{recipe.one_sentence}</p>
      <div className="story-pills">
        <span>confidence {Math.round(recipe.confidence * 100)}%</span>
        <span>risk {recipe.risk}</span>
        <span>{recipe.primitives.join(' → ')}</span>
      </div>
      <p className="why">{recipe.reason}</p>
      <button onClick={() => onBuild?.(recipe)}>Build Storyboard</button>
      <button className="ghost" onClick={() => onSkip?.(recipe)}>Not now</button>
    </article>
  );
}
