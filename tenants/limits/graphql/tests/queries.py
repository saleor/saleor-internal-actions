from typing import TypedDict

from saleor.graphql.tests.fixtures import TenantApiClient
from saleor.graphql.tests.utils import get_graphql_content

ALLOWED_USAGE_QUERY = """
    {
      shop {
        limits {
          allowedUsage {
            channels
            orders
            productVariants
            staffUsers
            warehouses
          }
        }
      }
    }
"""

PARTIAL_CURRENT_USAGE = """
    {
      shop {
        limits {
          currentUsage {
            %(field)s
          }
        }
      }
    }
"""

ALL_CURRENT_USAGE = """
    {
      shop {
        limits {
          currentUsage {
            channels
            orders
            productVariants
            staffUsers
            warehouses
          }
        }
      }
    }
"""


class LimitResult(TypedDict):
    allowedUsage: dict
    currentUsage: dict


def execute_query(client: TenantApiClient, query: str) -> LimitResult:
    response = client.post_graphql(query)
    content = get_graphql_content(response)
    limits = content["data"]["shop"]["limits"]
    return limits
