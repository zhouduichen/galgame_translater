# 夜樱工坊 UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all UI pages (home, upload, player, editor) with the 夜樱工坊 design system, including dark/light dual theme support.

**Architecture:** CSS custom properties for dual-theme tokens, CSS class-based theme switching (`data-theme` attribute on `<html>`), Zustand-free theme store. Each component uses the new CSS token names instead of hardcoded colors.

**Tech Stack:** Next.js 15, Tailwind CSS v4, Zustand (existing), CSS custom properties

---

### Task 0: Design System CSS Variables (globals.css)

**Files:**
- Overwrite: `apps/web/src/app/globals.css`

- [ ] **Replace the current globals.css with the full design system tokens**

```css
@import "tailwindcss";

@theme {
  /* Shared accents */
  --color-sakura-pink: #ff8ba0;
  --color-sakura-deep: #e6758b;
  --color-sakura-glow: #ffb3c1;
  --color-warm-gold: #d4a86a;
  --color-warm-gold-hover: #c49555;
  --color-success-green: #6bcb9e;
  --color-error-red: #e86868;

  /* Dark mode (default) */
  --color-night-deep: #0a0a10;
  --color-night-panel: #16161e;
  --color-night-card: #1e1e2a;
  --color-night-border: #2e2e3e;

  /* Light mode */
  --color-light-bg: #faf5f0;
  --color-light-panel: #f5efe8;
  --color-light-card: #ffffff;
  --color-light-border: #e0dbd4;

  /* Typography (Tailwind v4 variable format) */
  --font-display: "Noto Serif SC", "Noto Serif", Georgia, serif;
  --font-body: "Noto Sans SC", "Hiragino Sans GB", sans-serif;
  --font-mono: "JetBrains Mono", "Geist Mono", monospace;

  /* Radii */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
}

/* 
  Theme-aware CSS variables.
  [data-theme="dark"] is the default, [data-theme="light"] overrides.
*/
:root,
[data-theme="dark"] {
  --bg-deep: #0a0a10;
  --bg-panel: #16161e;
  --bg-card: #1e1e2a;
  --bg-border: #2e2e3e;
  --bg-overlay: rgba(0, 0, 0, 0.6);
  --text-primary: #ececf4;
  --text-secondary: #9090a8;
  --text-muted: #58587a;
  --glow-color: rgba(255, 139, 160, 0.19);
  --shadow-float-low: 0 4px 12px rgba(0, 0, 0, 0.3);
  --shadow-float-high: 0 8px 32px rgba(0, 0, 0, 0.4);
  --player-gradient: linear-gradient(to top, rgba(10, 10, 16, 0.95) 0%, rgba(10, 10, 16, 0.9) 60%, transparent 100%);
}

[data-theme="light"] {
  --bg-deep: #faf5f0;
  --bg-panel: #f5efe8;
  --bg-card: #ffffff;
  --bg-border: #e0dbd4;
  --bg-overlay: rgba(0, 0, 0, 0.15);
  --text-primary: #1c1c2a;
  --text-secondary: #6a6a7e;
  --text-muted: #a8a4b8;
  --glow-color: rgba(255, 139, 160, 0.25);
  --shadow-float-low: 0 2px 8px rgba(0, 0, 0, 0.08);
  --shadow-float-high: 0 8px 24px rgba(0, 0, 0, 0.1);
  --player-gradient: linear-gradient(to top, rgba(250, 245, 240, 0.95) 0%, rgba(250, 245, 240, 0.9) 60%, transparent 100%);
}

body {
  background: var(--bg-deep);
  color: var(--text-primary);
  font-family: var(--font-body);
  transition: background 300ms cubic-bezier(0.19, 1, 0.22, 1),
              color 300ms cubic-bezier(0.19, 1, 0.22, 1);
}

/* Particle animation keyframes */
@keyframes subtle-zoom {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}

@keyframes float-particle {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.4; }
  25% { transform: translateY(-30px) translateX(10px); opacity: 0.8; }
  50% { transform: translateY(-60px) translateX(-5px); opacity: 0.6; }
  75% { transform: translateY(-30px) translateX(15px); opacity: 0.8; }
}

@keyframes light-sweep {
  0% { transform: translateX(-100%) rotate(-15deg); opacity: 0; }
  50% { opacity: 0.4; }
  100% { transform: translateX(200%) rotate(-15deg); opacity: 0; }
}

@keyframes twinkle {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
```

