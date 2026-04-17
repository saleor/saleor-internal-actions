import dataclasses
from collections import defaultdict
from typing import DefaultDict, TextIO

import jinja2

from grant_license_checker.models.grant_json import GrantPackage, GrantResponse


@dataclasses.dataclass
class BaseRenderer:
    data: GrantResponse

    # `list_packages`: whether to include the package list.
    # `max_package_count`: the maximum number of packages to show per license.
    list_packages: bool
    max_package_count: int

    def get_packages_grouped_by_license(self) -> list[tuple[str, list[GrantPackage]]]:
        packages_by_licence: DefaultDict[str, list[GrantPackage]] = defaultdict(list)
        for eval_result in sorted(
            self.data.results,
            # Transform to lower-case for alphabetic ordering as it makes it
            # more natural for humans (e.g., 'D' is 0x44, which is lower than 'a' (0x61)).
            key=lambda o: (o.license.get_license_name().lower(), o.package.name.lower()),
        ):
            licenses = packages_by_licence[eval_result.license.get_license_name()]

            # Do not append if it's a duplicate, cdxgen can generate many duplicates
            # in the NPM ecosystem.
            if eval_result.package not in licenses:
                licenses.append(eval_result.package)

        # Sort by package count (ascending)
        sorted_list = sorted(
            packages_by_licence.items(),
            # - o[1] is the package count
            # - o[0] is the license name (2nd key that ensures consistent sorting)
            key=lambda o: (len(o[1]), o[0]),
        )
        return sorted_list

    @staticmethod
    def create_jinja_template() -> jinja2.Template:
        raise NotImplementedError("Subclasses must implement this method")

    def render(self, output_fp: TextIO) -> None:
        tpl = self.create_jinja_template()
        package_list = self.get_packages_grouped_by_license()

        for part in tpl.generate(
            sorted_list=package_list,
            list_packages=self.list_packages,
            max_package_count=self.max_package_count,
            data=self.data,
        ):
            output_fp.write(part)
