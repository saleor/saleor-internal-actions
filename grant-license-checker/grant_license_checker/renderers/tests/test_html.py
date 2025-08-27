from io import StringIO

from grant_license_checker.models.grant_json import (
    GrantResponse,
    GrantLicense,
    GrantEvaluations,
    GrantPackage,
)
from grant_license_checker.renderers import HTMLRenderer


def test_get_html_summary_without_package_list(grant_json_report):
    """Checks the HTML summary output is as expected when list_packages=False."""
    renderer = HTMLRenderer(
        data=grant_json_report, list_packages=False, max_package_count=-1
    )

    out_fp = StringIO()
    renderer.render(out_fp)

    # Should be sorted in ascending order by package count, and license name.
    output = out_fp.getvalue().strip()
    assert output == """<table>
    <tr>
        <th width='200px'>License Name</th>
        <th>Package Count</th>
    </tr>
    <tr>
        <td>Apache-2.0</td>
        <td>1</td>
    </tr>
    <tr>
        <td>0BSD</td>
        <td>3</td>
    </tr>
    <tr>
        <td>BSD-3-Clause</td>
        <td>3</td>
    </tr>
</table>"""


def test_get_html_summary_with_package_list(grant_json_report):
    """Checks the HTML summary output is as expected when list_packages=True."""
    renderer = HTMLRenderer(
        data=grant_json_report, list_packages=True, max_package_count=2
    )

    out_fp = StringIO()
    renderer.render(out_fp)

    # Should be sorted in ascending order by package count, and license name.
    output = out_fp.getvalue().strip()
    assert output == """<table>
    <tr>
        <th width='200px'>License Name</th>
        <th>Package Count</th>
<th>Packages</th>    </tr>
    <tr>
        <td>Apache-2.0</td>
        <td>1</td>
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        <li>tzdata</li>
                    </ul>
                </details>
            </td>
    </tr>
    <tr>
        <td>0BSD</td>
        <td>3</td>
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        <li>asgiref</li>
                        <li>Django</li>
                            <li>
                                <i>
                                    And 1 more...
                                </i>
                            </li>
                    </ul>
                </details>
            </td>
    </tr>
    <tr>
        <td>BSD-3-Clause</td>
        <td>3</td>
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        <li>asgiref</li>
                        <li>Django</li>
                            <li>
                                <i>
                                    And 1 more...
                                </i>
                            </li>
                    </ul>
                </details>
            </td>
    </tr>
</table>"""


def test_html_is_sanitized():
    """Ensures HTML in untrusted inputs are sanitized correctly."""
    grant_json_report = GrantResponse(
        inputs=[],
        timestamp="",
        results=[
            GrantEvaluations(
                license=GrantLicense(
                    name="<h1>License</h1>", spdx_expression="", license_id=""
                ),
                package=GrantPackage(name="<h2>Package</h2>", type="pypi"),
            ),
        ],
    )
    renderer = HTMLRenderer(
        data=grant_json_report, list_packages=True, max_package_count=2
    )

    out_fp = StringIO()
    renderer.render(out_fp)

    # Should have sanitized the untrusted inputs using "&lt;" and "&gt;"
    output = out_fp.getvalue().strip()
    assert output == (
        """<table>
    <tr>
        <th width='200px'>License Name</th>
        <th>Package Count</th>
<th>Packages</th>    </tr>
    <tr>
        <td>&lt;h1&gt;License&lt;/h1&gt;</td>
        <td>1</td>
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        <li>&lt;h2&gt;Package&lt;/h2&gt;</li>
                    </ul>
                </details>
            </td>
    </tr>
</table>"""
    )
