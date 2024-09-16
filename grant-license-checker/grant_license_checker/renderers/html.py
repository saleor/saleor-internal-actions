import jinja2

from grant_license_checker.renderers.base import BaseRenderer


HTML_TEMPLATE = """
<table>
    <tr>
        {# Width is needed due to SPDX expressions being long
           otherwise they take the whole space, which decreases readability. #}
        <th width='200px'>License Name</th>
        <th>Package Count</th>
        {% if list_packages %}<th>Packages</th>{% endif %}
    </tr>
    {% for license_name, package_list in sorted_list %}
    <tr>
        <td>{{ license_name }}</td>
        <td>{{ package_list | length }}</td>
        {% if list_packages %}
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        {% for pkg in package_list %}
                        {% if loop.index0 > max_package_count - 1 %}
                            {# Truncate packages if there are too many. -#}
                            {% set remain = (package_list | length) - loop.index0 %}
                            <li>
                                <i>
                                    And {{ remain }} more...
                                </i>
                            </li>
                            {% break %}
                        {% endif %}
                        <li>{{ pkg.name }}</li>
                        {% endfor %}
                    </ul>
                </details>
            </td>
        {% endif %}
    </tr>
    {% endfor %}
</table>
"""


class HTMLRenderer(BaseRenderer):
    @staticmethod
    def create_jinja_template() -> jinja2.Template:
        jinja_env = jinja2.Environment(
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=["jinja2.ext.loopcontrols"],
        )
        return jinja_env.from_string(HTML_TEMPLATE)
