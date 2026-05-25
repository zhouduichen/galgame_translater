"use client";

import { useEffect, useState } from "react";
import { PlayerContainer } from "@/components/player/PlayerContainer";
import type { Project } from "@/lib/types";

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
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
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-red-400">Error: {error}</p>
          <a href="/" className="mt-4 inline-block text-sm text-[#6688ff] hover:underline">
            &larr; Back to projects
          </a>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-[#8888a0] animate-pulse">Loading project...</p>
      </div>
    );
  }

  return <PlayerContainer project={project} />;
}
