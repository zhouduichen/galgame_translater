import { create } from "zustand";
import type { Project, Scene, StoryNode } from "@/lib/types";
import {
  applyChoiceEffects,
  getInitialStoryState,
  getNode,
  getNodeAfterChoice,
  getNextLinearNode,
  type StoryState,
} from "@/lib/storyRuntime";

export type PlayerStatus = "loading" | "playing" | "waiting_choice" | "transitioning" | "ended" | "error";

export type PlayerState = {
  project: Project | null;
  scene: Scene | null;
  node: StoryNode | null;
  history: StoryNode[];
  status: PlayerStatus;
  storyState: StoryState | null;
  textSpeed: number; // ms per character
  autoMode: boolean;
  uiMenuOpen: boolean;

  // Actions
  loadProject: (p: Project) => void;
  goTo: (node: StoryNode) => void;
  advance: () => void;
  chooseOption: (optionId: string) => void;
  goBack: () => void;
  changeScene: (sceneId: string) => void;
  restartScene: () => void;
  setTextSpeed: (speed: number) => void;
  toggleAutoMode: () => void;
  setUiMenuOpen: (open: boolean) => void;
};

export const usePlayerStore = create<PlayerState>((set, get) => ({
  project: null,
  scene: null,
  node: null,
  history: [],
  status: "loading",
  storyState: null,
  textSpeed: 40,
  autoMode: false,
  uiMenuOpen: false,

  loadProject: (project) => {
    const storyState = getInitialStoryState(project);
    const scene = project.scenes[storyState.currentSceneId] ?? null;
    const node = getNode(scene ?? undefined, storyState.currentNodeId);

    set({
      project,
      storyState,
      scene,
      node,
      history: [],
      status: node ? (node.type === "choice" ? "waiting_choice" : "playing") : "error",
    });
  },

  advance: () => {
    const { scene, node, goTo } = get();
    if (!scene || !node) return;
    const next = getNextLinearNode(scene, node);
    if (next) goTo(next);
  },

  chooseOption: (optionId) => {
    const { scene, node, storyState, goTo } = get();
    if (!scene || !node || node.type !== "choice" || !storyState) return;
    const option = node.options.find((item) => item.option_id === optionId);
    if (!option) return;

    const target = getNodeAfterChoice(scene, option);
    if (!target) return;

    set({
      storyState: {
        ...storyState,
        variables: applyChoiceEffects(storyState.variables, option.effects),
      },
    });
    goTo(target);
  },

  goTo: (node) => {
    const { node: current, scene, storyState } = get();
    if (!scene) return;
    const nextStoryState = storyState
      ? {
          ...storyState,
          currentSceneId: scene.scene_id,
          currentNodeId: node.node_id,
          visitedNodeIds: [...storyState.visitedNodeIds, node.node_id],
          history: current
            ? [...storyState.history, { sceneId: scene.scene_id, nodeId: current.node_id }]
            : storyState.history,
        }
      : null;

    set((s) => ({
      storyState: nextStoryState,
      history: current ? [...s.history, current] : s.history,
      node,
      status:
        node.type === "choice"
          ? "waiting_choice"
          : node.type === "ending"
            ? "ended"
            : node.type === "scene_transition"
              ? "transitioning"
              : "playing",
    }));

    if (node.type === "scene_transition" && node.target_scene_id) {
      setTimeout(() => get().changeScene(node.target_scene_id), 600);
    }
  },

  goBack: () => {
    const { history } = get();
    if (history.length === 0) return;
    const prev = history[history.length - 1];
    set({
      history: history.slice(0, -1),
      node: prev,
      status: "playing",
    });
  },

  changeScene: (sceneId) => {
    const { project } = get();
    if (!project) return;
    const scene = project.scenes[sceneId];
    if (!scene) return;
    const storyState = get().storyState;
    const firstNodeId = storyState?.currentNodeId ?? null;
    const firstNode = firstNodeId ? scene.nodes[firstNodeId] ?? null : null;
    set({
      scene,
      node: firstNode,
      history: [],
      status: firstNode ? "playing" : "error",
    });
  },

  restartScene: () => {
    const { scene, project } = get();
    if (!scene || !project) return;
    const storyState = getInitialStoryState(project);
    const firstNode = getNode(scene, storyState.currentNodeId);
    set({
      storyState,
      node: firstNode,
      history: [],
      status: firstNode ? "playing" : "error",
    });
  },

  setTextSpeed: (speed) => set({ textSpeed: speed }),
  toggleAutoMode: () => set((s) => ({ autoMode: !s.autoMode })),
  setUiMenuOpen: (open) => set({ uiMenuOpen: open }),
}));
