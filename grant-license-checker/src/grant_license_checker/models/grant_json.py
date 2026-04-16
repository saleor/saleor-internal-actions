from typing import ClassVar

from pydantic import BaseModel, Field


class GrantPackage(BaseModel):
    """
    https://github.com/anchore/grant/blob/4362dc22cf5ea9baeccfa59b2863879afe0c30d7/cmd/grant/cli/internal/format.go#L61-L66
    """

    name: str = Field(description="The name of the package.")
    type: str = Field(description="The ecosystem (Python, JavaScript, etc.)")


class GrantLicense(BaseModel):
    """
    https://github.com/anchore/grant/blob/4362dc22cf5ea9baeccfa59b2863879afe0c30d7/cmd/grant/cli/internal/format.go#L37
    """

    MISSING: ClassVar[str] = "<<missing>>"

    name: str = Field(
        title="License Name",
        description="The name of the license (for non-SPDX licenses)",
    )
    license_id: str = Field(
        title="License ID",
        description=(
            "SPDX license ID, only defined when the SPDX license name is undefined"
        ),
    )
    spdx_expression: str = Field(
        title="SPDX Expression",
        description=(
            "The SPDX license expression, "
            "blank if either 'license_id' or 'name' are defined."
        ),
    )

    def get_license_name(self) -> str:
        """Returns a license name.

        Either returns:
            - a non-SPDX license name,
            - an SPDX licence ID,
            - or an SPDX expression.
        """
        return self.license_id or self.spdx_expression or self.name or self.MISSING


class GrantEvaluations(BaseModel):
    """
    https://github.com/anchore/grant/blob/4362dc22cf5ea9baeccfa59b2863879afe0c30d7/cmd/grant/cli/internal/check/report.go#L94-L100
    """

    license: GrantLicense = Field(description="Details of the evaluated license")
    package: GrantPackage = Field(description="Details of the evaluated package")


class GrantResponse(BaseModel):
    """
    Partial pydandic model for grant's check.Response struct:
    https://github.com/anchore/grant/blob/4362dc22cf5ea9baeccfa59b2863879afe0c30d7/cmd/grant/cli/internal/check/report.go#L87-L92
    """

    timestamp: str
    inputs: list[str] = Field(description="List of SBOM input paths")
    results: list[GrantEvaluations] = Field(
        description="The list of packages evaluated"
    )
