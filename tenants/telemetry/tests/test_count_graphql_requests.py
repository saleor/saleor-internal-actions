from unittest.mock import MagicMock, call, patch

import pytest

from .. import Telemetry


@pytest.fixture
def mocked_gql_request_counter() -> MagicMock:
    with patch.object(Telemetry._gql_request_counter, "add") as mocked:
        yield mocked


def test_increment_graphql_request_count(mocked_gql_request_counter):
    """Test the behavior is as expected: calls ``counter.add(...)``"""
    Telemetry.inc_gql_request_count(123, {"label": "value"})
    mocked_gql_request_counter.assert_called_once_with(123, {"label": "value"})


def test_graphql_request_increments_tenant_request_counter(
    api_client, mocked_gql_request_counter, request: pytest.FixtureRequest
):
    """
    Ensures a middleware is incrementing the request count on the graphql middleware level
    """

    response = api_client.post_graphql("{ __typename }")
    assert response.status_code == 200

    request.getfixturevalue("as_other_tenant")
    other_api_client = request.getfixturevalue("other_tenant_api_client")
    response = other_api_client.post_graphql("{ __typename }")
    assert response.status_code == 200

    # (<increment>, <labels>)
    expected_calls = [
        call(1, {"host": "mirumee.com", "project_id": 23}),
        call(1, {"host": "othertenant.com", "project_id": 54}),
    ]

    mocked_gql_request_counter.assert_has_calls(expected_calls)


def test_non_graphql_request_does_not_increment_gql_counter(
    api_client, mocked_gql_request_counter
):
    """
    Ensures the middleware in charge of counting GraphQL requests does not increment
    other requests than graphql.
    """

    response = api_client.get("/")
    assert response.status_code == 200
    mocked_gql_request_counter.assert_not_called()
