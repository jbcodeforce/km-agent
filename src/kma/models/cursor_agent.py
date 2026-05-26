"""Agno Model adapter backed by the Cursor Python SDK."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Type, Union

from pydantic import BaseModel

from agno.agent import RunOutput
from agno.exceptions import ModelProviderError
from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse
from agno.utils.log import log_warning

try:
    from cursor_sdk import Agent, AgentOptions, CloudAgentOptions, CloudRepository, CursorAgentError, LocalAgentOptions
    from cursor_sdk.types import RunResult
except ImportError as exc:  # pragma: no cover - import guard for optional dependency
    raise ImportError("`cursor-sdk` not installed. Install with `uv add cursor-sdk`.") from exc


def _message_text(content: Any) -> str:
    """Flatten Agno message content to plain text for Cursor prompts."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                else:
                    parts.append(json.dumps(block, ensure_ascii=False))
            else:
                parts.append(str(block))
        return "\n".join(part for part in parts if part)
    return str(content)


def format_messages_for_cursor(messages: List[Message]) -> str:
    """Serialize Agno messages into a single Cursor agent prompt."""
    lines: list[str] = []
    for message in messages:
        role = message.role or "user"
        text = _message_text(message.content).strip()
        if not text and role != "tool":
            continue
        if role == "tool":
            tool_name = message.tool_name or "tool"
            lines.append(f"[tool:{tool_name}]\n{text}")
        else:
            lines.append(f"[{role}]\n{text}")
    return "\n\n".join(lines)


def build_cursor_agent_options(
    *,
    model_id: str,
    api_key: str,
    cwd: str | None = None,
    runtime: str = "local",
    repo_url: str | None = None,
    repo_ref: str = "main",
    auto_create_pr: bool = False,
) -> AgentOptions:
    """Build Cursor SDK ``AgentOptions`` from km-agent settings."""
    if runtime == "cloud":
        if not repo_url:
            raise ValueError(
                "KMA_CURSOR_REPO is required when KMA_CURSOR_RUNTIME=cloud "
                "(Git repository URL for the cloud agent)"
            )
        return AgentOptions(
            api_key=api_key,
            model=model_id,
            cloud=CloudAgentOptions(
                repos=[CloudRepository(url=repo_url, starting_ref=repo_ref)],
                auto_create_pr=auto_create_pr,
            ),
        )

    workspace = cwd or os.getcwd()
    return AgentOptions(
        api_key=api_key,
        model=model_id,
        local=LocalAgentOptions(cwd=workspace, setting_sources=[]),
    )


