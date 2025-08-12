import asyncio
import signal


async def main():
    stop_event = asyncio.Event()

    def _stop(*_):
        stop_event.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, _stop)
    loop.add_signal_handler(signal.SIGINT, _stop)

    while not stop_event.is_set():
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
