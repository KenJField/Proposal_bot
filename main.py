"""Main entry point for Proposal Bot."""

import json
import sys
from pathlib import Path
from typing import Any, Dict

from proposal_bot.config import get_settings
from proposal_bot.graphs.proposal_workflow import ProposalWorkflow
from proposal_bot.schemas.brief import Brief


def load_brief_from_file(brief_file: str) -> Brief:
    """
    Load a brief from a JSON file.

    Args:
        brief_file: Path to brief JSON file

    Returns:
        Brief object
    """
    with open(brief_file, "r") as f:
        brief_data = json.load(f)

    return Brief(**brief_data)


def run_proposal_workflow(brief_file: str, sales_rep_email: str = "sales@example.com") -> Dict[str, Any]:
    """
    Run the complete proposal workflow for a brief.

    Args:
        brief_file: Path to brief JSON file
        sales_rep_email: Sales representative email

    Returns:
        Final workflow state
    """
    print(f"\n{'='*80}")
    print(f"PROPOSAL BOT - LangChain Deep Agent System")
    print(f"{'='*80}\n")

    # Load brief
    print(f"📋 Loading brief from: {brief_file}")
    brief = load_brief_from_file(brief_file)
    print(f"✓ Brief loaded: {brief.title}")
    print(f"  Client: {brief.client_name}")
    print(f"  Contact: {brief.client_contact} ({brief.client_email})")
    print()

    # Initialize workflow
    print("🚀 Initializing proposal workflow...")
    workflow = ProposalWorkflow(checkpoint_db="checkpoints.db")
    print("✓ Workflow initialized")
    print()

    # Run workflow
    print("⚙️  Running workflow...\n")
    print(f"{'─'*80}")

    brief_data = brief.model_dump()
    result = workflow.run_workflow(brief_data, sales_rep_email)

    print(f"{'─'*80}\n")

    # Display results
    print("✅ Workflow completed!\n")
    print(f"Project ID: {result['project_id']}")
    print(f"Brief ID: {result['brief_id']}")
    print(f"Final Status: {result['current_step']}")
    print()

    print("📝 Workflow Messages:")
    for msg in result.get("messages", []):
        print(f"  • {msg}")
    print()

    if result.get("errors"):
        print("⚠️  Errors encountered:")
        for error in result["errors"]:
            print(f"  • {error}")
        print()

    if result.get("final_proposal"):
        print("📄 Final Proposal:")
        for key, value in result["final_proposal"].items():
            print(f"  {key}: {value}")
        print()

    print(f"{'='*80}\n")

    return result


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <brief_json_file> [sales_rep_email]")
        print()
        print("Example:")
        print("  python main.py data/briefs/example_brief_good_quality.json sales@example.com")
        print()
        print("Available example briefs:")
        print("  - data/briefs/example_brief_good_quality.json (complete brief)")
        print("  - data/briefs/example_brief_medium_quality.json (missing some details)")
        print("  - data/briefs/example_brief_poor_quality.json (very incomplete)")
        sys.exit(1)

    brief_file = sys.argv[1]
    sales_rep_email = sys.argv[2] if len(sys.argv) > 2 else "sales@example.com"

    if not Path(brief_file).exists():
        print(f"Error: Brief file not found: {brief_file}")
        sys.exit(1)

    try:
        result = run_proposal_workflow(brief_file, sales_rep_email)

        # Save result to file
        output_file = f"workflow_result_{result['project_id']}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        print(f"📁 Full workflow result saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error running workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