- [ ] **Commit**

```
git add apps/web/src/app/globals.css
git commit -m "feat(design): add 夜樱工坊 design tokens with dark/light theme support"
```

---

### Task 1: Layout, Font Loading, and Theme Provider

**Files:**
- Overwrite: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/components/ThemeProvider.tsx`
- Create: `apps/web/src/hooks/useTheme.ts`

- [ ] **Create the theme provider and hook**

`apps/web/src/hooks/useTheme.ts`:
```ts
"use client";

import { useCallback, useSyncExternalStore } from "react";

type Theme = "dark" | "light";

function getSnapshot(): Theme {
  if (typeof document === "undefined") return "dark";
  return (document.documentElement.getAttribute("data-theme") as Theme) || "dark";
}

function subscribe(callback: () => void): () => void {
  const observer = new MutationObserver(() => callback());
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, () => "dark");

  const toggleTheme = useCallback(() => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  }, [theme]);

  return { theme, toggleTheme };
}
```

`apps/web/src/components/ThemeProvider.tsx`:
```tsx
"use client";

import { useEffect } from "react";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const stored = localStorage.getItem("theme") as "dark" | "light" | null;
    if (stored) {
      document.documentElement.setAttribute("data-theme", stored);
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
    }
  }, []);
  return <>{children}</>;
}
```

- [ ] **Update layout.tsx with fonts and theme provider**

```tsx
import type { Metadata } from "next";
import { Noto_Serif_SC, Noto_Sans_SC, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";

const notoSerifSC = Noto_Serif_SC({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-display",
  display: "swap",
});

const notoSansSC = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Galgame Translater — 夜樱工坊",
  description: "将小说转化为 Galgame。上传你的故事，AI 生成视觉小说，在线编辑，导出 Ren'Py。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" data-theme="dark" className={`${notoSerifSC.variable} ${notoSansSC.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen antialiased">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

- [ ] **Run build check**

```bash
cd apps/web && npm.cmd run build
```

Expected: Build passes with no errors.

- [ ] **Commit**

```
git add apps/web/src/app/layout.tsx apps/web/src/app/globals.css apps/web/src/components/ThemeProvider.tsx apps/web/src/hooks/useTheme.ts
git commit -m "feat(web): add theme system with fonts, provider, and dark/light CSS vars"
```

---

### Task 2: Home Page — Project List Redesign

**Files:**
- Create: `apps/web/src/components/home/ProjectCard.tsx`
- Create: `apps/web/src/components/home/ParticleBackground.tsx`
- Create: `apps/web/src/components/home/ThemeToggle.tsx`
- Overwrite: `apps/web/src/app/page.tsx`

- [ ] **Create ParticleBackground component**

`apps/web/src/components/home/ParticleBackground.tsx`:
```tsx
"use client";

import { useEffect, useRef } from "react";

type Particle = { x: number; y: number; size: number; speedX: number; speedY: number; opacity: number; delay: number };

export function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let particles: Particle[] = [];

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }

    function init() {
      resize();
      particles = Array.from({ length: 30 }, () => ({
        x: Math.random() * canvas!.width,
        y: Math.random() * canvas!.height,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.3,
        speedY: (Math.random() - 0.5) * 0.3 - 0.1,
        opacity: Math.random() * 0.5 + 0.2,
        delay: Math.random() * 100,
      }));
    }

    function draw() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      const color = isLight ? "200, 180, 180" : "255, 139, 160";

      for (const p of particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${color}, ${p.opacity})`;
        ctx.fill();

        p.x += p.speedX;
        p.y += p.speedY;

        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
      }

      animationId = requestAnimationFrame(draw);
    }

    init();
    draw();
    window.addEventListener("resize", resize);
    const observer = new MutationObserver(() => draw());
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      observer.disconnect();
    };
  }, []);

  return <canvas ref={canvasRef} className="pointer-events-none fixed inset-0 z-0" />;
}
```

- [ ] **Create ThemeToggle component**

`apps/web/src/components/home/ThemeToggle.tsx`:
```tsx
"use client";

import { useTheme } from "@/hooks/useTheme";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="fixed right-6 top-6 z-50 flex h-10 w-10 items-center justify-center rounded-full border border-[var(--bg-border)] bg-[var(--bg-card)] text-[var(--text-secondary)] transition-all duration-300 hover:border-sakura-pink hover:text-sakura-pink hover:shadow-[0_0_12px_var(--accent-glow)]"
      aria-label={theme === "dark" ? "切换到亮色模式" : "切换到暗色模式"}
    >
      {theme === "dark" ? (
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      )}
    </button>
  );
}
```

- [ ] **Create ProjectCard component**

`apps/web/src/components/home/ProjectCard.tsx`:
```tsx
"use client";

import Link from "next/link";

type Props = {
  id: string;
  title: string;
};

export function ProjectCard({ id, title }: Props) {
  return (
    <div className="group rounded-xl border border-[var(--bg-border)] bg-[var(--bg-card)] p-5 transition-all duration-300 hover:border-sakura-pink hover:shadow-[0_0_20px_var(--accent-glow)]">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--text-primary)]">
          {title}
        </h3>
        <span className="rounded-full bg-sakura-pink/10 px-2.5 py-0.5 text-[10px] font-medium tracking-wider text-sakura-pink">
          DEMO
        </span>
      </div>
      <p className="mb-4 text-xs text-[var(--text-muted)] font-mono">{id}</p>
      <div className="flex gap-2">
        <Link
          href={`/project/${id}`}
          className="rounded-lg bg-sakura-pink px-4 py-2 text-xs font-medium text-white transition-all duration-300 hover:bg-sakura-deep hover:shadow-[0_0_16px_var(--accent-glow)]"
        >
          Play
        </Link>
        <Link
          href={`/project/${id}/edit`}
          className="rounded-lg border border-[var(--bg-border)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)] transition-all duration-300 hover:border-sakura-pink hover:text-sakura-pink"
        >
          Edit
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Rewrite the home page**

`apps/web/src/app/page.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProjectCard } from "@/components/home/ProjectCard";
import { ParticleBackground } from "@/components/home/ParticleBackground";
import { ThemeToggle } from "@/components/home/ThemeToggle";

