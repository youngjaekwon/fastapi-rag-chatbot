import asyncio
import signal
from typing import Any


async def main() -> None:
    stop_event = asyncio.Event()

    def _stop(*_: Any) -> None:
        stop_event.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, _stop)
    loop.add_signal_handler(signal.SIGINT, _stop)

    while not stop_event.is_set():
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
