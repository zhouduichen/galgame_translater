import { create } from "zustand";
import type { Project, Scene, StoryNode } from "@/lib/types";
import { getFirstNodeId } from "@/lib/types";

export type PlayerStatus = "loading" | "playing" | "waiting_choice" | "transitioning" | "ended" | "error";

export type PlayerState = {
  project: Project | null;
  scene: Scene | null;
  node: StoryNode | null;
  history: StoryNode[];
  status: PlayerStatus;
  textSpeed: number; // ms per character
  autoMode: boolean;
  uiMenuOpen: boolean;

  // Actions
  loadProject: (p: Project) => void;
  goTo: (node: StoryNode) => void;
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
  textSpeed: 40,
  autoMode: false,
  uiMenuOpen: false,

  loadProject: (project) => {
    const firstScene = Object.values(project.scenes)[0];
    if (!firstScene) {
      set({ project, status: "error" });
      return;
    }
    const firstId = getFirstNodeId(firstScene);
    const firstNode = firstId ? firstScene.nodes[firstId] : null;
    set({
      project,
      scene: firstScene,
      node: firstNode,
      history: [],
      status: firstNode ? "playing" : "error",
    });
  },

  goTo: (node) => {
    const { node: current, scene } = get();
    if (!scene) return;
    set((s) => ({
      history: current ? [...s.history, current] : s.history,
      node,
      status: node.type === "choice" ? "waiting_choice" : node.type === "ending" ? "ended" : node.type === "scene_transition" ? "transitioning" : "playing",
    }));
    // Auto-trigger scene transition
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
    const firstId = getFirstNodeId(scene);
    const firstNode = firstId ? scene.nodes[firstId] : null;
    set({
      scene,
      node: firstNode,
      history: [],
      status: firstNode ? "playing" : "error",
    });
  },

  restartScene: () => {
    const { scene } = get();
    if (!scene) return;
    const firstId = getFirstNodeId(scene);
    const firstNode = firstId ? scene.nodes[firstId] : null;
    set({
      node: firstNode,
      history: [],
      status: firstNode ? "playing" : "error",
    });
  },

  setTextSpeed: (speed) => set({ textSpeed: speed }),
  toggleAutoMode: () => set((s) => ({ autoMode: !s.autoMode })),
  setUiMenuOpen: (open) => set({ uiMenuOpen: open }),
}));