type ProjectSummary = { id: string; title: string };

export default function HomePage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/projects/")
      .then((r) => r.json())
      .then((data) => setProjects(data.projects || []))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <ParticleBackground />
      <ThemeToggle />
      <div className="relative z-10 mx-auto max-w-5xl px-6 py-16">
        {/* Brand header */}
        <header className="mb-16 text-center">
          <h1 className="font-[family-name:var(--font-display)] text-[clamp(2rem,5vw,3.5rem)] font-bold leading-tight tracking-wide text-[var(--text-primary)]">
            夜樱工坊
          </h1>
          <p className="mt-3 text-base text-[var(--text-secondary)] max-w-xl mx-auto leading-relaxed">
            上传你喜爱的故事，AI 将自动生成精致的视觉小说场景。
            搭配动态背景和角色立绘，打造属于你的 Galgame。
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-xl bg-sakura-pink px-6 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-sakura-deep hover:shadow-[0_0_24px_var(--accent-glow)] hover:-translate-y-0.5"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12h14"/></svg>
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
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-sakura-pink"><path d="M12 5v14M5 12h14"/></svg>
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
            Galgame Translater <span className="text-sakura-pink">v0.1.0</span>
          </p>
        </footer>
      </div>
    </>
  );
}
```

- [ ] **Run build check**

```bash
cd apps/web && npm.cmd run build
```

- [ ] **Commit**

```
git add apps/web/src/app/page.tsx apps/web/src/components/home/ apps/web/src/hooks/useTheme.ts
git commit -m "feat(web): redesign home page with 夜樱工坊 brand and project list"
```

---

### Task 3: Upload Page Redesign

**Files:**
- Overwrite: `apps/web/src/app/upload/page.tsx`

- [ ] **Rewrite the upload page with immersive sakura-themed UI**

`apps/web/src/app/upload/page.tsx`:
```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/home/ThemeToggle";

