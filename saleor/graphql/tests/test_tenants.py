from saleor.graphql.tests.utils import get_graphql_content
from saleor.core.jwt import jwt_decode


def test_tenant_aware_token_creation(
    tenant_connection_keeper,
    api_client,
    other_tenant_api_client,
    staff_user,
    settings
):
    query = """
    mutation TokenCreate($email: String!, $password: String!) {
        tokenCreate(email: $email, password: $password) {
            token
            errors {
                field
                message
            }
        }
    }
    """
    variables = {"email": staff_user.email, "password": "password"}

    response = api_client.post_graphql(query, variables)
    content = get_graphql_content(response)
    token_data = content["data"]["tokenCreate"]
    token = jwt_decode(token_data["token"])
    assert token["email"] == staff_user.email
    assert token_data["errors"] == []

    response = other_tenant_api_client.post_graphql(query, variables)
    content = get_graphql_content(response)
    token_data = content["data"]["tokenCreate"]
    errors = token_data["errors"]
    assert errors
    assert errors[0]["message"] == "Please, enter valid credentials"
    assert not token_data["token"]