@dataclass
class CursorAgentModel(Model):
    """Run Agno chat turns through a durable Cursor SDK agent session."""

    id: str = "composer-2.5"
    name: str = "CursorAgent"
    provider: str = "Cursor"

    api_key: Optional[str] = None
    cwd: Optional[str] = None
    runtime: str = "local"
    repo_url: Optional[str] = None
    repo_ref: str = "main"
    auto_create_pr: bool = False

    _agent: Any = field(default=None, init=False, repr=False)
    _sent_message_count: int = field(default=0, init=False, repr=False)

    def _resolve_api_key(self) -> str:
        key = (self.api_key or os.getenv("CURSOR_API_KEY") or os.getenv("KMA_LLM_API_KEY") or "").strip()
        if not key:
            raise ValueError(
                "CURSOR_API_KEY is required when KMA_LLM_PROVIDER=cursor "
                "(set the key in the environment or .env)"
            )
        return key

    def _get_agent(self) -> Agent:
        if self._agent is not None:
            return self._agent
        options = build_cursor_agent_options(
            model_id=self.id,
            api_key=self._resolve_api_key(),
            cwd=self.cwd,
            runtime=self.runtime,
            repo_url=self.repo_url,
            repo_ref=self.repo_ref,
            auto_create_pr=self.auto_create_pr,
        )
        self._agent = Agent.create(options)
        return self._agent

    def close(self) -> None:
        """Release the underlying Cursor agent session."""
        if self._agent is not None:
            self._agent.close()
            self._agent = None
            self._sent_message_count = 0

    def _prompt_delta(self, messages: List[Message]) -> str:
        if self._sent_message_count >= len(messages):
            self._sent_message_count = 0
        delta = messages[self._sent_message_count :]
        self._sent_message_count = len(messages)
        if not delta:
            return format_messages_for_cursor(messages[-1:])
        return format_messages_for_cursor(delta)

    def _run_cursor_prompt(self, prompt: str) -> RunResult:
        agent = self._get_agent()
        try:
            run = agent.send(prompt)
            result = run.wait()
        except CursorAgentError as exc:
            raise ModelProviderError(
                message=f"Cursor agent startup failed: {exc.message}",
                model_name=self.name,
                model_id=self.id,
            ) from exc

        if result.status == "error":
            raise ModelProviderError(
                message=f"Cursor agent run failed: run_id={result.id}",
                model_name=self.name,
                model_id=self.id,
            )
        return result

    def _result_to_model_response(self, result: RunResult) -> ModelResponse:
        return ModelResponse(
            role="assistant",
            content=result.result or "",
            provider_data={
                "run_id": result.id,
                "agent_id": result.agent_id,
                "status": result.status,
                "duration_ms": result.duration_ms,
            },
        )

    def invoke(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[RunOutput] = None,
        compress_tool_results: bool = False,
    ) -> ModelResponse:
        if tools:
            log_warning(
                "CursorAgentModel does not expose Agno tool calls; "
                "Cursor executes its own tools inside the agent runtime."
            )
        prompt = self._prompt_delta(messages)
        assistant_message.metrics.start_timer()
        result = self._run_cursor_prompt(prompt)
        assistant_message.metrics.stop_timer()
        return self._result_to_model_response(result)

    async def ainvoke(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[RunOutput] = None,
        compress_tool_results: bool = False,
    ) -> ModelResponse:
        return self.invoke(
            messages=messages,
            assistant_message=assistant_message,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            run_response=run_response,
            compress_tool_results=compress_tool_results,
        )

    def invoke_stream(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[RunOutput] = None,
        compress_tool_results: bool = False,
    ) -> Iterator[ModelResponse]:
        if tools:
            log_warning(
                "CursorAgentModel does not expose Agno tool calls; "
                "Cursor executes its own tools inside the agent runtime."
            )
        prompt = self._prompt_delta(messages)
        agent = self._get_agent()
        assistant_message.metrics.start_timer()
        result: RunResult | None = None
        try:
            run = agent.send(prompt)
            for message in run.messages():
                if message.type != "assistant":
                    continue
                for block in message.message.content:
                    if block.type == "text" and block.text:
                        yield ModelResponse(content=block.text)
            result = run.wait()
        except CursorAgentError as exc:
            raise ModelProviderError(
                message=f"Cursor agent startup failed: {exc.message}",
                model_name=self.name,
                model_id=self.id,
            ) from exc
        finally:
            assistant_message.metrics.stop_timer()

        if result is None or result.status == "error":
            run_id = result.id if result is not None else "unknown"
            raise ModelProviderError(
                message=f"Cursor agent run failed: run_id={run_id}",
                model_name=self.name,
                model_id=self.id,
            )
        yield self._result_to_model_response(result)

    async def ainvoke_stream(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        run_response: Optional[RunOutput] = None,
        compress_tool_results: bool = False,
    ) -> AsyncIterator[ModelResponse]:
        for chunk in self.invoke_stream(
            messages=messages,
            assistant_message=assistant_message,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            run_response=run_response,
            compress_tool_results=compress_tool_results,
        ):
            yield chunk

    def _parse_provider_response(self, response: Any, **kwargs) -> ModelResponse:
        if isinstance(response, RunResult):
            return self._result_to_model_response(response)
        if isinstance(response, dict) and "result" in response:
            return ModelResponse(role="assistant", content=response.get("result") or "")
        return ModelResponse(role="assistant", content=str(response))

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        if isinstance(response, dict):
            text = response.get("text") or response.get("content")
            if text:
                return ModelResponse(content=text)
        return ModelResponse(content=str(response))
