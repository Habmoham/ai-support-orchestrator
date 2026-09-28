"""
Langfuse tracing setup.

Isolated in its own module so the rest of the graph code doesn't need to
know about tracing internals. If Langfuse keys aren't set, get_langfuse_handler()
returns None and the graph runs exactly the same, just without traces -
tracing is an add-on, not a dependency the app can't run without.
"""

import os


def get_langfuse_handler():
    if not os.environ.get("LANGFUSE_PUBLIC_KEY") or not os.environ.get("LANGFUSE_SECRET_KEY"):
        return None

    from langfuse.langchain import CallbackHandler

    return CallbackHandler()
