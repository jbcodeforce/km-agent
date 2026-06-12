def __getattr__(name: str):
    if name == "compiler":
        from kma.agents.compiler import get_compiler

        return get_compiler()
    if name == "linter":
        from kma.agents.linter import get_linter

        return get_linter()
    if name == "navigator":
        from kma.agents.navigator import get_navigator

        return get_navigator()
    if name == "researcher":
        from kma.agents.researcher import get_researcher

        return get_researcher()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["navigator", "researcher", "compiler", "linter", "get_compiler", "get_linter", "get_navigator", "get_researcher"]
