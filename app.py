"""
Hugging Face Spaces / standalone entrypoint for E-commerce PM OS.

This file sits at the repo root so HF Spaces auto-detects it.
Run locally:  python app.py
Run shared:   GRADIO_SHARE=1 python app.py
"""

from pm_os.gradio_app import launch

if __name__ == "__main__":
    launch()
