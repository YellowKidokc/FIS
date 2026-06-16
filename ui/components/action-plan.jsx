export function ActionPlanPreview({ plan }) {
  return <pre className="action-plan-preview">{JSON.stringify(plan || { dry_run: true }, null, 2)}</pre>;
}
