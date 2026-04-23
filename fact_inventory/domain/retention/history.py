"""History-based fact retention policy domain objects.

Domain objects expressing retention rules independently of persistence
mechanisms. No framework or ORM imports.

Notes
-----
Domain objects represent core business concepts. By isolating business
rules here, they can be:

- Unit tested without mocking the database or ORM
- Reused across different services and versions
- Updated in response to business requirement changes without touching storage
"""

__all__ = ["HistoryRetentionPolicy"]


class HistoryRetentionPolicy:
    """Encapsulates per-client fact history retention policy as a domain concept.

    Validates that history retention limits are within acceptable bounds and
    provides access to the maximum number of fact records to keep per client.

    Notes
    -----
    Keeps at most max_entries fact records per client_address, deleting the
    oldest records when a client exceeds this limit. This approach prevents
    unbounded growth of historical records while retaining recent facts for
    each client.

    Examples
    --------
    >>> policy = HistoryRetentionPolicy(max_entries=100)
    >>> max_entries = policy.max_entries
    >>> # Pass policy to repository for deletion
    """

    MIN_ENTRIES = 1
    MAX_ENTRIES = 1000

    def __init__(self, max_entries: int) -> None:
        """Initialize history-based retention policy.

        Parameters
        ----------
        max_entries : int
            Maximum number of fact records to retain per client_address.
            Must be between ``MIN_ENTRIES`` and ``MAX_ENTRIES``, inclusive.

        Raises
        ------
        ValueError
            If max_entries is outside the valid range defined by ``MIN_ENTRIES``
            and ``MAX_ENTRIES``.
        """
        if max_entries < self.MIN_ENTRIES or max_entries > self.MAX_ENTRIES:
            raise ValueError(  # noqa: TRY003
                f"Max entries must be between {self.MIN_ENTRIES} "
                f"and {self.MAX_ENTRIES}, got {max_entries}"
            )
        self._max_entries = max_entries

    @property
    def max_entries(self) -> int:
        """Return the maximum number of fact records retained per client_address.

        Returns
        -------
        int
            Maximum number of fact records to keep per client_address.
        """
        return self._max_entries

    def __repr__(self) -> str:  # pragma: no cover
        """Return string representation of the HistoryRetentionPolicy instance.

        Returns
        -------
        str
            Formatted string showing the retention policy configuration.
        """
        return f"HistoryRetentionPolicy(max_entries={self._max_entries})"
