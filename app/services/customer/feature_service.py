"""Customer feature gate helpers for future paid expansion."""

from app.constants.identity import CUSTOMER_TIER_FREE, FREE_FEATURES


def can_use_feature(customer, feature_name):
    """Return whether a customer can use a named feature."""
    if not customer or not feature_name:
        return False
    extra_functions = customer.extra_functions or {}
    if extra_functions.get(feature_name) is True:
        return True
    if customer.tier == CUSTOMER_TIER_FREE:
        return feature_name in FREE_FEATURES
    return True
