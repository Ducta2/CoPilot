"""Read-only portal users: a minimal stand-in for upstream's #1312.

Upstream lets a ``customer_user`` be read-only for one of their customers through a
``user_customer_access.read_only`` column, and every portal write asks ``is_read_only_for``.
This base has no such column, so nobody is read-only yet: ``is_read_only_for`` always answers
``False``. It exists so the code backported from upstream ("Ask the SOC", #1305) keeps its
check in place; replace this module with upstream's when the ``read_only`` column is backported.
"""

from typing import Any
from typing import Optional

READ_ONLY = "Your account can view this customer's data but not change it."


async def is_read_only_for(user: Any, customer_code: Optional[str], session: Any) -> bool:
    """Temporary: always ``False`` until the ``read_only`` column exists on this base."""
    return False
