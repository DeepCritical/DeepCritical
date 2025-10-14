SYSTEM = (
    "You are a search engine result analyzer. You look at the SERP API response and group them into meaningful cluster.\n\n"
    "Each cluster should contain a summary of the content, key data and insights, the corresponding URLs and search advice. Respond in JSON format.\n"
)


SERP_CLUSTER_PROMPTS: dict[str, str] = {
    "system": SYSTEM,
    "cluster_results": "Cluster the following search results: {results}",
    "analyze_serp": "Analyze SERP results and create meaningful clusters: {serp_data}",
}


class SerpClusterPrompts:
    """Prompt templates for SERP clustering operations."""

    SYSTEM = SYSTEM
    PROMPTS = SERP_CLUSTER_PROMPTS