type UploadStatus = "idle" | "uploading" | "parsing" | "done" | "error";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = useCallback((f: File | null) => {
    setError(null);
    if (!f) return;
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "txt" && ext !== "md") {
      setError("仅支持 .txt 和 .md 文件");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setError("文件过大 — 最大 5MB");
      return;
    }
    setFile(f);
  }, []);

  async function handleUpload() {
    if (!file) return;
    setStatus("uploading");
    setError(null);

    try {
      const text = await file.text();
      const title = file.name.replace(/\.(txt|md)$/, "");
      const createRes = await fetch("/api/projects/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (!createRes.ok) throw new Error("创建项目失败");
      const { id } = await createRes.json();
      setProjectId(id);

      setStatus("parsing");
      const parseRes = await fetch(`/api/projects/${id}/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ novel_text: text, target_length: "10min_demo" }),
      });
      if (!parseRes.ok) throw new Error("提交解析任务失败");
      const { job_id } = await parseRes.json();

      let attempts = 0;
      while (attempts < 120) {
        const jobsRes = await fetch(`/api/projects/${id}/jobs`);
        const jobs = await jobsRes.json();
        const job = jobs.find((j: any) => j.job_id === job_id);
        if (job?.status === "completed" || job?.status === "failed") break;
        await new Promise((r) => setTimeout(r, 2000));
        attempts++;
      }

      setStatus("done");
    } catch (e: any) {
      setError(e.message);
      setStatus("error");
    }
  }

  const isProcessing = status === "uploading" || status === "parsing";

  return (
    <>
      <ThemeToggle />
      <div className="relative z-10 mx-auto max-w-2xl px-6 py-16">
        {/* Back link */}
        <Link href="/" className="mb-8 inline-flex items-center gap-1 text-sm text-sakura-pink transition-colors hover:text-sakura-deep">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          返回
        </Link>

        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold text-[var(--text-primary)]">
          新项目
        </h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          上传 .txt 或 .md 小说文件，AI 将为你生成可播放的 Galgame demo。
        </p>

        {/* Dropzone */}
        <div
          className={`relative mt-8 cursor-pointer rounded-xl border-2 border-dashed p-14 text-center transition-all duration-300 ${
            dragging
              ? "border-sakura-pink bg-sakura-pink/5 shadow-[0_0_32px_var(--accent-glow)]"
              : "border-[var(--bg-border)] bg-[var(--bg-card)]/30 hover:border-sakura-pink/50 hover:bg-[var(--bg-card)]/50"
          } ${isProcessing ? "pointer-events-none opacity-60" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
        >
          <input
            type="file"
            accept=".txt,.md"
            className="absolute inset-0 cursor-pointer opacity-0"
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            disabled={isProcessing}
          />
          {file ? (
            <div className="animate-[fadeIn_0.3s_ease-out]">
              <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-sakura-pink/10">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-sakura-pink"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
              <p className="text-base font-medium text-[var(--text-primary)]">{file.name}</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <div>
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-sakura-pink/10">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-sakura-pink"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              </div>
              <p className="text-base text-[var(--text-secondary)]">
                将小说拖放到这里，或<span className="text-sakura-pink">浏览文件</span>
              </p>
              <p className="mt-2 text-xs text-[var(--text-muted)]">支持 .txt 和 .md，最大 5MB</p>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 animate-[fadeIn_0.3s_ease-out] rounded-xl border border-[var(--error-red)]/30 bg-[var(--error-red)]/5 px-5 py-3 text-sm text-[var(--error-red)]">
            {error}
          </div>
        )}

        {/* Upload button */}
        {file && status === "idle" && (
          <button
            onClick={handleUpload}
            className="mt-6 w-full rounded-xl bg-sakura-pink px-5 py-3.5 font-medium text-white transition-all duration-300 hover:bg-sakura-deep hover:shadow-[0_0_24px_var(--accent-glow)]"
          >
            ✿ 上传并解析
          </button>
        )}

        {/* Progress */}
        {status === "uploading" && (
          <div className="mt-6 animate-[fadeIn_0.3s_ease-out]">
            <ProgressBar label="上传中..." />
          </div>
        )}
        {status === "parsing" && (
          <div className="mt-6 animate-[fadeIn_0.3s_ease-out]">
            <ProgressBar label="AI 解析中（约 2-3 分钟）..." animate />
          </div>
        )}

        {/* Done */}
        {status === "done" && projectId && (
          <div className="mt-6 animate-[fadeIn_0.5s_ease-out] space-y-4 rounded-xl border border-[var(--bg-border)] bg-[var(--bg-card)] p-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success-green/10">
              <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-success-green"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <p className="font-[family-name:var(--font-display)] text-xl font-semibold text-success-green">
              解析完成！
            </p>
            <div className="flex justify-center gap-3">
              <Link
                href={`/project/${projectId}`}
                className="rounded-xl bg-sakura-pink px-6 py-2.5 text-sm font-medium text-white transition-all duration-300 hover:bg-sakura-deep hover:shadow-[0_0_16px_var(--accent-glow)]"
              >
                播放 Demo
              </Link>
              <Link
                href={`/project/${projectId}/edit`}
                className="rounded-xl border border-[var(--bg-border)] px-6 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all duration-300 hover:border-sakura-pink hover:text-sakura-pink"
              >
                编辑
              </Link>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function ProgressBar({ label, animate }: { label: string; animate?: boolean }) {
  const [dots, setDots] = useState("");

  useEffect(() => {
    if (!animate) return;
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "" : d + "."));
    }, 500);
    return () => clearInterval(interval);
  }, [animate]);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-[var(--text-secondary)]">{label}</span>
        {animate && <span className="text-xs text-[var(--text-muted)]">处理中{dots}</span>}
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-deep)]">
        <div
          className={`h-full rounded-full bg-gradient-to-r from-sakura-pink to-sakura-glow transition-all duration-500 ${
            animate ? "w-2/3 animate-pulse" : "w-full"
          }`}
        />
      </div>
    </div>
  );
}
```

Note: Need to add `"useEffect"` import in the ProgressBar function. Also need `"use client"` - the page already has it. The ProgressBar use of `useEffect` and `useState` requires updating its imports. Let me add the missing import.

Actually wait - `useEffect` and `useState` are already imported at the top of the page file. But ProgressBar is a local function that also uses `useEffect` and `useState`. Since it's inside the same "use client" file, it should work.

- [ ] **Run build check**

```bash
cd apps/web && npm.cmd run build
```

- [ ] **Commit**

```
git add apps/web/src/app/upload/page.tsx
git commit -m "feat(web): redesign upload page with 夜樱工坊 brand"
```

---

### Task 4: Player Components — Theme-Aware Update

**Files:**
- Modify: `apps/web/src/components/player/DialogueBox.tsx`
- Modify: `apps/web/src/components/player/NarrationBox.tsx`
- Modify: `apps/web/src/components/player/ChoicePanel.tsx`
- Modify: `apps/web/src/components/player/BackgroundLayer.tsx`
- Modify: `apps/web/src/components/player/CharacterSprite.tsx`
- Modify: `apps/web/src/components/player/PlayerControls.tsx`
- Modify: `apps/web/src/components/player/PlayerContainer.tsx`
- Modify: `apps/web/src/app/project/[id]/page.tsx`

For each player component, replace hardcoded color values with CSS variable references (`var(--bg-card)`, `var(--text-primary)`, `var(--bg-border)`, `var(--bg-overlay)`), replace `#6688ff` with `sakura-pink`, and use the `font-[family-name:var(--font-display)]` class for character names.

