import { beforeEach, describe, expect, it } from "vitest";
import { usePlayerStore } from "./playerStore";
import type { Project } from "@/lib/types";

const transitionProject: Project = {
  project_id: "proj_transition",
  title: "Transition",
  author: "",
  characters: {},
  asset_resources: {},
  variables: [],
  start_scene_id: "scene_1",
  created_at: "",
  updated_at: "",
  version: 1,
  scenes: {
    scene_1: {
      scene_id: "scene_1",
      title: "One",
      description: "",
      nodes: {
        n1: {
          type: "scene_transition",
          node_id: "n1",
          target_scene_id: "scene_2",
          effect: "fade",
        },
      },
    },
    scene_2: {
      scene_id: "scene_2",
      title: "Two",
      description: "",
      nodes: {
        s2_start: { type: "narration", node_id: "s2_start", text: "Arrived" },
      },
    },
  },
};

describe("playerStore scene transitions", () => {
  beforeEach(() => {
    usePlayerStore.setState({
      project: null,
      scene: null,
      node: null,
      history: [],
      status: "loading",
      storyState: null,
      textSpeed: 40,
      autoMode: false,
      uiMenuOpen: false,
    });
  });

  it("loads the target scene first node when changing scenes", () => {
    usePlayerStore.getState().loadProject(transitionProject);
    usePlayerStore.getState().changeScene("scene_2");

    const state = usePlayerStore.getState();
    expect(state.scene?.scene_id).toBe("scene_2");
    expect(state.node?.node_id).toBe("s2_start");
    expect(state.status).toBe("playing");
  });
});
