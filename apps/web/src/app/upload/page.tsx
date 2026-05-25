"use client";

import { useCallback, useState } from "react";

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
      setError("Only .txt and .md files are supported");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setError("File too large — max 5MB");
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

      // 1. Create project
      const createRes = await fetch("/api/projects/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (!createRes.ok) throw new Error("Failed to create project");
      const { id } = await createRes.json();
      setProjectId(id);

      // 2. Submit parse job
      setStatus("parsing");
      const parseRes = await fetch(`/api/projects/${id}/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ novel_text: text, target_length: "10min_demo" }),
      });
      if (!parseRes.ok) throw new Error("Failed to submit parse job");
      const { job_id } = await parseRes.json();

      // 3. Poll for job completion (since worker processes it)
      let attempts = 0;
      const poll = async (): Promise<boolean> => {
        const jobsRes = await fetch(`/api/projects/${id}/jobs`);
        const jobs = await jobsRes.json();
        const job = jobs.find((j: any) => j.job_id === job_id);
        if (!job) return false;
        if (job.status === "completed" || job.status === "failed") return true;
        return false;
      };

      // Poll up to 120s (for LLM parsing which takes time)
      while (attempts < 120) {
        const done = await poll();
        if (done) break;
        await new Promise((r) => setTimeout(r, 2000));
        attempts++;
      }

      setStatus("done");
    } catch (e: any) {
      setError(e.message);
      setStatus("error");
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <a href="/" className="mb-8 inline-block text-sm text-[#6688ff] hover:underline">
        &larr; Back
      </a>
      <h1 className="mb-2 text-2xl font-bold">New Project</h1>
      <p className="mb-8 text-sm text-[#8888a0]">
        Upload a .txt or .md novel file. We&apos;ll parse it into a playable visual novel demo.
      </p>

      {/* Dropzone */}
      <div
        className={`relative rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
          dragging ? "border-[#6688ff] bg-[#6688ff]/10" : "border-[#2a2a3a] hover:border-[#555568]"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
      >
        <input
          type="file"
          accept=".txt,.md"
          className="absolute inset-0 cursor-pointer opacity-0"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          disabled={status === "uploading" || status === "parsing"}
        />
        {file ? (
          <div>
            <p className="text-lg font-medium text-[#e8e8f0]">{file.name}</p>
            <p className="mt-1 text-sm text-[#555568]">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div>
            <p className="text-lg text-[#8888a0]">
              Drop your novel here, or <span className="text-[#6688ff]">browse</span>
            </p>
            <p className="mt-2 text-xs text-[#555568]">Supports .txt and .md, max 5MB</p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Upload button */}
      {file && status === "idle" && (
        <button
          className="mt-6 w-full rounded-lg bg-[#6688ff] px-5 py-3 font-medium text-white transition-colors hover:bg-[#5577ee]"
          onClick={handleUpload}
        >
          Upload & Parse
        </button>
      )}

      {/* Progress */}
      {status === "uploading" && (
        <div className="mt-6">
          <ProgressBar label="Uploading..." />
        </div>
      )}
      {status === "parsing" && (
        <div className="mt-6">
          <ProgressBar label="Parsing with AI (2-3 minutes)..." animate />
        </div>
      )}

      {/* Done */}
      {status === "done" && projectId && (
        <div className="mt-6 space-y-3 rounded-lg border border-[#2a2a3a] bg-[#13131a] p-6 text-center">
          <p className="text-lg font-medium text-green-400">Parse complete!</p>
          <div className="flex justify-center gap-3">
            <a
              href={`/project/${projectId}`}
              className="rounded-lg bg-[#6688ff] px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-[#5577ee]"
            >
              Play Demo
            </a>
            <a
              href={`/project/${projectId}/edit`}
              className="rounded-lg border border-[#2a2a3a] px-5 py-2 text-sm text-[#e8e8f0] transition-colors hover:border-[#6688ff]"
            >
              Edit
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function ProgressBar({ label, animate }: { label: string; animate?: boolean }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-[#8888a0]">{label}</span>
        {animate && <span className="text-xs text-[#555568] animate-pulse">Processing...</span>}
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#1a1a25]">
        <div
          className={`h-full rounded-full bg-[#6688ff] ${animate ? "w-2/3 animate-pulse" : "w-full"}`}
          style={animate ? {} : { transition: "width 0.3s" }}
        />
      </div>
    </div>
  );
}
