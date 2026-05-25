import { beforeEach, describe, expect, it, vi } from "vitest";
import { useEditorStore } from "./editorStore";
import type { Project } from "@/lib/types";

const project: Project = {
  project_id: "proj_editor",
  title: "Editor Test",
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
      title: "Scene",
      description: "",
      nodes: {
        n1: { type: "narration", node_id: "n1", text: "One", next_node_id: "n2" },
        n2: { type: "narration", node_id: "n2", text: "Two" },
      },
    },
  },
};

describe("editorStore", () => {
  beforeEach(() => {
    useEditorStore.setState({
      project: null,
      currentSceneId: null,
      selectedNodeId: null,
      dirty: false,
    });
    vi.restoreAllMocks();
  });

  it("loads the explicit start scene", () => {
    useEditorStore.getState().loadProject(project);

    expect(useEditorStore.getState().currentSceneId).toBe("scene_1");
  });

  it("marks project dirty after editing a node", () => {
    useEditorStore.getState().loadProject(project);
    useEditorStore.getState().updateNode("n1", { text: "Changed" });

    const updated = useEditorStore.getState().project;
    expect(updated?.scenes.scene_1.nodes.n1).toMatchObject({ text: "Changed" });
    expect(useEditorStore.getState().dirty).toBe(true);
  });

  it("persists through the shared API helper", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    useEditorStore.getState().loadProject(project);
    await useEditorStore.getState().saveProject();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/proj_editor",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(useEditorStore.getState().dirty).toBe(false);
  });
});