- [ ] **Update DialogueBox.tsx**

Replace:
- `from-[#0a0a0f]/95 via-[#0a0a0f]/90 to-transparent` → `var(--player-gradient)`
- `text-[#6688ff]` → `text-sakura-pink`
- `text-[#8888a0]` → `text-[var(--text-secondary)]`
- `text-[#555568]` → `text-[var(--text-muted)]`
- `bg-[#ffffff10]` → `bg-white/10`
- character name: add `font-[family-name:var(--font-display)]` class

Final component:
```tsx
"use client";

import { useTypewriter } from "@/hooks/useTypewriter";
import type { Character, Emotion } from "@/lib/types";

type Props = {
  text: string;
  character?: Character | null;
  emotion?: Emotion;
  textSpeed: number;
  onComplete?: () => void;
  onClick: () => void;
};

export function DialogueBox({ text, character, emotion, textSpeed, onClick }: Props) {
  const { displayed, complete, skip } = useTypewriter(text, textSpeed);
  const color = character?.color ?? "#ff8ba0";

  function handleClick() {
    if (!complete) { skip(); }
    else { onClick(); }
  }

  return (
    <div
      className="absolute bottom-0 left-0 right-0 cursor-pointer px-6 pb-6 pt-16"
      style={{ background: "var(--player-gradient)" }}
      onClick={handleClick}
    >
      <div className="mx-auto max-w-3xl">
        {character && (
          <div className="mb-2 flex items-center gap-2">
            <span
              className="font-[family-name:var(--font-display)] text-lg font-semibold"
              style={{ color }}
            >
              {character.name}
            </span>
            {emotion && emotion !== "neutral" && (
              <span className="rounded bg-white/10 px-2 py-0.5 text-xs text-[var(--text-secondary)]">
                {emotion}
              </span>
            )}
          </div>
        )}
        <p className="min-h-[3em] text-lg leading-relaxed text-[var(--text-primary)]">
          {displayed}
          {!complete && <span className="ml-0.5 animate-pulse text-sakura-pink">▌</span>}
        </p>
        {complete && (
          <p className="mt-2 animate-pulse text-xs text-[var(--text-muted)]">
            {textSpeed <= 0 ? "点击继续" : "▼ 点击继续"}
          </p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Update NarrationBox.tsx**

Replace hardcoded colors with CSS vars and sakura-pink:
```tsx
"use client";

