from time import perf_counter

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm import LLMClient
from app.agent.state import ResearchState
from app.db.models import AgentStep, Note, Report, Source, StepStatus, Task, TaskStatus, UploadedFile
from app.services.citation_service import (
    build_citation_items,
    format_citation_references,
    save_report_citations,
)
from app.services.memory_service import build_memory_content, create_memory, search_memories
from app.services.rag_service import SourceDocument, index_documents, retrieve_relevant_chunks
from app.tools.reader import ReaderTool, truncate_text
from app.tools.search import SearchTool


def _record_step(
    db: Session,
    task_id: int,
    step_type: str,
    step_input: dict,
    step_output: dict,
    started_at: float,
) -> None:
    duration_ms = int((perf_counter() - started_at) * 1000)
    db.add(
        AgentStep(
            task_id=task_id,
            step_type=step_type,
            input=step_input,
            output=step_output,
            status=StepStatus.completed,
            duration_ms=duration_ms,
        )
    )
    db.commit()


def _load_uploaded_documents(db: Session, task_id: int) -> list[dict[str, str | bool | None]]:
    statement = select(UploadedFile).where(UploadedFile.task_id == task_id).order_by(UploadedFile.id)
    documents = []
    for uploaded_file in db.scalars(statement):
        documents.append(
            {
                "title": uploaded_file.filename,
                "url": f"uploaded://{uploaded_file.filename}",
                "content": uploaded_file.parsed_text,
                "summary": truncate_text(uploaded_file.parsed_text, 500),
                "source_type": uploaded_file.file_type,
                "readable": bool(uploaded_file.parsed_text),
                "error": None if uploaded_file.parsed_text else "No text parsed from uploaded file",
            }
        )
    return documents


