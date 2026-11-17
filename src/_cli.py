"""Shared CLI argument helpers for Horizon entrypoints."""

import argparse

# Installs the cross-group dedup and technology-section patches. Imported here
# rather than in main.py so the install happens for every CLI entrypoint; the
# module docstring explains why the patches are not applied in place yet.
from .processing import compat_patches as _compat_patches  # noqa: F401


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