import { useTypewriter } from "@/hooks/useTypewriter";

type Props = {
  text: string;
  textSpeed: number;
  onClick: () => void;
};

export function NarrationBox({ text, textSpeed, onClick }: Props) {
  const { displayed, complete, skip } = useTypewriter(text, textSpeed);

  function handleClick() {
    if (!complete) { skip(); }
    else { onClick(); }
  }

  return (
    <div
      className="absolute inset-0 flex cursor-pointer items-center justify-center px-8"
      onClick={handleClick}
    >
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-lg italic leading-relaxed text-[var(--text-primary)]/80">{displayed}</p>
        {!complete && <span className="ml-0.5 animate-pulse text-sakura-pink">▌</span>}
        {complete && (
          <p className="mt-4 animate-pulse text-xs text-[var(--text-muted)]">点击继续</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Update ChoicePanel.tsx**

```tsx
"use client";

import type { ChoiceOption } from "@/lib/types";

type Props = {
  narration: string;
  options: ChoiceOption[];
  onChoose: (opt: ChoiceOption) => void;
};

export function ChoicePanel({ narration, options, onChoose }: Props) {
  return (
    <div className="absolute inset-0 flex items-center justify-center px-6" style={{ background: "var(--bg-overlay)" }}>
      <div className="mx-auto w-full max-w-xl">
        {narration && (
          <p className="mb-8 text-center text-lg text-[var(--text-primary)]/80">{narration}</p>
        )}
        <div className="space-y-3">
          {options.map((opt, i) => (
            <button
              key={opt.option_id}
              className="group w-full rounded-xl border border-[var(--bg-border)] bg-[var(--bg-card)] px-6 py-4 text-left text-[var(--text-primary)] transition-all duration-300 hover:border-sakura-pink hover:bg-sakura-pink/5 hover:translate-x-1"
              onClick={() => onChoose(opt)}
            >
              <span className="mr-3 inline-flex h-6 w-6 items-center justify-center rounded-full border border-sakura-pink text-xs text-sakura-pink transition-all duration-300 group-hover:bg-sakura-pink group-hover:text-white">
                {i + 1}
              </span>
              {opt.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Update BackgroundLayer.tsx**

```tsx
import type { AssetResource } from "@/lib/types";

export function BackgroundLayer({ resource }: { resource?: AssetResource | null }) {
  if (!resource || resource.url.startsWith("/assets/placeholder")) {
    return (
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--bg-deep)] via-sakura-pink/5 to-[var(--bg-deep)]" />
    );
  }
  return (
    <div className="absolute inset-0">
      <img src={resource.url} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0 bg-black/30" />
    </div>
  );
}
```

- [ ] **Update CharacterSprite.tsx**

Replace `#2a2a3a` → `var(--bg-border)`, `#1a1a25` → `var(--bg-card)`, `#8888a0` → `var(--text-secondary)`.

```tsx
"use client";

import type { Character, AssetResource, Side } from "@/lib/types";

type Props = {
  character?: Character | null;
  emotion?: string;
  side: Side;
  assetResources: Record<string, AssetResource>;
};

export function CharacterSprite({ character, emotion, side, assetResources }: Props) {
  if (!character) return null;

  const assetId = emotion ? character.asset_ids[emotion] : null;
  const resource = assetId ? assetResources[assetId] : null;

  const sideClasses: Record<Side, string> = {
    left: "left-0 translate-x-0",
    right: "right-0 translate-x-0",
    center: "left-1/2 -translate-x-1/2",
  };

  return (
    <div className={`pointer-events-none absolute bottom-0 ${sideClasses[side]} h-[85%] w-auto max-w-[45%]`}>
      {resource && !resource.url.startsWith("/assets/placeholder") ? (
        <img src={resource.url} alt={character.name} className="h-full w-auto object-contain" />
      ) : (
        <div className="flex h-full w-48 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-2 flex h-24 w-24 items-center justify-center rounded-full border-2 border-[var(--bg-border)] bg-[var(--bg-card)] text-3xl text-sakura-pink">
              {character.name.charAt(0)}
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{character.name}</p>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Update PlayerControls.tsx**

```tsx
"use client";

import type { PlayerStatus } from "@/stores/playerStore";

type Props = {
  status: PlayerStatus;
  autoMode: boolean;
  textSpeed: number;
  hasHistory: boolean;
  onBack: () => void;
  onToggleAuto: () => void;
  onTextSpeedChange: (speed: number) => void;
  onRestart: () => void;
};

export function PlayerControls({
  status, autoMode, textSpeed, hasHistory,
  onBack, onToggleAuto, onTextSpeedChange, onRestart,
}: Props) {
  return (
    <div className="absolute right-4 top-4 flex items-center gap-2">
      {hasHistory && (
        <button
          className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-card)]/80 px-3 py-1.5 text-xs text-[var(--text-secondary)] backdrop-blur-sm transition-all duration-200 hover:border-sakura-pink hover:text-[var(--text-primary)]"
          onClick={onBack}
        >
          返回
        </button>
      )}

      <button
        className={`rounded-lg border px-3 py-1.5 text-xs font-medium backdrop-blur-sm transition-all duration-200 ${
          autoMode
            ? "border-sakura-pink bg-sakura-pink/15 text-sakura-pink"
            : "border-[var(--bg-border)] bg-[var(--bg-card)]/80 text-[var(--text-secondary)] hover:border-sakura-pink hover:text-[var(--text-primary)]"
        }`}
        onClick={onToggleAuto}
      >
        AUTO
      </button>

      <select
        className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-card)]/80 px-2 py-1.5 text-xs text-[var(--text-secondary)] backdrop-blur-sm transition-all duration-200 hover:border-sakura-pink"
        value={textSpeed}
        onChange={(e) => onTextSpeedChange(Number(e.target.value))}
      >
        <option value={0}>即时</option>
        <option value={20}>快速</option>
        <option value={40}>普通</option>
        <option value={80}>慢速</option>
      </select>

      {status === "ended" && (
        <button
          className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-card)]/80 px-3 py-1.5 text-xs text-[var(--text-secondary)] backdrop-blur-sm transition-all duration-200 hover:border-sakura-pink hover:text-[var(--text-primary)]"
          onClick={onRestart}
        >
          重来
        </button>
      )}
    </div>
  );
}
```

- [ ] **Update page.tsx (project/[id])**

The player page layout should use theme-aware CSS variables in the loading/error states:

Replace the loading and error states in the page:
```tsx
if (error) {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--bg-deep)]">
      <div className="text-center">
        <p className="text-[var(--error-red)]">Error: {error}</p>
        <a href="/" className="mt-4 inline-block text-sm text-sakura-pink hover:underline">
          &larr; 返回项目列表
        </a>
      </div>
    </div>
  );
}

