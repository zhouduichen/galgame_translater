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

export function applyChoiceEffects(
  variables: StoryVariables,
  effects: Record<string, string | number | boolean> = {},
): StoryVariables {
  return {
    ...variables,
    ...effects,
  };
}
