from io import StringIO

from grant_license_checker.models.grant_json import (
    GrantResponse,
    GrantLicense,
    GrantEvaluations,
    GrantPackage,
)
from grant_license_checker.renderers import TTYRenderer


def test_get_tty_summary_without_package_list(grant_json_report):
    """Checks the TTY summary output is as expected when list_packages=False."""
    renderer = TTYRenderer(
        data=grant_json_report, list_packages=False, max_package_count=-1
    )

    out_fp = StringIO()
    renderer.render(out_fp)

    # Should be sorted in ascending order by package count, and license name.
    output = out_fp.getvalue().strip()
    assert (
        output
        == """\
\x1b[1mApache-2.0\x1b[0m: 1 package
\x1b[1m0BSD\x1b[0m: 3 packages
\x1b[1mBSD-3-Clause\x1b[0m: 3 packages"""
    )


def test_get_tty_summary_with_package_list(grant_json_report):
    """Checks the TTY summary output is as expected when list_packages=True."""
    renderer = TTYRenderer(
        data=grant_json_report, list_packages=True, max_package_count=2
    )

    out_fp = StringIO()
    renderer.render(out_fp)

    # Should be sorted in ascending order by package count, and license name.
    output = out_fp.getvalue().strip()
    assert (
        output
        == """\
\x1b[1mApache-2.0\x1b[0m: 1 package
└──tzdata
\x1b[1m0BSD\x1b[0m: 3 packages
└──asgiref
└──Django
└──[1 more...]
\x1b[1mBSD-3-Clause\x1b[0m: 3 packages
└──asgiref
└──Django
└──[1 more...]"""
    )


def test_ansi_escape_sequences_are_sanitized():
    """Ensures ANSI escape sequences are sanitized correctly."""
    grant_json_report = GrantResponse(
        inputs=[],
        timestamp="",
        results=[
            GrantEvaluations(
                license=GrantLicense(
                    name="<<License: \x1b[1;31m>>", spdx_expression="", license_id=""
                ),
                package=GrantPackage(name="<<Package: \x1b[224;71m>>", type="pypi"),
            ),
        ]
    )
    renderer = TTYRenderer(
        data=grant_json_report, list_packages=True, max_package_count=2
    )

    out_fp = StringIO()
    renderer.render(out_fp)

    # Should have sanitized the ANSI escape sequences,
    # only '\033[1m' and '\033[0m' should be present (come from the template itself,
    # not the values).
    output = out_fp.getvalue().strip()
    assert output == (
        "\033[1m<<License: [1;31m>>\033[0m: 1 package\n"
        "└──<<Package: [224;71m>>"
    )
