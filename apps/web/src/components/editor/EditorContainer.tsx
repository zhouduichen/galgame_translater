"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { SceneTree } from "./SceneTree";
import { NodeCard } from "./NodeCard";
import type { Project, StoryNode } from "@/lib/types";
import { getNodeIdsInOrder } from "@/lib/types";
import { api } from "@/lib/api";

type JobStatus = "pending" | "running" | "completed" | "failed";
type GenJobInfo = { job_id: string; status: JobStatus; job_type: string; error?: string | null };
type GenProgress = {
  running: boolean;
  total: number;
  completed: number;
  failed: number;
  errors: string[];
};

const NODE_TYPE_LABELS: Record<string, string> = {
  dialogue: "对白",
  narration: "旁白",
  choice: "选项",
  scene_transition: "转场",
  branch: "分支",
  ending: "结局",
};

type Props = {
  project: Project;
  onBackToPlayer: () => void;
};

export function EditorContainer({ project, onBackToPlayer }: Props) {
  const store = useEditorStore();
  const [genProgress, setGenProgress] = useState<GenProgress | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  useEffect(() => {
    store.loadProject(project);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.project_id]);

  const {
    currentSceneId,
    selectedNodeId,
    dirty,
    selectScene,
    selectNode,
    updateNode,
    addNode,
    deleteNode,
    reorderNode,
    updateChoiceOption,
    addChoiceOption,
    deleteChoiceOption,
    saveProject,
  } = store;

  const currentScene = currentSceneId ? store.project?.scenes[currentSceneId] ?? null : null;

  const orderedNodeIds = useMemo(() => {
    if (!currentScene) return [];
    const ids = getNodeIdsInOrder(currentScene);
    // Add any nodes that aren't in the linear chain (e.g., choice targets, scene transitions)
    const allIds = Object.keys(currentScene.nodes);
    const extra = allIds.filter((id) => !ids.includes(id));
    return [...ids, ...extra];
  }, [currentScene]);

  if (!currentScene) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-[var(--text-secondary)]">未选择场景</p>
      </div>
    );
  }

  const characters = store.project?.characters ?? {};

  async function handleGenerateAssets() {
    setGenProgress({ running: true, total: 0, completed: 0, failed: 0, errors: [] });

    try {
      const res = await fetch(`/api/projects/${project.project_id}/generate-assets`, { method: "POST" });
      if (!res.ok) throw new Error("提交失败");
      const data = await res.json();
      const total: number = data.count;

      setGenProgress((prev) => (prev ? { ...prev, total } : null));

      // Poll job status
      const pollInterval = setInterval(async () => {
        try {
          const jobsRes = await fetch(`/api/projects/${project.project_id}/jobs`);
          if (!jobsRes.ok) return;
          const allJobs: GenJobInfo[] = await jobsRes.json();
          const genJobs = allJobs.filter((j: GenJobInfo) => j.job_type === "generate_asset");

          let completed = 0;
          let failed = 0;
          const errors: string[] = [];

          for (const j of genJobs) {
            if (j.status === "completed") completed++;
            else if (j.status === "failed") {
              failed++;
              if (j.error) errors.push(j.error);
            }
          }

          setGenProgress((prev) => (prev ? { ...prev, completed, failed, errors } : null));

          if (completed + failed >= total) {
            clearInterval(pollInterval);
            pollingRef.current = null;

            // Refresh project to get updated asset_resources
            const updatedProject = await api.getProject(project.project_id);
            store.loadProject(updatedProject);

            if (failed === 0) {
              setTimeout(() => setGenProgress(null), 2000);
            }
          }
        } catch {
          // ignore poll errors
        }
      }, 2000);

      pollingRef.current = pollInterval;
    } catch {
      setGenProgress(null);
    }
  }

  async function handleRetryFailed() {
    await handleGenerateAssets();
  }

  function renderGenerateButton() {
    if (genProgress?.running) {
      const pct =
        genProgress.total > 0 ? `${genProgress.completed + genProgress.failed}/${genProgress.total}` : "";
      return (
        <button className="rounded bg-sakura-pink/20 px-3 py-1.5 text-xs text-sakura-pink cursor-wait" disabled>
          {genProgress.failed > 0 ? `素材生成 ${pct}` : `生成中 ${pct}`}
        </button>
      );
    }

    if (genProgress && genProgress.failed > 0) {
      return (
        <>
          <button
            className="rounded bg-[var(--bg-card)] px-3 py-1.5 text-xs text-[var(--error-red)] transition-colors hover:bg-[var(--error-red)]/10"
            onClick={handleRetryFailed}
          >
            重试失败素材
          </button>
          <span className="text-xs text-[var(--error-red)]">{genProgress.failed} 个失败</span>
        </>
      );
    }

    return (
      <button
        className="rounded bg-[var(--bg-card)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:border-sakura-pink hover:text-sakura-pink"
        onClick={handleGenerateAssets}
      >
        生成立绘/背景
      </button>
    );
  }

  return (
    <div className="flex h-screen bg-[var(--bg-deep)]">
      {/* 左侧：场景树 */}
      <div className="w-56 flex-shrink-0 border-r border-[var(--bg-border)] overflow-y-auto p-3">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--text-secondary)]">场景</h2>
          <span className="text-xs text-[var(--text-muted)]">{Object.keys(store.project?.scenes ?? {}).length}</span>
        </div>
        <SceneTree
          scenes={store.project?.scenes ?? {}}
          currentSceneId={currentSceneId}
          onSelect={selectScene}
        />
      </div>

      {/* Center: Node timeline */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">{currentScene.title}</h2>
            <p className="text-xs text-[var(--text-muted)]">{currentScene.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/studio"
              className="rounded bg-[var(--bg-card)] px-3 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:text-sakura-pink"
            >
              工作室
            </a>
            <button
              className="rounded bg-[var(--bg-card)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
              onClick={onBackToPlayer}
            >
              播放
            </button>
            {renderGenerateButton()}
            <button
              className={`rounded px-3 py-1.5 text-xs transition-colors ${
                dirty
                  ? "bg-sakura-pink text-white hover:bg-sakura-deep"
                  : "bg-[var(--bg-card)] text-[var(--text-muted)]"
              }`}
              onClick={saveProject}
              disabled={!dirty}
            >
              {dirty ? "保存" : "已保存"}
            </button>
          </div>
        </div>

        {/* Add node buttons */}
        <div className="mb-4 flex gap-2">
          {(["dialogue", "narration", "choice"] as const).map((type) => (
            <button
              key={type}
              className="rounded border border-[var(--bg-border)] bg-[var(--bg-card)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:border-sakura-pink hover:text-[var(--text-primary)]"
              onClick={() => {
                const lastNodeId = orderedNodeIds[orderedNodeIds.length - 1];
                addNode(type, lastNodeId);
              }}
            >
              + {type === "dialogue" ? "对白" : type === "narration" ? "旁白" : "选项"}
            </button>
          ))}
        </div>

        {/* Node list */}
        <div className="space-y-2">
          {orderedNodeIds.length === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--text-muted)]">这个场景还没有节点。可以先添加一个。</p>
          ) : (
            orderedNodeIds.map((nodeId, idx) => {
              const node = currentScene.nodes[nodeId];
              if (!node) return null;
              return (
                <NodeCard
                  key={nodeId}
                  node={node as StoryNode}
                  characters={characters}
                  selected={selectedNodeId === nodeId}
                  nodeIds={orderedNodeIds}
                  onSelect={() => selectNode(nodeId)}
                  onUpdate={(patch) => updateNode(nodeId, patch)}
                  onDelete={() => deleteNode(nodeId)}
                  onMoveUp={() => reorderNode(nodeId, "up")}
                  onMoveDown={() => reorderNode(nodeId, "down")}
                  isFirst={idx === 0}
                  isLast={idx === orderedNodeIds.length - 1}
                  onAddOption={
                    node.type === "choice"
                      ? () => addChoiceOption(nodeId)
                      : undefined
                  }
                  onUpdateOption={
                    node.type === "choice"
                      ? (optId, patch) => updateChoiceOption(nodeId, optId, patch)
                      : undefined
                  }
                  onDeleteOption={
                    node.type === "choice"
                      ? (optId) => deleteChoiceOption(nodeId, optId)
                      : undefined
                  }
                />
              );
            })
          )}
        </div>
      </div>

      {/* Right: Inspector / info */}
      <div className="w-64 flex-shrink-0 border-l border-[var(--bg-border)] overflow-y-auto p-3">
        <h3 className="mb-3 text-sm font-semibold text-[var(--text-secondary)]">检查器</h3>
        {selectedNodeId && currentScene.nodes[selectedNodeId] ? (
          <div className="space-y-3 text-xs text-[var(--text-secondary)]">
            <div>
              <span className="text-[var(--text-muted)]">ID:</span>{" "}
              <code className="text-sakura-pink">{selectedNodeId}</code>
            </div>
            <div>
              <span className="text-[var(--text-muted)]">类型：</span>{" "}
              <span>
                {NODE_TYPE_LABELS[currentScene.nodes[selectedNodeId].type] ?? currentScene.nodes[selectedNodeId].type}
              </span>
            </div>
            {orderedNodeIds.indexOf(selectedNodeId) >= 0 && (
              <div>
                <span className="text-[var(--text-muted)]">位置：</span>{" "}
                {orderedNodeIds.indexOf(selectedNodeId) + 1} / {orderedNodeIds.length}
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-[var(--text-muted)]">选择一个节点查看详情</p>
        )}

        <div className="mt-6">
          <h4 className="mb-2 text-xs font-semibold text-[var(--text-muted)]">节点类型</h4>
          <div className="space-y-1 text-xs text-[var(--text-muted)]">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#6688ff]" />
              对白
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#88cc88]" />
              旁白
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#ff8866]" />
              选项
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#ffcc44]" />
              转场
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#ff6688]" />
              结局
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
