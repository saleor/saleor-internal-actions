import jinja2

from grant_license_checker.renderers.base import BaseRenderer


TTY_TEMPLATE = """\
{% for license_name, package_list in sorted_list %}
{% set package_count = (package_list | length) %}
\033[1m{{ license_name }}\033[0m: {{ package_count }} package{% if package_count > 1 %}s{% endif %}

{% if list_packages %}
    {%- for pkg in package_list -%}
        {# Truncate packages if there are too many. -#}
        {%- if max_package_count >= 0 and loop.index0 > max_package_count - 1 -%}
            └──[{{ (package_list | length) - loop.index0 }} more...]
            {% break %}
        {% endif -%}
        └──{{ pkg.name }}
    {% endfor %}
{% endif %}
{% endfor %}
"""

# Maps ASCII control characters (with code points less than 32) to None.
# Used to sanitize untrusted inputs.
ASCII_CONTROL_CODE_TRANSLATION_MAPPING = dict.fromkeys(range(32))


def strip_control_codes(s: str) -> str:
    """Strips ASCII control characters from a string"""
    return s.translate(ASCII_CONTROL_CODE_TRANSLATION_MAPPING)


def sanitize(value: any):
    if isinstance(value, str):
        return strip_control_codes(value)
    return value


class TTYRenderer(BaseRenderer):
    @staticmethod
    def create_jinja_template() -> jinja2.Template:
        jinja_env = jinja2.Environment(
            extensions=["jinja2.ext.loopcontrols"],
            trim_blocks=True,
            lstrip_blocks=True,
            # Automatic escaping needs to be disabled as Jinja2 only support
            # XML and HTML.
            autoescape=False,
            finalize=sanitize,
        )
        return jinja_env.from_string(TTY_TEMPLATE)