if (!project) {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--bg-deep)]">
      <p className="text-[var(--text-secondary)] animate-pulse">加载项目中...</p>
    </div>
  );
}
```

- [ ] **Run build check**

```bash
cd apps/web && npm.cmd run build
```

- [ ] **Commit**

```
git add apps/web/src/components/player/ apps/web/src/app/project/\[id\]/page.tsx
git commit -m "feat(web): update player components with theme-aware CSS variables"
```

---

### Task 5: Editor Components — Theme-Aware Update

**Files:**
- Modify: `apps/web/src/components/editor/EditorContainer.tsx`
- Modify: `apps/web/src/components/editor/NodeCard.tsx`
- Modify: `apps/web/src/components/editor/SceneTree.tsx`
- Modify: `apps/web/src/app/project/[id]/edit/page.tsx`

- [ ] **Update EditorContainer.tsx**

Replace hardcoded background/colors with CSS vars and sakura-pink:

Key replacements:
- `bg-[#0a0a0f]` → `bg-[var(--bg-deep)]`
- `border-[#2a2a3a]` → `border-[var(--bg-border)]`
- `text-[#8888a0]` → `text-[var(--text-secondary)]`
- `text-[#555568]` → `text-[var(--text-muted)]`
- `text-[#e8e8f0]` → `text-[var(--text-primary)]`
- `bg-[#6688ff]` → `bg-sakura-pink`
- `hover:bg-[#5577ee]` → `hover:bg-sakura-deep`
- `bg-[#1a1a25]` → `bg-[var(--bg-card)]`
- `hover:border-[#6688ff]` → `hover:border-sakura-pink`

- [ ] **Update NodeCard.tsx**

Replace:
- `border-l-[#6688ff]` → `border-l-sakura-pink`
- `border-l-[#88cc88]` → `border-l-[#6bcb9e]` (update green)
- `border-l-[#ff8866]` → keep orange or use `border-l-[#e86868]`
- `border-[#2a2a3a]` → `border-[var(--bg-border)]`
- `bg-[#13131a]` → `bg-[var(--bg-panel)]`
- `bg-[#0a0a0f]` → `bg-[var(--bg-deep)]`
- `ring-1 ring-[#6688ff]` → `ring-1 ring-sakura-pink`
- `text-[#e8e8f0]` → `text-[var(--text-primary)]`
- `text-[#aaaac0]` → `text-[var(--text-primary)]/80`
- `text-[#8888a0]` → `text-[var(--text-secondary)]`
- `text-[#555568]` → `text-[var(--text-muted)]`
- `text-[#6688ff]` → `text-sakura-pink`
- `bg-[#ffffff10]` → `bg-white/10`

- [ ] **Update SceneTree.tsx**

Read the existing file first, then replace colors:
- `bg-[#1a1a25]` → `bg-[var(--bg-card)]`
- `text-[#8888a0]` → `text-[var(--text-secondary)]`
- `text-[#e8e8f0]` → `text-[var(--text-primary)]`
- `border-[#2a2a3a]` → `border-[var(--bg-border)]`
- `text-[#6688ff]` → `text-sakura-pink`
- `bg-[#6688ff]/20` → `bg-sakura-pink/20`

- [ ] **Update editor page (project/[id]/edit/page.tsx)**

Replace loading/error states same as player page:
```tsx
if (error) {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--bg-deep)]">
      <div className="text-center">
        <p className="text-[var(--error-red)]">Error: {error}</p>
        <a href="/" className="mt-4 inline-block text-sm text-sakura-pink hover:underline">
          &larr; 返回项目列表
        </a>
      </div>
    </div>
  );
}

if (!project) {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--bg-deep)]">
      <p className="text-[var(--text-secondary)] animate-pulse">加载编辑器...</p>
    </div>
  );
}
```

- [ ] **Run build check**

```bash
cd apps/web && npm.cmd run build
```

- [ ] **Commit**

```
git add apps/web/src/components/editor/ apps/web/src/app/project/\[id\]/edit/page.tsx
git commit -m "feat(web): update editor components with theme-aware CSS variables"
```

---

### Task 6: Polish and Integration Test

- [ ] **Full build verification**

```bash
cd apps/web && npm.cmd run build
```

Expected: Production build passes with no errors.

- [ ] **Run frontend tests if they exist**

```bash
cd apps/web && npm.cmd run test
```

Expected: All existing tests still pass (no functional changes were made).

- [ ] **Final commit with any edge-case fixes**

```
git add -A
git commit -m "chore: final polish for 夜樱工坊 UI redesign"
```
