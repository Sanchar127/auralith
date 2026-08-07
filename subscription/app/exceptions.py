class SubscriptionError(Exception):
    pass


class SubscriptionNotFoundError(SubscriptionError):
    pass


class SubscriptionAlreadyActiveError(SubscriptionError):
    pass


class InsufficientTokensError(SubscriptionError):
    pass

class SubscriptionPlanError(Exception):
    """Base exception for subscription plans."""


class SubscriptionPlanNotFoundError(SubscriptionPlanError):
    """Raised when a subscription plan is not found."""


class SubscriptionPlanAlreadyExistsError(SubscriptionPlanError):
    """Raised when creating a duplicate subscription plan."""