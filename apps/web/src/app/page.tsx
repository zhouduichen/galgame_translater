"use client";

import { useEffect, useState } from "react";

type ProjectSummary = { id: string; title: string };

export default function HomePage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/projects/")
      .then((r) => r.json())
      .then((data) => setProjects(data.projects))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <header className="mb-12">
        <h1 className="text-3xl font-bold tracking-tight">Galgame Translater</h1>
        <p className="mt-2 text-[#8888a0]">
          Upload a novel, generate a playable visual novel demo, edit online, and export to Ren&apos;Py.
        </p>
      </header>

      <section className="mb-12 flex flex-wrap gap-4">
        <a
          href="/upload"
          className="inline-flex items-center gap-2 rounded-lg bg-[#6688ff] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#5577ee]"
        >
          + New Project
        </a>
        <a
          href="/project/proj_001"
          className="inline-flex items-center gap-2 rounded-lg border border-[#2a2a3a] bg-[#1a1a25] px-5 py-2.5 text-sm font-medium text-[#e8e8f0] transition-colors hover:border-[#6688ff]"
        >
          Play Demo
        </a>
        <a
          href="/project/proj_001/edit"
          className="inline-flex items-center gap-2 rounded-lg border border-[#2a2a3a] bg-[#1a1a25] px-5 py-2.5 text-sm font-medium text-[#e8e8f0] transition-colors hover:border-[#6688ff]"
        >
          Edit Demo
        </a>
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold">Projects</h2>
        {loading ? (
          <p className="text-sm text-[#555568] animate-pulse">Loading...</p>
        ) : projects.length === 0 ? (
          <p className="text-sm text-[#8888a0]">No projects yet. Create one above.</p>
        ) : (
          <div className="space-y-2">
            {projects.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-lg border border-[#2a2a3a] bg-[#13131a] px-4 py-3"
              >
                <div>
                  <span className="font-medium text-[#e8e8f0]">{p.title}</span>
                  <span className="ml-2 text-xs text-[#555568]">{p.id}</span>
                </div>
                <div className="flex gap-2">
                  <a
                    href={`/project/${p.id}`}
                    className="rounded px-2.5 py-1 text-xs text-[#6688ff] transition-colors hover:bg-[#6688ff]/20"
                  >
                    Play
                  </a>
                  <a
                    href={`/project/${p.id}/edit`}
                    className="rounded px-2.5 py-1 text-xs text-[#8888a0] transition-colors hover:bg-[#1a1a25] hover:text-[#e8e8f0]"
                  >
                    Edit
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <footer className="mt-16 border-t border-[#2a2a3a] pt-6 text-center text-xs text-[#555568]">
        Galgame Translater v0.1.0 &mdash; Novel to Visual Novel Pipeline
      </footer>
    </div>
  );
}
