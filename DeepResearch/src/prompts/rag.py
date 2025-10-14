"""
RAG (Retrieval-Augmented Generation) prompts for DeepCritical research workflows.

This module defines prompt templates for RAG operations including general RAG queries
and specialized bioinformatics RAG queries.
"""

# General RAG query prompt template
RAG_QUERY_PROMPT = """Based on the following context, please answer the question: {query}

Context:
{context}

Answer:"""

# Bioinformatics-specific RAG query prompt template
BIOINFORMATICS_RAG_QUERY_PROMPT = """Based on the following bioinformatics data, please provide a comprehensive answer to: {query}

Context from bioinformatics databases:
{context}

Please provide:
1. A direct answer to the question
2. Key findings from the data
3. Relevant gene symbols, GO terms, or other identifiers mentioned
4. Confidence level based on the evidence quality

Answer:"""

# Prompt templates dictionary for easy access
RAG_PROMPTS: dict[str, str] = {
    "rag_query": RAG_QUERY_PROMPT,
    "bioinformatics_rag_query": BIOINFORMATICS_RAG_QUERY_PROMPT,
}


class RAGPrompts:
    """Prompt templates for RAG operations."""

    # Prompt templates
    RAG_QUERY = RAG_QUERY_PROMPT
    BIOINFORMATICS_RAG_QUERY = BIOINFORMATICS_RAG_QUERY_PROMPT
    PROMPTS = RAG_PROMPTS

    @classmethod
    def get_rag_query_prompt(cls, query: str, context: str) -> str:
        """Get formatted RAG query prompt."""
        return cls.PROMPTS["rag_query"].format(query=query, context=context)

    @classmethod
    def get_bioinformatics_rag_query_prompt(cls, query: str, context: str) -> str:
        """Get formatted bioinformatics RAG query prompt."""
        return cls.PROMPTS["bioinformatics_rag_query"].format(
            query=query, context=context
        )
