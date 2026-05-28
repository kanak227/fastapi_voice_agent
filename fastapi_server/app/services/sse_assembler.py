from __future__ import annotations


class SSEAssembler:
    """Incrementally parse Server-Sent Events from byte chunks."""

    __slots__ = ("_buf",)

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, chunk: bytes) -> list[tuple[str, str]]:
        self._buf.extend(chunk)
        events: list[tuple[str, str]] = []
        while True:
            sep = self._buf.find(b"\n\n")
            if sep < 0:
                break
            block = bytes(self._buf[:sep]).decode("utf-8", errors="replace")
            del self._buf[: sep + 2]
            event_name = "message"
            data_lines: list[str] = []
            for line in block.splitlines():
                if line.startswith("event:"):
                    event_name = line[6:].strip() or event_name
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
            data = "\n".join(data_lines)
            events.append((event_name, data))
        return events

    def drain(self) -> list[tuple[str, str]]:
        """Flush an incomplete trailing block (no trailing blank line)."""
        if not self._buf:
            return []
        block = bytes(self._buf).decode("utf-8", errors="replace").strip()
        self._buf.clear()
        if not block:
            return []
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line[6:].strip() or event_name
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        data = "\n".join(data_lines)
        return [(event_name, data)] if data else []
