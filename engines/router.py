from core.models import Finding

def analyze(folderbrain, cache=None, options=None):
    return [Finding("route_keep_001", "router", "classification", "Move / keep decision", "Default route is keep in place until the user approves a plan.", confidence=0.7, risk="low", weight=7, suggested_actions=["keep_in_place", "move_as_unit", "split_folder"], evidence={"policy": "guided-review"})]
