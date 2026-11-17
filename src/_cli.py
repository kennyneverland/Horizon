"""Shared CLI argument helpers for Horizon entrypoints."""

import argparse

# Lets RSSSourceConfig keep the per-source max_items the config declares.
from .processing import source_caps as _source_caps  # noqa: F401


def add_log_level_argument(
    parser: argparse.ArgumentParser, default: str = "WARNING"
) -> None:
    parser.add_argument(
        "-l", "--log-level",
        default=default,
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        metavar="LEVEL",
        help=f"Logging level (default: {default})",
    )


def add_data_dir_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-d", "--data-dir",
        default="data",
        metavar="PATH",
        help="Path to the data directory (default: 'data')",
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        metavar="PATH",
        help="Path to config file (default: <data-dir>/config.json)",
    )
