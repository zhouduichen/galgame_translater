import type { ParseDraft, Project } from "./types";

const BASE = "/api/projects";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const api = {
  listProjects(): Promise<{ projects: { id: string; title: string }[] }> {
    return fetchJson(`${BASE}/`);
  },

  getProject(id: string): Promise<Project> {
    return fetchJson(`${BASE}/${id}`);
  },

  updateProject(project: Project): Promise<{ ok: boolean }> {
    return fetchJson(`${BASE}/${project.project_id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(project),
    });
  },

  getDraft(projectId: string): Promise<ParseDraft> {
    return fetchJson(`${BASE}/${projectId}/draft`);
  },

  parseNovel(projectId: string, novelText: string): Promise<{ job_id: string }> {
    return fetchJson(`${BASE}/${projectId}/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ novel_text: novelText }),
    });
  },
};