def build_research_graph(db: Session):
    llm = LLMClient()
    search_tool = SearchTool()
    reader_tool = ReaderTool()

    def planner(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        query = state["user_query"]
        plan = {
            "goal": query,
            "subtasks": [
                "检索历史长期记忆，避免重复研究",
                "检索代表性资料、论文和项目",
                "读取网页正文和本地上传文档",
                "写入 pgvector RAG 知识库并检索相关证据",
                "生成带引用编号的结构化研究报告",
            ],
        }
        keywords = [query, f"{query} 代表论文 项目", f"{query} 方法 优缺点 趋势"]
        output = {"plan": plan, "keywords": keywords}
        _record_step(db, state["task_id"], "planner", {"query": query}, output, started_at)
        return {**state, **output}

    def memory_recall(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        memories = search_memories(db, state["user_query"])
        output = {"recalled_memories": memories}
        step_output = {
            "memory_count": len(memories),
            "memories": [
                {
                    "id": memory["id"],
                    "task_id": memory["task_id"],
                    "memory_type": memory["memory_type"],
                    "distance": memory["distance"],
                    "preview": truncate_text(memory["content"], 300),
                }
                for memory in memories
            ],
        }
        _record_step(db, state["task_id"], "memory_recall", {"query": state["user_query"]}, step_output, started_at)
        return {**state, **output}

    def search(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        memory_terms = " ".join(
            truncate_text(memory["content"], 120) for memory in state.get("recalled_memories", [])[:2]
        )
        keywords = [*state["keywords"]]
        if memory_terms:
            keywords.append(f"{state['user_query']} {memory_terms}")
        results = search_tool.search_many(keywords)
        output = {"search_results": results, "keywords": keywords}
        _record_step(db, state["task_id"], "search", {"keywords": keywords}, output, started_at)
        return {**state, **output}

    def reader(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        web_documents = reader_tool.read_many(state["search_results"])
        uploaded_documents = _load_uploaded_documents(db, state["task_id"])
        sources = [*web_documents, *uploaded_documents]

        source_documents: list[SourceDocument] = []
        for document in sources:
            source = Source(
                task_id=state["task_id"],
                title=str(document["title"]),
                url=str(document["url"]),
                content_summary=str(document["summary"] or ""),
                source_type=str(document["source_type"]),
            )
            db.add(source)
            db.flush()
            document["source_id"] = source.id
            if document["content"]:
                source_documents.append(
                    SourceDocument(
                        source_id=source.id,
                        title=str(document["title"]),
                        url=str(document["url"]),
                        source_type=str(document["source_type"]),
                        content=str(document["content"]),
                    )
                )

        db.commit()
        chunk_count = index_documents(db, state["task_id"], source_documents)
        output = {"sources": sources}
        step_output = {
            "web_count": len(web_documents),
            "uploaded_count": len(uploaded_documents),
            "readable_count": sum(1 for item in sources if item["readable"]),
            "indexed_chunks": chunk_count,
        }
        _record_step(db, state["task_id"], "reader", {"results": state["search_results"]}, step_output, started_at)
        return {**state, **output}

    def extractor(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        readable_sources = [source for source in state["sources"] if source["content"]]
        evidence = "\n\n".join(
            f"Source: {source['title']}\n{truncate_text(str(source['content']), 900)}"
            for source in readable_sources[:4]
        )
        memory_context = "\n".join(
            f"Memory: {truncate_text(memory['content'], 500)}"
            for memory in state.get("recalled_memories", [])[:2]
        )
        note_content = (
            f"围绕“{state['user_query']}”已读取 {len(readable_sources)} 个来源。"
            f"历史记忆参考：{truncate_text(memory_context, 800)} "
            f"初步证据摘要：{truncate_text(evidence, 1800)}"
        )
        notes = [{"content": note_content, "tags": ["web", "document", "evidence", "memory"]}]

        for note in notes:
            db.add(Note(task_id=state["task_id"], content=note["content"], tags=note["tags"]))
        db.commit()
        output = {"notes": notes}
        _record_step(db, state["task_id"], "extractor", {"source_count": len(state["sources"])}, output, started_at)
        return {**state, **output}

    def rag(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        chunks = retrieve_relevant_chunks(db, state["task_id"], state["user_query"])
        output = {"retrieved_chunks": chunks}
        step_output = {
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "title": chunk["metadata"].get("title"),
                    "url": chunk["metadata"].get("url"),
                    "distance": chunk["distance"],
                    "preview": truncate_text(chunk["content"], 300),
                }
                for chunk in chunks
            ],
        }
        _record_step(db, state["task_id"], "rag", {"query": state["user_query"]}, step_output, started_at)
        return {**state, **output}

    def memory_save(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        content = build_memory_content(
            state["user_query"],
            state.get("notes", []),
            state.get("retrieved_chunks", []),
        )
        memory = create_memory(
            db,
            content,
            task_id=state["task_id"],
            memory_type="long_term_memory",
            tags=["research", "auto"],
        )
        output = {
            "saved_memory": {
                "id": memory.id,
                "task_id": memory.task_id,
                "memory_type": memory.memory_type,
                "preview": truncate_text(memory.content, 500),
            }
        }
        _record_step(db, state["task_id"], "memory_save", {"note_count": len(state.get("notes", []))}, output, started_at)
        return state

    def reflection(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        readable_count = sum(1 for source in state["sources"] if source["readable"])
        chunk_count = len(state.get("retrieved_chunks", []))
        memory_count = len(state.get("recalled_memories", []))
        result = {
            "enough_sources": readable_count >= 2 or chunk_count >= 2,
            "need_more_search": readable_count < 2 and chunk_count < 2,
            "comment": f"已读取 {readable_count} 个来源，RAG 检索到 {chunk_count} 个 chunks，召回 {memory_count} 条历史记忆。",
        }
        output = {"reflection": result}
        _record_step(db, state["task_id"], "reflection", {"notes": state["notes"]}, output, started_at)
        return {**state, **output}

    def report(state: ResearchState) -> ResearchState:
        started_at = perf_counter()
        citation_items = build_citation_items(state.get("retrieved_chunks", []))
        citation_hint = " ".join(f"[{item['citation_index']}]" for item in citation_items[:3]) or "[无可追踪引用]"
        memory_evidence = "\n\n".join(
            f"[Memory {index + 1}] {truncate_text(memory['content'], 900)}"
            for index, memory in enumerate(state.get("recalled_memories", [])[:3])
        )
        cited_evidence = "\n\n".join(
            f"[{item['citation_index']}] {item['title']}\n{item['quote']}"
            for item in citation_items
        )
        fallback_evidence = "\n\n".join(
            f"[Source {index + 1}] {source['title']}\n{truncate_text(str(source['content']), 1000)}"
            for index, source in enumerate(state["sources"][:3])
        )
        evidence = "\n\n".join(part for part in [memory_evidence, cited_evidence or fallback_evidence] if part)
        model_text = llm.complete(
            system="你是一个严谨的研究助理，基于长期记忆和带编号的证据输出结构化中文研究报告。",
            user=f"研究问题：{state['user_query']}\n\n证据：\n{evidence}\n\n请在关键结论后使用引用编号，例如 {citation_hint}。",
        )
        references = format_citation_references(citation_items)
        markdown = f"""# {state["user_query"]} 研究报告

## 1. 研究背景
{model_text}

## 2. 核心概念
系统已检索历史长期记忆，并结合当前任务的 RAG 证据生成报告。关键结论应优先绑定引用编号 {citation_hint}。

## 3. 代表方法
- 检索增强生成 {citation_hint}
- 长期记忆召回
- 跨来源证据整合

## 4. 代表项目 / 论文
- 后续会由 Extractor 节点从 RAG 和 Memory 中进一步结构化抽取。

## 5. 优点与局限
- 优点：已经具备跨任务记忆复用和引用级证据追踪能力。
- 局限：当前引用绑定基于检索 chunks，后续需要做到句子级证据对齐。

## 6. 未来趋势
- 接入记忆去重、可信度评分和 LLM 结构化信息抽取。

## 7. 参考来源
{references}
"""
        report = Report(task_id=state["task_id"], markdown_content=markdown)
        db.add(report)
        db.flush()
        if citation_items:
            save_report_citations(
                db,
                task_id=state["task_id"],
                report_id=report.id,
                citation_items=citation_items,
            )
        task = db.get(Task, state["task_id"])
        if task:
            task.status = TaskStatus.completed
        db.commit()
        output = {
            "report_markdown": markdown,
            "citation_count": len(citation_items),
            "citations": citation_items,
        }
        _record_step(db, state["task_id"], "report", {"reflection": state["reflection"]}, output, started_at)
        return {**state, **output}

    graph = StateGraph(ResearchState)
    graph.add_node("planner", planner)
    graph.add_node("memory_recall", memory_recall)
    graph.add_node("search", search)
    graph.add_node("reader", reader)
    graph.add_node("extractor", extractor)
    graph.add_node("rag", rag)
    graph.add_node("memory_save", memory_save)
    graph.add_node("reflection", reflection)
    graph.add_node("report", report)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "memory_recall")
    graph.add_edge("memory_recall", "search")
    graph.add_edge("search", "reader")
    graph.add_edge("reader", "extractor")
    graph.add_edge("extractor", "rag")
    graph.add_edge("rag", "memory_save")
    graph.add_edge("memory_save", "reflection")
    graph.add_edge("reflection", "report")
    graph.add_edge("report", END)

    return graph.compile()


def run_research(db: Session, task: Task) -> ResearchState:
    task.status = TaskStatus.running
    db.commit()
    graph = build_research_graph(db)
    return graph.invoke({"task_id": task.id, "user_query": task.user_query, "errors": []})
