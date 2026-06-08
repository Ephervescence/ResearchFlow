import argparse
import json
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(base_url: str, path: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_api(base_url: str, attempts: int = 10) -> None:
    for _ in range(attempts):
        try:
            request_json(base_url, "/health")
            return
        except (HTTPError, URLError, TimeoutError):
            sleep(1)
    raise RuntimeError(f"API is not reachable at {base_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a ResearchFlow API smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--query",
        default="请帮我调研 RAG 在多模态问答中的应用，包括核心方法、代表项目、优缺点和未来趋势。",
    )
    args = parser.parse_args()

    wait_for_api(args.base_url)
    task = request_json(args.base_url, "/api/tasks", "POST", {"user_query": args.query})
    task_id = task["id"]

    run_result = request_json(args.base_url, f"/api/tasks/{task_id}/run", "POST")
    steps = request_json(args.base_url, f"/api/tasks/{task_id}/steps")
    sources = request_json(args.base_url, f"/api/tasks/{task_id}/sources")
    report = request_json(args.base_url, f"/api/tasks/{task_id}/report")
    citations = request_json(args.base_url, f"/api/tasks/{task_id}/citations")
    memories = request_json(args.base_url, "/api/memories")

    print(
        json.dumps(
            {
                "task_id": task_id,
                "run_status": run_result["status"],
                "steps": len(steps),
                "sources": len(sources),
                "report_chars": len(report["markdown_content"]),
                "citations": len(citations),
                "memories": len(memories),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if len(steps) < 8:
        raise SystemExit("Expected at least 8 agent steps")
    if not report["markdown_content"]:
        raise SystemExit("Expected report markdown")


if __name__ == "__main__":
    main()
