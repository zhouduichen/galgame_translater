import type { ChoiceOption, Project, Scene, StoryNode } from "./types";
import { getFirstNodeId } from "./types";

export type StoryVariables = Record<string, string | number | boolean>;

export type StoryState = {
  currentSceneId: string;
  currentNodeId: string | null;
  variables: StoryVariables;
  visitedNodeIds: string[];
  history: { sceneId: string; nodeId: string }[];
};

function defaultVariableValue(type: string): string | number | boolean {
  if (type === "int" || type === "number") return 0;
  if (type === "bool" || type === "boolean") return false;
  return "";
}

export function getInitialVariables(project: Project): StoryVariables {
  return Object.fromEntries(
    project.variables.map((variable) => [
      variable.name,
      variable.default ?? defaultVariableValue(variable.type),
    ]),
  );
}

export function getInitialStoryState(project: Project): StoryState {
  const sceneId = project.start_scene_id || Object.keys(project.scenes)[0] || "";
  const scene = project.scenes[sceneId];
  const firstNodeId = scene ? getFirstNodeId(scene) : null;

  return {
    currentSceneId: sceneId,
    currentNodeId: firstNodeId,
    variables: getInitialVariables(project),
    visitedNodeIds: firstNodeId ? [firstNodeId] : [],
    history: [],
  };
}

export function getNode(scene: Scene | undefined, nodeId: string | null): StoryNode | null {
  if (!scene || !nodeId) return null;
  return scene.nodes[nodeId] ?? null;
}

export function getNextLinearNode(scene: Scene, node: StoryNode): StoryNode | null {
  if (!("next_node_id" in node) || !node.next_node_id) return null;
  return scene.nodes[node.next_node_id] ?? null;
}

export function getNodeAfterChoice(scene: Scene, option: ChoiceOption): StoryNode | null {
  return scene.nodes[option.next_node_id] ?? null;
}

/**
 * Evaluate a branch condition expression against current variables.
 * Supports simple comparisons: `variable op value`
 * where op is one of: >=, <=, !=, ==, >, <
 *
 * Returns true if the condition is met or malformed (defaults to true_next).
 */
export function evaluateBranchCondition(
  condition: string,
  variables: StoryVariables,
): boolean {
  const trimmed = condition.trim();
  if (!trimmed) return true;

  // Match patterns like "variable >= 3", "has_key == true", "name != ''"
  const match = trimmed.match(
    /^(\w+)\s*(>=|<=|!=|==|>|<)\s*(.+)$/,
  );
  if (!match) return true; // unparseable → follow true_next

  const [, varName, op, rawValue] = match;
  const actual = variables[varName];

  // Parse the RHS literal
  let expected: string | number | boolean = rawValue.trim();
  if (expected === "true") expected = true;
  else if (expected === "false") expected = false;
  else if (expected === "''" || expected === '""') expected = "";
  else {
    const num = Number(expected);
    if (!Number.isNaN(num)) expected = num;
  }

  if (typeof actual === "number" && typeof expected === "number") {
    switch (op) {
      case ">=": return actual >= expected;
      case "<=": return actual <= expected;
      case "!=": return actual !== expected;
      case "==": return actual === expected;
      case ">":  return actual > expected;
      case "<":  return actual < expected;
    }
  }

  // Fallback: compare as strings / booleans
  switch (op) {
    case "==": return actual == expected; // eslint-disable-line eqeqeq
    case "!=": return actual != expected; // eslint-disable-line eqeqeq
    default: return true;
  }
}

/**
 * Resolve a BranchNode: evaluate the condition and return the next node.
 */
export function resolveBranch(
  scene: Scene,
  node: StoryNode & { type: "branch" },
  variables: StoryVariables,
): StoryNode | null {
  const takeTrue = evaluateBranchCondition(node.condition, variables);
  const targetId = takeTrue ? node.true_next : node.false_next;
  return scene.nodes[targetId] ?? null;
}

export function applyChoiceEffects(
  variables: StoryVariables,
  effects: Record<string, string | number | boolean> = {},
): StoryVariables {
  return {
    ...variables,
    ...effects,
  };
}
