#!/usr/bin/env python3
"""
This command summarizes a grant JSON output with human friendly formats.

Such as:
- HTML table (GitHub Markdown-compatible),
- TTY plaintext.
"""
import argparse
import dataclasses
import logging
import sys
from typing import Self

from grant_license_checker.cli_utils.files import cli_maybe_open_file
from grant_license_checker.models.grant_json import GrantResponse
from grant_license_checker.renderers import RENDERERS

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Command:
    # Inputs:
    #   - data: the parsed grant JSON file.
    data: GrantResponse

    # Outputs:
    #   - list_packages: whether to include the package list in the output.
    #   - max_package_count: how many packages to show per license in the output
    #     before truncating (when list_packages=True).
    #   - output_format: which renderer to use
    #     (one of: grant_license_checker.renderers.RENDERERS).
    #   - output_path: where to save the results (defaults to stdout).
    list_packages: bool
    max_package_count: int
    output_format: str
    output_path: str

    @classmethod
    def get_argparser(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=__doc__)

        # Input config
        input_argparse = parser.add_argument_group("Input Preferences")
        input_argparse.add_argument(
            "-i", "--input", required=True, help="The grant JSON output file"
        )

        # Output config
        output_argparse = parser.add_argument_group("Output Preferences")
        output_argparse.add_argument(
            "-l",
            "--list-packages",
            help="Whether to include the package list in the output.",
            action="store_true",
        )
        output_argparse.add_argument(
            "-m",
            "--max-packages",
            help=(
                "The maximum number of packages to include in the output per license. "
                "A value too large can potentially not fit inside GitHub comments. "
                "-1 to disabled."
            ),
            default=20,
            type=int,
        )
        output_argparse.add_argument(
            "-f",
            "--format",
            help=(
                "The output format, one of: "
                "'text' (logs friendly), 'html' (markdown friendly)"
            ),
            choices=RENDERERS.keys(),
            default="tty",
        )
        output_argparse.add_argument(
            "-o",
            "--output",
            help="The path to the output the result. Defaults to stdout.",
            default="-",
        )

        # Logging config
        logging_argparse = parser.add_mutually_exclusive_group()
        logging_argparse.add_argument("-v", "--verbose", help="Enable verbose logging")
        logging_argparse.add_argument("-D", "--debug", help="Enable debug logging")
        return parser

    @classmethod
    def parse_args(cls) -> Self:
        args = cls.get_argparser().parse_args()

        # Set-up logging level.
        log_level = logging.WARNING
        if args.verbose:
            log_level = logging.INFO
        elif args.debug:
            log_level = logging.DEBUG

        # Configure logging.
        logging.basicConfig(
            level=log_level, format="%(asctime)s | %(levelname)s | %(message)s"
        )

        # Read and parse the JSON input file from grant.
        # stdin (shell pipe) is supported, it will be read until EOF.
        with cli_maybe_open_file(args.input, "r", default=sys.stdin) as input_fp:
            try:
                raw = input_fp.read()
            except ValueError as exc:
                logging.error("Failed to read input file (%s): %s", input_fp.name, exc)

                # Reraise the exception in order to be able to assert the parent
                # exception in tests.
                raise SystemExit(1) from exc

        try:
            data = GrantResponse.model_validate_json(raw)
        except ValueError as exc:
            logger.error("Failed to parse the input file (%s): %s", args.input, exc)
            sys.exit(1)

        return Command(
            data=data,
            output_format=args.format,
            list_packages=args.list_packages,
            max_package_count=args.max_packages,
            output_path=args.output,
        )

    def run(self):
        renderer_cls = RENDERERS.get(self.output_format)

        if renderer_cls is None:
            logger.error(
                "No such renderer: %s, supported renderers: %s",
                self.output_format,
                ', '.join(RENDERERS.keys()),
            )
            sys.exit(1)

        renderer = renderer_cls(
            data=self.data,
            list_packages=self.list_packages,
            max_package_count=self.max_package_count,
        )

        with cli_maybe_open_file(self.output_path, "w", default=sys.stdout) as out_fp:
            renderer.render(out_fp)


def main():
    Command.parse_args().run()


if __name__ == "__main__":
    main()
