import argparse
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from core.services.mcp_server_service import build_auth_headers, resolve_server_url
from core.services.mcp_tool_service import sanitize_json_schema
from evals.fixtures import FIXTURES, ToolFixture


def _load_servers(names):
    from core.database.session import get_db_context
    from core.models.mcp_server import McpServer

    with get_db_context() as db:
        q = db.query(McpServer).filter(McpServer.is_active.is_(True))
        if names:
            q = q.filter(McpServer.name.in_(names))
        rows = q.all()
        for r in rows:
            db.expunge(r)
        return rows


def _load_api_key(org_id, provider_slug):
    from core.database.session import get_db_context
    from core.models.api_key import ApiKey
    from core.models.model_provider import ModelProvider
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        api_key = (
            db.query(ApiKey)
            .join(ModelProvider, ModelProvider.id == ApiKey.provider_id)
            .filter(
                ApiKey.organization_id == org_id,
                ApiKey.is_active.is_(True),
                ApiKey.service_type == "llm",
                ModelProvider.slug == provider_slug,
            )
            .first()
        )
        if not api_key or not api_key.encrypted_key:
            raise SystemExit(f"No active '{provider_slug}' LLM key for org {org_id}")
        return decrypt(api_key.encrypted_key)


async def _fetch_tools(server) -> List[Any]:
    from core.services.mcp_tool_service import build_mcp_request_headers

    headers = build_mcp_request_headers(server)
    url = resolve_server_url(server)
    tools: List[Any] = []
    try:
        async with AsyncExitStack() as stack:
            if server.transport_type == "sse":
                read, write = await stack.enter_async_context(
                    sse_client(url=url, headers=headers)
                )
            else:
                read, write, _ = await stack.enter_async_context(
                    streamablehttp_client(url=url, headers=headers)
                )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            listed = await session.list_tools()
            tools = list(listed.tools)
    except Exception as exc:
        if not tools:
            raise
        print(f"[schemas] {server.name}: ignoring teardown error ({type(exc).__name__})")
    return tools


def _openai_tool(tool) -> Dict[str, Any]:
    schema = dict(sanitize_json_schema(tool.inputSchema or {}))
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": (tool.description or "")[:1024],
            "parameters": schema,
        },
    }


def _call_llm(client, model, system_prompt, prompt, tools):
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        tools=tools or None,
        tool_choice="auto" if tools else None,
    )
    msg = resp.choices[0].message
    calls = []
    for c in msg.tool_calls or []:
        try:
            args = json.loads(c.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append((c.function.name, args))
    return msg.content, calls


async def run(args) -> int:
    from deepeval.metrics import ToolCorrectnessMetric
    from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams
    from openai import OpenAI

    servers = _load_servers(args.servers)
    if not servers:
        raise SystemExit("No active MCP servers found")

    api_key = _load_api_key(servers[0].organization_id, args.provider)
    kwargs = {"api_key": api_key}
    if args.base_url:
        kwargs["base_url"] = args.base_url
    client = OpenAI(**kwargs)

    if True:
        by_server: Dict[str, List[Dict[str, Any]]] = {}
        for server in servers:
            try:
                tools = await _fetch_tools(server)
            except Exception as exc:
                print(f"[schemas] {server.name}: FAILED — {str(exc)[:110]}")
                continue
            by_server[server.name] = [_openai_tool(t) for t in tools]
            print(f"[schemas] {server.name}: {len(tools)} tools")

        fixtures = [f for f in FIXTURES if not args.servers or f.server in args.servers]
        if args.tag:
            fixtures = [f for f in fixtures if args.tag in f.tags]
        print(f"[llm] provider={args.provider} model={args.model}")
        print(f"[eval] {len(fixtures)} fixtures\n")

        failures = 0
        for fx in fixtures:
            tools = by_server.get(fx.server, [])
            if not tools:
                print(f"SKIP  {fx.name}  (server '{fx.server}' not loaded)")
                continue
            try:
                text, calls = _call_llm(client, args.model, fx.system_prompt, fx.prompt, tools)
            except Exception as exc:
                failures += 1
                print(f"ERROR {fx.name}  {str(exc)[:130]}")
                continue

            expected = ToolCall(name=fx.expected_tool, input_parameters=fx.expected_params or {})
            test_case = LLMTestCase(
                input=fx.prompt,
                actual_output=text or "",
                tools_called=[ToolCall(name=n, input_parameters=a) for n, a in calls],
                expected_tools=[expected],
            )
            eval_params = [ToolCallParams.INPUT_PARAMETERS] if fx.expected_params else []
            metric = ToolCorrectnessMetric(
                threshold=fx.threshold,
                evaluation_params=eval_params,
                include_reason=True,
            )
            metric.measure(test_case)

            called = [n for n, _ in calls]
            if metric.is_successful():
                print(f"PASS  {fx.name}  score={metric.score:.2f}  → {called[0] if called else '-'}")
            else:
                failures += 1
                print(f"FAIL  {fx.name}  score={metric.score:.2f} (threshold {fx.threshold})")
                print(f"        {metric.reason}")
                for n, a in calls:
                    print(f"        called {n}: {json.dumps(a)[:170]}")

        print(f"\n{len(fixtures) - failures}/{len(fixtures)} passed")
        return 1 if failures else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--provider", default="groq")
    p.add_argument("--model", default="openai/gpt-oss-120b")
    p.add_argument("--base-url", default="https://api.groq.com/openai/v1")
    p.add_argument("--servers", nargs="*", default=None)
    p.add_argument("--tag", default=None)
    sys.exit(asyncio.run(run(p.parse_args())))


if __name__ == "__main__":
    main()
