"""Optional aggregated chat stream helpers built on top of raw Codex events."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Generic, List, Optional, TypeVar, Union

from .event import (
    AgentMessageEvent,
    AgentReasoningEvent,
    Duration,
    EventMsg,
    ExecCommandBeginEvent,
    ExecCommandEndEvent,
    ExecCommandOutputDeltaEvent,
    ExecOutputStream,
)

T = TypeVar("T")


class _AsyncStreamBuffer(Generic[T]):
    """Utility to buffer items while allowing streaming consumption."""

    def __init__(self) -> None:
        self._items: List[T] = []
        self._data_ready = asyncio.Event()
        self._completed = asyncio.Event()
        self._stream_started = False

    @property
    def items(self) -> List[T]:
        return self._items

    def append(self, item: T) -> None:
        self._items.append(item)
        self._data_ready.set()

    def finish(self) -> None:
        self._completed.set()
        self._data_ready.set()

    def has_items(self) -> bool:
        return bool(self._items)

    def is_complete(self) -> bool:
        return self._completed.is_set()

    async def iter(self) -> AsyncIterator[T]:
        if self._stream_started:
            raise RuntimeError("stream() already consumed")
        self._stream_started = True
        index = 0
        while True:
            while index < len(self._items):
                yield self._items[index]
                index += 1
            if self._completed.is_set():
                break
            self._data_ready.clear()
            await self._data_ready.wait()

    async def wait_complete(self) -> None:
        await self._completed.wait()


class StreamSlot(Generic[T]):
    """Manages lifecycle of a single-instance stream with auto-incrementing sequence.

    Used for assistant messages and reasoning streams that have at most one
    active instance at a time.
    """

    def __init__(self, stream_class: type[T]) -> None:
        self._stream_class = stream_class
        self._seq = 0
        self._current: Optional[T] = None

    def handle_delta(self, delta: str, conversation_id: Optional[str]) -> Optional[T]:
        """Handle a delta event. Returns new stream if created, None if updating existing."""
        if self._current is None:
            self._seq += 1
            self._current = self._stream_class(self._seq, conversation_id)
            self._current.add_delta(delta)  # type: ignore[attr-defined]
            return self._current
        else:
            self._current.add_delta(delta)  # type: ignore[attr-defined]
            return None

    def handle_complete(self, event: Any, conversation_id: Optional[str]) -> Optional[T]:
        """Handle a complete event. Returns new stream if created, None if completing existing."""
        if self._current is None:
            self._seq += 1
            self._current = self._stream_class(self._seq, conversation_id)
            self._current.complete(event)  # type: ignore[attr-defined]
            result = self._current
            self._current = None
            return result
        else:
            self._current.complete(event)  # type: ignore[attr-defined]
            self._current = None
            return None

    def reset(self) -> None:
        """Reset the slot state."""
        self._current = None

    def flush_incomplete(self) -> None:
        """Flush any incomplete stream."""
        if self._current and hasattr(self._current, 'is_complete') and not self._current.is_complete:  # type: ignore[attr-defined]
            self._current._buffer.finish()  # type: ignore[attr-defined]

    @property
    def current(self) -> Optional[T]:
        """Get the current active stream, if any."""
        return self._current


@dataclass
class CommandOutputChunk:
    """Command output chunk with stream metadata."""

    stream: ExecOutputStream
    data: bytes
    text: Optional[str]


class AssistantMessageStream:
    """Aggregated assistant message with streaming access to deltas."""

    def __init__(self, sequence: int, conversation_id: Optional[str]) -> None:
        self.sequence = sequence
        self.conversation_id = conversation_id
        self._buffer: _AsyncStreamBuffer[str] = _AsyncStreamBuffer()
        self._final_event: Optional[AgentMessageEvent] = None

    def add_delta(self, delta: str) -> None:
        self._buffer.append(delta)

    def complete(self, event: AgentMessageEvent) -> None:
        self._final_event = event
        if not self._buffer.has_items() and event.message:
            self._buffer.append(event.message)
        self._buffer.finish()

    async def stream(self) -> AsyncIterator[str]:
        async for chunk in self._buffer.iter():
            yield chunk

    async def wait_complete(self) -> None:
        await self._buffer.wait_complete()

    @property
    def message(self) -> Optional[str]:
        if self._final_event:
            return self._final_event.message
        if self._buffer.has_items():
            return "".join(self._buffer.items)
        return None

    @property
    def is_complete(self) -> bool:
        return self._buffer.is_complete()


class ReasoningStream:
    """Aggregated reasoning stream similar to assistant message handling."""

    def __init__(self, sequence: int, conversation_id: Optional[str]) -> None:
        self.sequence = sequence
        self.conversation_id = conversation_id
        self._buffer: _AsyncStreamBuffer[str] = _AsyncStreamBuffer()
        self._final_event: Optional[AgentReasoningEvent] = None

    def add_delta(self, delta: str) -> None:
        self._buffer.append(delta)

    def complete(self, event: AgentReasoningEvent) -> None:
        self._final_event = event
        if not self._buffer.has_items() and event.text:
            self._buffer.append(event.text)
        self._buffer.finish()

    async def stream(self) -> AsyncIterator[str]:
        async for chunk in self._buffer.iter():
            yield chunk

    async def wait_complete(self) -> None:
        await self._buffer.wait_complete()

    @property
    def text(self) -> Optional[str]:
        if self._final_event:
            return self._final_event.text
        if self._buffer.has_items():
            return "".join(self._buffer.items)
        return None

    @property
    def is_complete(self) -> bool:
        return self._buffer.is_complete()


class CommandStream:
    """Aggregated command execution stream."""

    def __init__(self, begin: ExecCommandBeginEvent, sequence: int) -> None:
        self.sequence = sequence
        self.call_id = begin.call_id
        self.command = begin.command
        self.cwd = begin.cwd
        self.parsed_cmd = begin.parsed_cmd
        self.begin_event = begin
        self._buffer: _AsyncStreamBuffer[CommandOutputChunk] = _AsyncStreamBuffer()
        self.exit_code: Optional[int] = None
        self.duration: Optional[Duration] = None
        self.stdout: Optional[str] = None
        self.stderr: Optional[str] = None
        self.aggregated_output: Optional[str] = None
        self.formatted_output: Optional[str] = None
        self.end_event: Optional[ExecCommandEndEvent] = None

    def add_output(self, event: ExecCommandOutputDeltaEvent) -> None:
        data = event.decoded_chunk
        try:
            text = event.decoded_text
        except UnicodeDecodeError:
            text = None
        self._buffer.append(CommandOutputChunk(stream=event.stream, data=data, text=text))

    def complete(self, event: ExecCommandEndEvent) -> None:
        self.end_event = event
        self.exit_code = event.exit_code
        self.duration = event.duration
        self.stdout = event.stdout
        self.stderr = event.stderr
        self.aggregated_output = event.aggregated_output
        self.formatted_output = event.formatted_output
        if event.aggregated_output and not self._buffer.has_items():
            # Provide something for consumers even if no deltas streamed.
            self._buffer.append(
                CommandOutputChunk(stream=ExecOutputStream.STDOUT, data=event.aggregated_output.encode(), text=event.aggregated_output)
            )
        self._buffer.finish()

    async def stream(self) -> AsyncIterator[CommandOutputChunk]:
        async for chunk in self._buffer.iter():
            yield chunk

    async def wait_complete(self) -> None:
        await self._buffer.wait_complete()

    @property
    def is_complete(self) -> bool:
        return self._buffer.is_complete()


class CommandRegistry:
    """Manages multiple concurrent command streams.

    Unlike single-instance streams (assistant, reasoning), commands can have
    multiple instances running concurrently, tracked by call_id.
    """

    def __init__(self) -> None:
        self._seq = 0
        self._streams: Dict[str, CommandStream] = {}

    def begin(self, event: ExecCommandBeginEvent) -> CommandStream:
        """Handle command begin event. Returns new CommandStream."""
        self._seq += 1
        stream = CommandStream(event, self._seq)
        self._streams[event.call_id] = stream
        return stream

    def add_output(self, event: ExecCommandOutputDeltaEvent) -> Optional[EventMsg]:
        """Handle command output event. Returns orphaned event if no matching stream."""
        stream = self._streams.get(event.call_id)
        if stream is None:
            return event  # Orphaned output delta
        stream.add_output(event)
        return None

    def end(self, event: ExecCommandEndEvent) -> Optional[EventMsg]:
        """Handle command end event. Returns orphaned event if no matching stream."""
        stream = self._streams.pop(event.call_id, None)
        if stream is None:
            return event  # Orphaned end event
        stream.complete(event)
        return None

    def reset(self) -> None:
        """Reset registry state."""
        self._streams.clear()

    def flush_incomplete(self) -> None:
        """Flush all incomplete command streams."""
        for stream in self._streams.values():
            if not stream.is_complete:
                stream._buffer.finish()


class EventAggregator:
    """Orchestrates all event aggregation with dispatch table.

    This class consolidates the logic for aggregating delta events into
    structured stream objects. It uses a dispatch table for efficient
    type-based routing.
    """

    def __init__(self) -> None:
        self._assistant = StreamSlot(AssistantMessageStream)
        self._reasoning = StreamSlot(ReasoningStream)
        self._commands = CommandRegistry()

        # Import event types for dispatch
        from .event import (
            AgentMessageDeltaEvent,
            AgentReasoningDeltaEvent,
        )

        # Dispatch table mapping event types to handler methods
        self._dispatch: Dict[type, Any] = {
            AgentMessageDeltaEvent: self._handle_assistant_delta,
            AgentMessageEvent: self._handle_assistant_complete,
            AgentReasoningDeltaEvent: self._handle_reasoning_delta,
            AgentReasoningEvent: self._handle_reasoning_complete,
            ExecCommandBeginEvent: self._handle_command_begin,
            ExecCommandOutputDeltaEvent: self._handle_command_output,
            ExecCommandEndEvent: self._handle_command_end,
        }

    def process(self, event: Any) -> Optional[Union[AssistantMessageStream, ReasoningStream, CommandStream, EventMsg]]:
        """Process an event through the aggregation pipeline.

        Returns:
            - New stream object if created (should be appended to events)
            - Orphaned event if no handler found or handler returned event
            - None if event was consumed by existing stream
        """
        handler = self._dispatch.get(type(event))
        if handler:
            return handler(event)
        # Pass through unknown events
        return event

    def reset(self) -> None:
        """Reset all aggregation state."""
        self._assistant.reset()
        self._reasoning.reset()
        self._commands.reset()

    def flush_incomplete(self) -> None:
        """Flush all incomplete streams."""
        self._assistant.flush_incomplete()
        self._reasoning.flush_incomplete()
        self._commands.flush_incomplete()

    # Handler methods
    def _handle_assistant_delta(self, event: Any) -> Optional[AssistantMessageStream]:
        return self._assistant.handle_delta(event.delta, event.conversation_id)

    def _handle_assistant_complete(self, event: AgentMessageEvent) -> Optional[AssistantMessageStream]:
        return self._assistant.handle_complete(event, event.conversation_id)

    def _handle_reasoning_delta(self, event: Any) -> Optional[ReasoningStream]:
        return self._reasoning.handle_delta(event.delta, event.conversation_id)

    def _handle_reasoning_complete(self, event: AgentReasoningEvent) -> Optional[ReasoningStream]:
        return self._reasoning.handle_complete(event, event.conversation_id)

    def _handle_command_begin(self, event: ExecCommandBeginEvent) -> CommandStream:
        return self._commands.begin(event)

    def _handle_command_output(self, event: ExecCommandOutputDeltaEvent) -> Optional[EventMsg]:
        return self._commands.add_output(event)

    def _handle_command_end(self, event: ExecCommandEndEvent) -> Optional[EventMsg]:
        return self._commands.end(event)


AggregatedChatEvent = Union[
    AssistantMessageStream,
    ReasoningStream,
    CommandStream,
    EventMsg,
]


async def structured(chat: AsyncIterator[EventMsg]) -> AsyncIterator[AggregatedChatEvent]:
    """Yield aggregated wrappers while preserving access to raw events.

    **DEPRECATED**: This function is now redundant. As of version 0.2.0,
    Chat yields structured events by default. Simply iterate over the Chat
    instance directly:

        async for event in chat:  # Already structured!
            ...

    This function is kept for backward compatibility and simply passes through
    the chat iterator unchanged.
    """
    async for event in chat:
        yield event  # type: ignore[misc]


__all__ = [
    "AggregatedChatEvent",
    "AssistantMessageStream",
    "CommandOutputChunk",
    "CommandStream",
    "ReasoningStream",
    "structured",
]
