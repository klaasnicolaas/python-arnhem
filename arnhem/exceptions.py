"""Asynchronous Python client providing Open Data information of Arnhem."""


class ODPArnhemError(Exception):
    """Generic Open Data Platform Arnhem exception."""


class ODPArnhemConnectionError(ODPArnhemError):
    """Open Data Platform Arnhem - connection exception."""


class ODPArnhemNoResultsError(ODPArnhemError):
    """Open Data Platform Arnhem - no results found exception."""
