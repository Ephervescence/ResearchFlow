const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export type Task = {
  id: number;
  title: string;
  user_query: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type AgentStep = {
  id: number;
  task_id: number;
  step_type: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  status: string;
  error_message: string | null;
  duration_ms: number | null;
  created_at: string;
};

export type Source = {
  id: number;
  title: string;
  url: string;
  content_summary: string;
  source_type: string;
};

export type Report = {
  id: number;
  task_id: number;
  markdown_content: string;
  created_at: string;
};

export type ReportCitation = {
  id: number;
  task_id: number;
  report_id: number;
  source_id: number | null;
  chunk_id: number | null;
  citation_index: number;
  title: string;
  url: string;
  quote: string;
  created_at: string;
};

export type Memory = {
  id: number;
  task_id: number | null;
  content: string;
  memory_type: string;
  tags: string[];
  created_at: string;
};

export type UploadedFile = {
  id: number;
  task_id: number;
  filename: string;
  file_type: string;
  parsed_text: string;
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export function createTask(userQuery: string): Promise<Task> {
  return request<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify({ user_query: userQuery }),
  });
}

export function getTask(taskId: number): Promise<Task> {
  return request<Task>(`/tasks/${taskId}`);
}

export function runTask(taskId: number): Promise<{ task_id: number; status: string }> {
  return request(`/tasks/${taskId}/run`, { method: "POST" });
}

export async function uploadTaskFile(taskId: number, file: File): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/files`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<UploadedFile>;
}

export function getSteps(taskId: number): Promise<AgentStep[]> {
  return request(`/tasks/${taskId}/steps`);
}

export function getSources(taskId: number): Promise<Source[]> {
  return request(`/tasks/${taskId}/sources`);
}

export function getReport(taskId: number): Promise<Report> {
  return request(`/tasks/${taskId}/report`);
}

export function getCitations(taskId: number): Promise<ReportCitation[]> {
  return request(`/tasks/${taskId}/citations`);
}

export function getMemories(): Promise<Memory[]> {
  return request("/memories");
}
