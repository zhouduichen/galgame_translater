import { describe, expect, it } from "vitest";
import {
  applyChoiceEffects,
  getInitialStoryState,
  getNodeAfterChoice,
  getNextLinearNode,
} from "./storyRuntime";
import type { Project } from "./types";

const project: Project = {
  project_id: "proj_test",
  title: "Test",
  author: "",
  characters: {},
  asset_resources: {},
  variables: [
    { name: "confidence", type: "int", default: 0 },
    { name: "has_key", type: "bool", default: false },
  ],
  start_scene_id: "scene_start",
  created_at: "",
  updated_at: "",
  version: 1,
  scenes: {
    scene_start: {
      scene_id: "scene_start",
      title: "Start",
      description: "",
      nodes: {
        n1: { type: "narration", node_id: "n1", text: "Start", next_node_id: "choice" },
        choice: {
          type: "choice",
          node_id: "choice",
          text: "Choose",
          options: [
            {
              option_id: "take",
              text: "Take the key",
              next_node_id: "n2",
              effects: { confidence: 1, has_key: true },
            },
          ],
        },
        n2: { type: "narration", node_id: "n2", text: "Done" },
      },
    },
  },
};

describe("storyRuntime", () => {
  it("starts from the explicit start scene", () => {
    const state = getInitialStoryState(project);

    expect(state.currentSceneId).toBe("scene_start");
    expect(state.currentNodeId).toBe("n1");
    expect(state.variables).toEqual({ confidence: 0, has_key: false });
  });

  it("finds the next linear node", () => {
    const scene = project.scenes.scene_start;
    const next = getNextLinearNode(scene, scene.nodes.n1);

    expect(next?.node_id).toBe("choice");
  });

  it("applies choice effects without mutating previous variables", () => {
    const next = applyChoiceEffects({ confidence: 0, has_key: false }, { confidence: 1, has_key: true });

    expect(next).toEqual({ confidence: 1, has_key: true });
  });

  it("resolves a choice target node", () => {
    const scene = project.scenes.scene_start;
    const node = scene.nodes.choice;
    if (node.type !== "choice") throw new Error("expected choice node");

    const target = getNodeAfterChoice(scene, node.options[0]);

    expect(target?.node_id).toBe("n2");
  });
});
