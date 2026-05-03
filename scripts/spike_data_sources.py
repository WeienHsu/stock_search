import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.data_source_probe import main


if __name__ == "__main__":
    main()
