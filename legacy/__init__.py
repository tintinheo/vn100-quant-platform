"""Import trap for retired artifacts.

The legacy directory is retained for audit history only. It is deliberately not
part of the ``vnquant`` distribution and must never become executable runtime.
"""

raise ImportError(
    "legacy artifacts are historical and disabled; use the active vnquant package"
)
