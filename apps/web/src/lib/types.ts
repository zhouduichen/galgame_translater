// ─── Enums ──────────────────────────────────────────────────────────────────

export type NodeType = "dialogue" | "narration" | "choice" | "scene_transition" | "branch" | "ending";
export type Emotion = "neutral" | "happy" | "sad" | "angry" | "surprised" | "shy" | "thinking" | "crying" | "laughing";
export type Side = "left" | "right" | "center";

// ─── Asset ──────────────────────────────────────────────────────────────────

export type AssetResource = {
  id: string;
  url: string;
  asset_type: string;
  character_id?: string;
  emotion?: string;
  generator?: string;
  seed?: number;
  width: number;
  height: number;
};

// ─── Character ──────────────────────────────────────────────────────────────

export type Character = {
  character_id: string;
  name: string;
  role: string;
  description: string;
  traits: string[];
  color?: string;
  asset_ids: Record<string, string>;
};

// ─── Nodes ──────────────────────────────────────────────────────────────────

export type ChoiceOption = {
  option_id: string;
  text: string;
  next_node_id: string;
  condition?: string;
  effects?: Record<string, number | boolean | string>;
};

export type DialogueNode = {
  type: "dialogue";
  node_id: string;
  character_id: string;
  text: string;
  emotion: Emotion;
  side: Side;
  next_node_id?: string;
};

export type NarrationNode = {
  type: "narration";
  node_id: string;
  text: string;
  next_node_id?: string;
  background_id?: string;
};

export type ChoiceNode = {
  type: "choice";
  node_id: string;
  text: string;
  options: ChoiceOption[];
};

export type SceneTransitionNode = {
  type: "scene_transition";
  node_id: string;
  target_scene_id: string;
  effect: string;
  next_node_id?: string;
};

export type BranchNode = {
  type: "branch";
  node_id: string;
  condition: string;
  true_next: string;
  false_next: string;
};

export type EndingNode = {
  type: "ending";
  node_id: string;
  ending_type: "good" | "bad" | "true" | "neutral";
  epilogue: string;
};

export type StoryNode = DialogueNode | NarrationNode | ChoiceNode | SceneTransitionNode | BranchNode | EndingNode;

// ─── Scene ──────────────────────────────────────────────────────────────────

export type Scene = {
  scene_id: string;
  title: string;
  description: string;
  background_id?: string;
  nodes: Record<string, StoryNode>;
};

// Helper to safely access next_node_id on nodes that may or may not have it
function nextNodeId(n: StoryNode): string | undefined {
  return "next_node_id" in n ? (n as any).next_node_id : undefined;
}

function hasNextNode(n: StoryNode): boolean {
  return !!nextNodeId(n);
}

export function getFirstNodeId(scene: Scene): string | null {
  const targets = new Set<string>();
  for (const node of Object.values(scene.nodes)) {
    const nid = nextNodeId(node);
    if (nid) targets.add(nid);
    if (node.type === "choice") {
      for (const opt of node.options) targets.add(opt.next_node_id);
    }
    if (node.type === "branch") {
      targets.add(node.true_next);
      targets.add(node.false_next);
    }
  }
  for (const nid of Object.keys(scene.nodes)) {
    if (!targets.has(nid)) return nid;
  }
  return null;
}

export function getNodeIdsInOrder(scene: Scene): string[] {
  const ordered: string[] = [];
  let current = getFirstNodeId(scene);
  const visited = new Set<string>();
  while (current && !visited.has(current)) {
    visited.add(current);
    ordered.push(current);
    const node = scene.nodes[current];
    if (!node) break;
    if (node.type === "choice") break;
    if (node.type === "ending") break;
    if (node.type === "scene_transition") break;
    if (node.type === "branch") break;
    current = nextNodeId(node) ?? null;
  }
  return ordered;
}

// ─── Project ────────────────────────────────────────────────────────────────

export type Project = {
  project_id: string;
  title: string;
  author: string;
  characters: Record<string, Character>;
  scenes: Record<string, Scene>;
  asset_resources: Record<string, AssetResource>;
  variables: { name: string; type: string; default: string | number | boolean }[];
  created_at: string;
  updated_at: string;
  version: number;
};

// ─── Draft ──────────────────────────────────────────────────────────────────

export type ParseDraft = {
  draft_id: string;
  project_id: string;
  novel_title: string;
  synopsis: string;
  characters: Character[];
  scenes: Scene[];
};
