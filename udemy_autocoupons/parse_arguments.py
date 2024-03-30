"""This module exports the parse_arguments function."""

from argparse import ArgumentParser
from platform import system
from typing import TypedDict

from frozendict import frozendict


class ParsedArguments(TypedDict):
    """Parsed arguments from the command line."""

    profile_directory: str
    user_data_dir: str
    setup: str


DIRECTORIES_BY_SYSTEM = frozendict(
    {
        "Linux": "~/.config/google-chrome/",
        "Darwin": "~/Library/Application Support/Google/Chrome/",
        "Windows": "%USERPROFILE%/AppData/Local/Google/Chrome/User Data/",
    },
)


def parse_arguments() -> ParsedArguments:
    """Parses arguments from the command line.

    Returns:
        Parsed arguments.
    """
    parser = ArgumentParser()

    parser.add_argument("--profile-directory", default="Profile 1")
    parser.add_argument(
        "--user-data-dir",
        default=DIRECTORIES_BY_SYSTEM[system()],
    )
    parser.add_argument("--setup", choices=["telegram"])

    args = parser.parse_args()

    return {
        "profile_directory": args.profile_directory,
        "user_data_dir": args.user_data_dir,
        "setup": args.setup,
    }
