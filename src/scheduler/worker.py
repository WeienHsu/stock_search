from __future__ import annotations

from dotenv import load_dotenv

from src.scheduler.scheduler import build_scheduler


def main() -> None:
    load_dotenv()
    scheduler = build_scheduler(blocking=True)
    print("stock_search scheduler worker started")
    scheduler.start()


if __name__ == "__main__":
    main()
