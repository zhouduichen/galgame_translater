"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProjectCard } from "@/components/home/ProjectCard";
import { ThemeToggle } from "@/components/home/ThemeToggle";

type ProjectSummary = { id: string; title: string };

const BUILTIN_DEMO_PROJECT: ProjectSummary = {
  id: "proj_001",
  title: "春日轨道 第一章",
};

function withBuiltinDemo(projects: ProjectSummary[]) {
  return [
    BUILTIN_DEMO_PROJECT,
    ...projects.filter((project) => project.id !== BUILTIN_DEMO_PROJECT.id),
  ];
}

export default function StudioPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([BUILTIN_DEMO_PROJECT]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadProjects() {
      try {
        const response = await fetch("/api/projects/");
        if (!response.ok) {
          throw new Error("项目列表加载失败");
        }
        const data = await response.json();
        if (!cancelled) {
          setProjects(withBuiltinDemo(data.projects ?? []));
        }
      } catch {
        if (!cancelled) {
          setProjects([BUILTIN_DEMO_PROJECT]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadProjects();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <ThemeToggle />
      <div className="relative z-10 mx-auto max-w-5xl px-6 py-16">
        {/* Back link */}
        <Link href="/" className="mb-8 inline-flex items-center gap-1 text-sm text-sakura-pink transition-colors hover:text-sakura-deep">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          返回首页
        </Link>

        {/* Brand header */}
        <header className="mb-16 text-center">
          <h1 className="font-[family-name:var(--font-display)] text-[clamp(2rem,5vw,3.5rem)] font-bold leading-tight tracking-wide text-[var(--text-primary)]">
            夜樱工坊
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-base leading-relaxed text-[var(--text-secondary)]">
            上传你喜爱的故事，AI 将自动生成精致的视觉小说场景。
            搭配动态背景和角色立绘，打造属于你的 Galgame。
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-xl bg-sakura-pink px-6 py-3 text-sm font-medium text-white transition-all duration-300 hover:-translate-y-0.5 hover:bg-sakura-deep hover:shadow-[0_0_24px_var(--accent-glow)]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12h14"/></svg>
              新项目
            </Link>
          </div>
        </header>

        {/* Projects section */}
        <section>
          <div className="mb-6 flex items-center justify-between">
            <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold text-[var(--text-primary)]">
              我的作品
            </h2>
            {!loading && (
              <span className="text-xs text-[var(--text-muted)]">
                {projects.length} 个项目
              </span>
            )}
          </div>

          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse rounded-xl border border-[var(--bg-border)] bg-[var(--bg-card)] p-5">
                  <div className="mb-3 h-5 w-2/3 rounded bg-[var(--bg-panel)]" />
                  <div className="mb-4 h-3 w-1/3 rounded bg-[var(--bg-panel)]" />
                  <div className="flex gap-2">
                    <div className="h-8 w-16 rounded-lg bg-[var(--bg-panel)]" />
                    <div className="h-8 w-16 rounded-lg bg-[var(--bg-panel)]" />
                  </div>
                </div>
              ))}
            </div>
          ) : projects.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--bg-border)] bg-[var(--bg-card)]/50 px-8 py-16 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-sakura-pink/10">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-sakura-pink"><path d="M12 5v14M5 12h14"/></svg>
              </div>
              <p className="text-base text-[var(--text-secondary)]">还没有项目</p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">点击上方按钮创建你的第一个 Galgame</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((p) => (
                <ProjectCard key={p.id} id={p.id} title={p.title} />
              ))}
            </div>
          )}
        </section>

        {/* Footer */}
        <footer className="mt-20 border-t border-[var(--bg-border)] pt-8 text-center">
          <p className="text-xs text-[var(--text-muted)]">
            Galgame 转译器 <span className="text-sakura-pink">v0.1.0</span>
          </p>
        </footer>
      </div>
    </>
  );
}
