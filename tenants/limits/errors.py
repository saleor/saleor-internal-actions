from graphql import GraphQLError


class LimitReachedException(GraphQLError):
    MESSAGE = "Reached plan limits of %(maximum)s %(resource)s"

    def __init__(self, *, resource_plural: str, maximum_count: int, current: int):
        self.data = {
            "maximum": maximum_count,
            "resource": resource_plural,
            "current": current,
        }
        msg = self.MESSAGE % self.data
        super().__init__(msg)
        self.extensions = {"billingPlan": self.data}
