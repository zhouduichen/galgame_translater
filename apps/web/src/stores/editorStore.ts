import { create } from "zustand";
import type { Project, Scene, StoryNode, ChoiceOption } from "@/lib/types";
import { api } from "@/lib/api";

export type EditorState = {
  project: Project | null;
  currentSceneId: string | null;
  selectedNodeId: string | null;
  dirty: boolean;

  loadProject: (p: Project) => void;
  selectScene: (sceneId: string) => void;
  selectNode: (nodeId: string | null) => void;
  updateNode: (nodeId: string, patch: Partial<StoryNode>) => void;
  addNode: (type: StoryNode["type"], afterNodeId?: string) => void;
  deleteNode: (nodeId: string) => void;
  reorderNode: (nodeId: string, direction: "up" | "down") => void;
  updateChoiceOption: (nodeId: string, optionId: string, patch: Partial<ChoiceOption>) => void;
  addChoiceOption: (nodeId: string) => void;
  deleteChoiceOption: (nodeId: string, optionId: string) => void;
  saveProject: () => Promise<void>;
};

let nodeCounter = 100;

function generateNodeId(): string {
  return `node_${Date.now()}_${++nodeCounter}`;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  project: null,
  currentSceneId: null,
  selectedNodeId: null,
  dirty: false,

  loadProject: (project) => {
    const sceneId = project.start_scene_id || Object.keys(project.scenes)[0] || null;
    set({
      project,
      currentSceneId: sceneId,
      selectedNodeId: null,
      dirty: false,
    });
  },

  selectScene: (sceneId) => set({ currentSceneId: sceneId, selectedNodeId: null }),

  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  updateNode: (nodeId, patch) => {
    const { project, currentSceneId } = get();
    if (!project || !currentSceneId) return;
    const scene = project.scenes[currentSceneId];
    if (!scene || !scene.nodes[nodeId]) return;
    scene.nodes[nodeId] = { ...scene.nodes[nodeId], ...patch } as StoryNode;
    set({ project: { ...project }, dirty: true });
  },

  addNode: (type, afterNodeId) => {
    const { project, currentSceneId } = get();
    if (!project || !currentSceneId) return;
    const scene = project.scenes[currentSceneId];
    if (!scene) return;

    const nodeId = generateNodeId();
    let newNode: StoryNode;

    switch (type) {
      case "dialogue":
        newNode = { type: "dialogue", node_id: nodeId, character_id: "", text: "", emotion: "neutral", side: "center" };
        break;
      case "narration":
        newNode = { type: "narration", node_id: nodeId, text: "" };
        break;
      case "choice":
        newNode = { type: "choice", node_id: nodeId, text: "", options: [] };
        break;
      default:
        newNode = { type: "narration", node_id: nodeId, text: "" };
    }

    // Link afterNode → newNode → afterNode's old next
    if (afterNodeId && scene.nodes[afterNodeId]) {
      const prev = scene.nodes[afterNodeId];
      if ("next_node_id" in prev) {
        (newNode as any).next_node_id = (prev as any).next_node_id;
        (prev as any).next_node_id = nodeId;
      }
    }

    scene.nodes[nodeId] = newNode;
    set({ project: { ...project }, dirty: true, selectedNodeId: nodeId });
  },

  deleteNode: (nodeId) => {
    const { project, currentSceneId } = get();
    if (!project || !currentSceneId) return;
    const scene = project.scenes[currentSceneId];
    if (!scene || !scene.nodes[nodeId]) return;

    // Relink previous node
    for (const n of Object.values(scene.nodes)) {
      if ("next_node_id" in n && (n as any).next_node_id === nodeId) {
        const deleted = scene.nodes[nodeId];
        (n as any).next_node_id = "next_node_id" in deleted ? (deleted as any).next_node_id : undefined;
      }
      if (n.type === "choice") {
        for (const opt of n.options) {
          if (opt.next_node_id === nodeId) {
            const deleted = scene.nodes[nodeId];
            opt.next_node_id = "next_node_id" in deleted ? (deleted as any).next_node_id ?? "" : "";
          }
        }
      }
    }

    delete scene.nodes[nodeId];
    set({
      project: { ...project },
      dirty: true,
      selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId,
    });
  },

  reorderNode: (nodeId, direction) => {
    const { project, currentSceneId } = get();
    if (!project || !currentSceneId) return;
    const scene = project.scenes[currentSceneId];
    if (!scene || !scene.nodes[nodeId]) return;

    const ordered = Object.keys(scene.nodes);
    const idx = ordered.indexOf(nodeId);
    if (idx === -1) return;
    // Reorder by swapping next_node_id links
    // Simple approach: swap IDs in the order array and reconstruct
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= ordered.length) return;
    [ordered[idx], ordered[swapIdx]] = [ordered[swapIdx], ordered[idx]];
    // Rebuild nodes dict in new order
    const newNodes: Record<string, StoryNode> = {};
    for (const id of ordered) {
      newNodes[id] = scene.nodes[id];
    }
    scene.nodes = newNodes;
    set({ project: { ...project }, dirty: true });
  },

  updateChoiceOption: (nodeId, optionId, patch) => {
    const { project, currentSceneId } = get();
    if (!project || !currentSceneId) return;
    const scene = project.scenes[currentSceneId];
    if (!scene) return;
    const node = scene.nodes[nodeId];
    if (!node || node.type !== "choice") return;
    const opt = node.options.find((o) => o.option_id === optionId);
    if (!opt) return;
    Object.assign(opt, patch);
    set({ project: { ...project }, dirty: true });
  },

  addChoiceOption: (nodeId) => {
    const { project, currentSceneId } = get();
    if (!project || !currentSceneId) return;
    const scene = project.scenes[currentSceneId];
    if (!scene) return;
    const node = scene.nodes[nodeId];
    if (!node || node.type !== "choice") return;
    node.options.push({
      option_id: `opt_${Date.now()}`,
      text: "",
      next_node_id: "",
    });
    set({ project: { ...project }, dirty: true });
  },

  deleteChoiceOption: (nodeId, optionId) => {
    const { project, currentSceneId } = get();
    if (!project || !currentSceneId) return;
    const scene = project.scenes[currentSceneId];
    if (!scene) return;
    const node = scene.nodes[nodeId];
    if (!node || node.type !== "choice") return;
    node.options = node.options.filter((o) => o.option_id !== optionId);
    set({ project: { ...project }, dirty: true });
  },

  saveProject: async () => {
    const { project } = get();
    if (!project) return;
    await api.updateProject(project);
    set({ dirty: false });
  },
}));
