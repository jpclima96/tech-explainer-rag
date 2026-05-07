"""Domain exceptions raised by the fact-checking pipeline."""


class FactCheckError(Exception):
    """Base error for the fact-checker package."""


class LLMOutputError(FactCheckError):
    """Raised when the LLM returns malformed or unparseable output."""


class RetrieverError(FactCheckError):
    """Raised when the retriever fails to fetch evidence."""
