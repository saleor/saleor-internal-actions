from grant_license_checker.models.grant_json import GrantPackage
from grant_license_checker.renderers import BaseRenderer


def test_get_packages_grouped_by_license(grant_json_report):
    renderer = BaseRenderer(
        data=grant_json_report, list_packages=False, max_package_count=-1
    )

    # Should be sorted in ascending order by the following keys:
    # - Number of packages per license,
    # - License name.
    assert renderer.get_packages_grouped_by_license() == [
        # Should show <<missing>> for the root component as CycloneDX
        # doesn't fetch or detect the project's license.
        ("<<missing>>", [GrantPackage(name="example-project", type="python")]),
        ("Apache-2.0", [GrantPackage(name="tzdata", type="python")]),
        (
            "BSD-3-Clause",
            [
                GrantPackage(name="asgiref", type="python"),
                GrantPackage(name="Django", type="python"),
            ],
        ),
        (
            "0BSD",
            [
                GrantPackage(name="asgiref", type="python"),
                GrantPackage(name="Django", type="python"),
                GrantPackage(name="sqlparse", type="python"),
            ],
        ),
    ]
