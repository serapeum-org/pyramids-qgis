"""Processing-pipeline (``process``) algorithms.

File-output operations that drive the pyramids processing registry: run a declarative pipeline
over an input (``run``) or apply one registered tool to an input (``apply``). Both wrap the
``pyramids process`` CLI.

The read-only ``process tool`` commands (``list``, ``show``) are not exposed as algorithms —
they only list/inspect the registered tools rather than producing an output.
"""
