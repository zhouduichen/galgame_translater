"use client";

import { useEffect, useState } from "react";
import { EditorContainer } from "@/components/editor/EditorContainer";
import type { Project } from "@/lib/types";

export default function EditorPage({ params }: { params: Promise<{ id: string }> }) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolvedId, setResolvedId] = useState<string | null>(null);

  useEffect(() => {
    params.then((p) => setResolvedId(p.id));
  }, [params]);

  useEffect(() => {
    if (!resolvedId) return;
    fetch(`/api/projects/${resolvedId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Project) => setProject(data))
      .catch((e) => setError(e.message));
  }, [resolvedId]);

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-deep)]">
        <div className="text-center">
          <p className="text-red-400">错误：{error}</p>
          <a href="/studio" className="mt-4 inline-block text-sm text-sakura-pink hover:underline">
            &larr; 返回项目列表
          </a>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-deep)]">
        <p className="text-[var(--text-secondary)] animate-pulse">正在加载编辑器...</p>
      </div>
    );
  }

  return (
    <EditorContainer
      project={project}
      onBackToPlayer={() => {
        window.location.href = `/project/${resolvedId}`;
      }}
    />
  );
}
