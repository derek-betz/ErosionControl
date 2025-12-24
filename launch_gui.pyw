import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if SRC.exists():
    sys.path.insert(0, str(SRC))


def main() -> None:
    from ec_agent.desktop_app import run

    run()


if __name__ == "__main__":
    main()
