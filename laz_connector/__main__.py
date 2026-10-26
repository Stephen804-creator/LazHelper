"""Command-line entry point for the Laz Connector."""
from __future__ import annotations

import argparse

from laz_connector import __version__
from laz_connector.agent import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Laz Helper local device connector")
    parser.add_argument("--version", action="version", version=f"Laz Connector {__version__}")
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
