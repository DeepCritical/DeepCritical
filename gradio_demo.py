
import os
import sys
import gradio as gr
import hydra
from omegaconf import DictConfig, OmegaConf
import asyncio

# Ensure the current directory is in python path to find DeepResearch package
sys.path.append(os.getcwd())

# Import the run_graph function
try:
    from DeepResearch.app import run_graph
except ImportError:
    # If running from a different directory structure
    try:
        from deepresearch.app import run_graph
    except ImportError:
        print("Could not import run_graph. Make sure you are in the root of the repo.")

def run_research(
    question,
    openai_key,
    anthropic_key,
    tavily_key,
    flow_selection
):
    """
    Runs the deep research workflow based on user input.
    """
    # Set environment variables
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    if anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key

    # Initialize Hydra and compose config
    # We need to point to the 'configs' directory relative to where this script is run
    # Assuming this script is run from the root of the repo

    try:
        # Clear any existing hydra instance
        hydra.core.global_hydra.GlobalHydra.instance().clear()

        with hydra.initialize(version_base=None, config_path="configs"):
            # Base config
            overrides = [
                f"question={question}",
            ]

            # Flow selection logic
            # "Default", "PRIME (Protein Engineering)", "Bioinformatics", "DeepSearch", "Challenge"

            # Reset all flows first (assuming config enables some by default)
            # Actually, looking at config.yaml, let's see what is enabled.
            # We will explicitly enable the selected flow.

            if flow_selection == "PRIME (Protein Engineering)":
                overrides.append("flows.prime.enabled=true")
            elif flow_selection == "Bioinformatics":
                overrides.append("flows.bioinformatics.enabled=true")
            elif flow_selection == "DeepSearch":
                overrides.append("flows.deepsearch.enabled=true")
            elif flow_selection == "Challenge":
                overrides.append("challenge.enabled=true")
            elif flow_selection == "RAG":
                overrides.append("flows.rag.enabled=true")

            # Compose config
            cfg = hydra.compose(config_name="config", overrides=overrides)

            # Run the graph
            result = run_graph(question, cfg)
            return result

    except Exception as e:
        return f"Error occurred: {str(e)}\n\nTraceback:\n{import_traceback()}"

def import_traceback():
    import traceback
    return traceback.format_exc()

# Define Gradio Interface
with gr.Blocks(title="DeepCritical Research Agent") as demo:
    gr.Markdown("# DeepCritical Research Agent")
    gr.Markdown("An autonomous research agent powered by Hydra and Pydantic Graph.")

    with gr.Row():
        with gr.Column():
            openai_key = gr.Textbox(label="OpenAI API Key", type="password", placeholder="sk-...")
            anthropic_key = gr.Textbox(label="Anthropic API Key", type="password", placeholder="sk-ant-...")
            tavily_key = gr.Textbox(label="Tavily API Key", type="password", placeholder="tvly-...")

    with gr.Row():
        question = gr.Textbox(label="Research Question", placeholder="e.g. What are the core contributions of the PRIME paper?", lines=3)

    with gr.Row():
        flow_selection = gr.Dropdown(
            choices=["Default", "PRIME (Protein Engineering)", "Bioinformatics", "DeepSearch", "Challenge", "RAG"],
            value="Default",
            label="Research Flow"
        )

    submit_btn = gr.Button("Start Research", variant="primary")

    output = gr.Markdown(label="Research Report")

    submit_btn.click(
        fn=run_research,
        inputs=[question, openai_key, anthropic_key, tavily_key, flow_selection],
        outputs=output
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=True)
