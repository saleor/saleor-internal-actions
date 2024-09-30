import csv
from typing import TextIO

from grant_license_checker.renderers.base import BaseRenderer


class TSVRenderer(BaseRenderer):
    dialect = csv.excel_tab

    def render(self, output_fp: TextIO) -> None:
        package_list = self.get_packages_grouped_by_license()

        writer = csv.writer(output_fp, dialect=self.dialect)
        writer.writerow(("license", "package"))  # Header

        # Note: truncation is not supported for TSV renderer, it's meant for
        #       machine analysis rather than for human friendly output.
        for license_name, package_list in enumerate(package_list):
            for pkg in package_list:
                writer.writerow((license_name, pkg.name))
