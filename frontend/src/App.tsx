import { useMemo, useState } from "react";
import {
  BookOpen,
  Brain,
  ClipboardList,
  Database,
  FileText,
  Link,
  Play,
  Quote,
  Search,
} from "lucide-react";
import {
  AgentStep,
  Memory,
  Report,
  ReportCitation,
  Source,
  Task,
  UploadedFile,
  createTask,
  getCitations,
  getMemories,
  getReport,
  getSources,
  getSteps,
  getTask,
  runTask,
  uploadTaskFile,
} from "./api";

const defaultQuery = "请帮我调研 RAG 在多模态问答中的应用，包括核心方法、代表项目、优缺点和未来趋势。";

const stepLabels: Record<string, string> = {
  planner: "规划",
  memory_recall: "记忆召回",
  search: "搜索",
  reader: "阅读",
  extractor: "提取",
  rag: "RAG 检索",
  memory_save: "记忆沉淀",
  reflection: "反思",
  report: "报告",
};

function isExternalUrl(url: string) {
  return url.startsWith("http://") || url.startsWith("https://");
}

function compactJson(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

const pollIntervalMs = 2000;
const maxPollAttempts = 150;

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function App() {
  const [query, setQuery] = useState(defaultQuery);
  const [task, setTask] = useState<Task | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [citations, setCitations] = useState<ReportCitation[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const metrics = useMemo(
    () => [
      { label: "步骤", value: steps.length },
      { label: "来源", value: sources.length },
      { label: "引用", value: citations.length },
      { label: "记忆", value: memories.length },
    ],
    [citations.length, memories.length, sources.length, steps.length],
  );

  async function startResearch() {
    setLoading(true);
    setError(null);
    setSteps([]);
    setSources([]);
    setCitations([]);
    setMemories([]);
    setReport(null);
    setUploadedFiles([]);
    try {
      const created = await createTask(query);
      setTask(created);

      const uploaded = [];
      for (const file of selectedFiles) {
        uploaded.push(await uploadTaskFile(created.id, file));
      }
      setUploadedFiles(uploaded);

      await runTask(created.id);
      for (let attempt = 0; attempt < maxPollAttempts; attempt += 1) {
        const [nextTask, nextSteps, nextSources, nextCitations, nextMemories] = await Promise.all([
          getTask(created.id),
          getSteps(created.id),
          getSources(created.id),
          getCitations(created.id),
          getMemories(),
        ]);
        setTask(nextTask);
        setSteps(nextSteps);
        setSources(nextSources);
        setCitations(nextCitations);
        setMemories(nextMemories);

        if (nextTask.status === "completed") {
          setReport(await getReport(created.id));
          return;
        }
        if (nextTask.status === "failed") {
          throw new Error("研究任务执行失败，请查看执行流里的 run_failed 日志。");
        }
        await delay(pollIntervalMs);
      }
      throw new Error("研究任务仍在运行，请稍后刷新页面查看结果。");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "启动研究任务失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="workspace">
      <section className="task-panel">
        <div>
          <p className="eyebrow">ResearchFlow</p>
          <h1>智能研究助手</h1>
          <p className="subtitle">输入研究主题，观察 Agent 的规划、搜索、阅读、RAG、记忆和引用追踪。</p>
        </div>

        <label className="query-label" htmlFor="query">
          研究任务
        </label>
        <textarea id="query" value={query} onChange={(event) => setQuery(event.target.value)} />

        <label className="query-label" htmlFor="files">
          本地资料
        </label>
        <input
          id="files"
          className="file-input"
          type="file"
          multiple
          accept=".pdf,.md,.markdown,.txt"
          onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
        />
        {selectedFiles.length > 0 && (
          <div className="file-list">
            {selectedFiles.map((file) => (
              <span key={`${file.name}-${file.size}`}>{file.name}</span>
            ))}
          </div>
        )}

        <button className="primary-button" onClick={startResearch} disabled={loading || !query.trim()}>
          <Play size={18} />
          {loading ? "运行中" : "开始研究"}
        </button>

        {task && (
          <div className="status-strip">
            <ClipboardList size={18} />
            <span>任务 #{task.id}</span>
            <strong>{task.status}</strong>
          </div>
        )}

        <div className="metric-grid">
          {metrics.map((metric) => (
            <div className="metric-item" key={metric.label}>
              <strong>{metric.value}</strong>
              <span>{metric.label}</span>
            </div>
          ))}
        </div>

        {uploadedFiles.length > 0 && (
          <div className="file-list uploaded">
            {uploadedFiles.map((file) => (
              <span key={file.id}>{file.filename}</span>
            ))}
          </div>
        )}
        {error && <pre className="error-box">{error}</pre>}
      </section>

      <section className="run-panel">
        <div className="panel-header">
          <ClipboardList size={20} />
          <h2>执行流</h2>
        </div>
        <div className="timeline">
          {steps.length === 0 && <p className="muted">任务启动后会展示 Agent 节点日志。</p>}
          {steps.map((step) => (
            <article className="step-item" key={step.id}>
              <div>
                <strong>{stepLabels[step.step_type] ?? step.step_type}</strong>
                <span>{step.status}</span>
              </div>
              <p>
                {step.step_type} · {step.duration_ms ?? 0} ms
              </p>
              {step.error_message && <pre className="step-error">{step.error_message}</pre>}
              <pre>{compactJson(step.output)}</pre>
            </article>
          ))}
        </div>

        <div className="evidence-grid">
          <section>
            <div className="panel-header">
              <Search size={20} />
              <h2>资料来源</h2>
            </div>
            <div className="source-list">
              {sources.length === 0 && <p className="muted">暂无来源。</p>}
              {sources.map((source) =>
                isExternalUrl(source.url) ? (
                  <a href={source.url} target="_blank" rel="noreferrer" className="source-item" key={source.id}>
                    <BookOpen size={18} />
                    <span>
                      <strong>{source.title}</strong>
                      <small>{source.content_summary}</small>
                    </span>
                  </a>
                ) : (
                  <div className="source-item" key={source.id}>
                    <Database size={18} />
                    <span>
                      <strong>{source.title}</strong>
                      <small>{source.content_summary}</small>
                    </span>
                  </div>
                ),
              )}
            </div>
          </section>

          <section>
            <div className="panel-header">
              <Quote size={20} />
              <h2>引用证据</h2>
            </div>
            <div className="source-list">
              {citations.length === 0 && <p className="muted">报告生成后展示引用证据。</p>}
              {citations.map((citation) => (
                <article className="citation-item" key={citation.id}>
                  <div>
                    <strong>[{citation.citation_index}]</strong>
                    <span>{citation.title}</span>
                  </div>
                  <p>{citation.quote}</p>
                  {isExternalUrl(citation.url) && (
                    <a href={citation.url} target="_blank" rel="noreferrer">
                      <Link size={14} />
                      来源链接
                    </a>
                  )}
                </article>
              ))}
            </div>
          </section>
        </div>
      </section>

      <section className="report-panel">
        <div className="panel-header">
          <FileText size={20} />
          <h2>研究报告</h2>
        </div>
        {report ? <pre className="report">{report.markdown_content}</pre> : <p className="muted">报告生成后显示在这里。</p>}

        <div className="panel-header memory-header">
          <Brain size={20} />
          <h2>长期记忆</h2>
        </div>
        <div className="memory-list">
          {memories.length === 0 && <p className="muted">暂无长期记忆。</p>}
          {memories.slice(0, 6).map((memory) => (
            <article className="memory-item" key={memory.id}>
              <div>
                <strong>{memory.memory_type}</strong>
                <span>#{memory.id}</span>
              </div>
              <p>{memory.content}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
