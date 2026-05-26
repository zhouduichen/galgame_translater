"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/home/ThemeToggle";
import { BgImage } from "@/components/BgImage";
import { api } from "@/lib/api";

type UploadStatus = "idle" | "uploading" | "parsing" | "generating" | "done" | "error";

type JobStatus = "pending" | "running" | "completed" | "failed";
type GenerationJob = {
  job_id: string;
  status: JobStatus;
  job_type: string;
  progress?: number | null;
  error?: string | null;
};

type GenProgress = {
  total: number;
  completed: number;
  failed: number;
  running: number;
  errors: string[];
};

function findJob(jobs: GenerationJob[], jobId: string): GenerationJob | null {
  return jobs.find((job) => job.job_id === jobId) ?? null;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [genProgress, setGenProgress] = useState<GenProgress | null>(null);
  const [parseProgress, setParseProgress] = useState(0);
  const [workerWarning, setWorkerWarning] = useState(false);

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
    setGenProgress(null);
    setParseProgress(0);
    setWorkerWarning(false);
  }, []);

  async function handleUpload() {
    if (!file) return;
    setStatus("uploading");
    setError(null);

    try {
      const text = await file.text();
      const title = file.name.replace(/\.(txt|md)$/, "");
      const createRes = await fetch("/api/projects", {
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

      let completed = false;
      let failedError: string | null = null;
      let attempts = 0;

      while (attempts < 120) {
        const jobsRes = await fetch(`/api/projects/${id}/jobs`);
        if (!jobsRes.ok) throw new Error("查询解析任务失败");
        const jobs: GenerationJob[] = await jobsRes.json();
        const job = findJob(jobs, job_id);

        if (job?.progress != null) {
          setParseProgress(job.progress * 100);
        }

        if (job?.status === "completed") {
          setParseProgress(100);
          completed = true;
          break;
        }
        if (job?.status === "failed") {
          failedError = job.error || "解析任务失败";
          break;
        }

        await new Promise((r) => setTimeout(r, 2000));
        attempts++;
      }

      if (failedError) throw new Error(failedError);
      if (!completed) throw new Error("解析任务超时，请确认 Worker 是否正在运行");

      // Parse done — show result immediately. Asset generation fires in background.
      await api.getProject(id);
      setProjectId(id);
      setStatus("done");

      (async () => {
        try {
          const genRes = await fetch(`/api/projects/${id}/generate-assets`, { method: "POST" });
          if (!genRes.ok) return;
          const { count } = await genRes.json();
          setGenProgress({ total: count, completed: 0, failed: 0, running: 0, errors: [] });

          let staleTicks = 0;
          let lastDone = 0;
          for (let i = 0; i < 1800; i++) {
            await new Promise((r) => setTimeout(r, 1000));
            try {
              const jobsRes = await fetch(`/api/projects/${id}/jobs`);
              if (!jobsRes.ok) continue;
              const allJobs: GenerationJob[] = await jobsRes.json();
              const genJobs = allJobs.filter((j: GenerationJob) => j.job_type === "generate_asset");
              let completed = 0, failed = 0, running = 0;
              const errors: string[] = [];
              for (const j of genJobs) {
                if (j.status === "completed") completed++;
                else if (j.status === "failed") { failed++; if (j.error) errors.push(j.error); }
                else if (j.status === "running") running++;
              }
              setGenProgress({ total: count, completed, failed, running, errors });
              const done = completed + failed;
              if (done > lastDone) { lastDone = done; staleTicks = 0; }
              else { staleTicks++; }
              if (staleTicks >= 10) setWorkerWarning(true);
              if (done >= count) break;
            } catch { /* ignore transient poll errors */ }
          }
        } catch { /* background gen failed silently */ }
      })();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "上传或解析失败");
      setStatus("error");
    }
  }

  const isProcessing = status === "uploading" || status === "parsing";

  return (
    <>
      <BgImage />
      <ThemeToggle />
      <div className="relative z-10 mx-auto max-w-2xl px-6 py-16">
        {/* Back link */}
        <Link href="/studio" className="mb-8 inline-flex items-center gap-1 text-sm text-sakura-pink transition-colors hover:text-sakura-deep">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          返回
        </Link>

        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold text-[var(--text-primary)]">
          新项目
        </h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          上传 .txt 或 .md 小说文件，AI 将为你生成可播放的 Galgame 演示版。
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
            <ProgressBar
              label={`AI 解析中... ${Math.round(parseProgress)}%`}
              animate={parseProgress < 100}
              value={parseProgress}
            />
          </div>
        )}
        {status === "generating" && genProgress && (
          <div className="mt-6 animate-[fadeIn_0.3s_ease-out]">
            <ProgressBar
              label={`素材生成中：已完成 ${genProgress.completed} / 运行中 ${genProgress.running} / 总数 ${genProgress.total}`}
              sublabel={genProgress.failed > 0 ? `${genProgress.failed} 个失败` : undefined}
              animate={genProgress.completed + genProgress.failed < genProgress.total}
              value={genProgress.total > 0 ? ((genProgress.completed + genProgress.failed) / genProgress.total) * 100 : 0}
            />
            {workerWarning && (
              <p className="mt-3 text-sm text-amber-400">
                请确保 Worker 和 ComfyUI 已启动（参考 README 启动步骤）
              </p>
            )}
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
            {genProgress && genProgress.total > 0 && (
              <div className="mx-auto max-w-sm">
                <ProgressBar
                  label={genProgress.completed + genProgress.failed >= genProgress.total
                    ? `素材生成完成：${genProgress.completed}/${genProgress.total}`
                    : `素材生成中：已完成 ${genProgress.completed} / 运行中 ${genProgress.running} / 总数 ${genProgress.total}`}
                  sublabel={genProgress.failed > 0 ? `${genProgress.failed} 个失败` : undefined}
                  value={genProgress.total > 0 ? ((genProgress.completed + genProgress.failed) / genProgress.total) * 100 : 0}
                />
                {workerWarning && genProgress.completed + genProgress.failed < genProgress.total && (
                  <p className="mt-3 text-sm text-amber-400">
                    请确保 Worker 和 ComfyUI 已启动（参考 README 启动步骤）
                  </p>
                )}
              </div>
            )}
            <div className="flex justify-center gap-3">
              <Link
                href={`/project/${projectId}`}
                className="rounded-xl bg-sakura-pink px-6 py-2.5 text-sm font-medium text-white transition-all duration-300 hover:bg-sakura-deep hover:shadow-[0_0_16px_var(--accent-glow)]"
              >
                播放演示版
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

function ProgressBar({ label, sublabel, animate, value }: { label: string; sublabel?: string; animate?: boolean; value?: number }) {
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
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="text-[var(--text-secondary)]">{label}</span>
        <div className="flex items-center gap-2">
          {sublabel && <span className="text-xs text-[var(--error-red)]">{sublabel}</span>}
          {animate && <span className="text-xs text-[var(--text-muted)]">处理中{dots}</span>}
        </div>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-deep)]">
        <div
          className={`h-full rounded-full bg-gradient-to-r from-sakura-pink to-sakura-glow transition-all duration-500 ${
            value != null ? "" : animate ? "w-2/3 animate-pulse" : "w-full"
          }`}
          style={value != null ? { width: `${value}%` } : undefined}
        />
      </div>
    </div>
  );
}
