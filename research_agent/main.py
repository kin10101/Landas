#!/usr/bin/env python3
"""
Landas Research Agent - Terminal Entry Point

Usage:
    python main.py                 # Run with default config
    python main.py --format json   # Output JSON only
    python main.py --format table  # Output table only
"""

import asyncio
import argparse
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from research_runner import ResearchRunner


def main():
    parser = argparse.ArgumentParser(description="Landas Research Agent")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "table", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--save",
        type=bool,
        default=True,
        help="Save results to file (default: true)",
    )

    args = parser.parse_args()

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    # Run research
    asyncio.run(run_research(args.config, args.format, args.save))


async def run_research(config_path: str, output_format: str, save_results: bool):
    """Run the research pipeline"""
    try:
        if not os.path.exists(config_path):
            print(f"[!] Config file not found: {config_path}")
            sys.exit(1)

        runner = ResearchRunner(config_path)

        try:
            json_output, table_output, finding = await runner.run(output_format=output_format)

            if save_results and finding:
                from datetime import datetime
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

                from output_formatter import OutputFormatter

                if json_output:
                    OutputFormatter.save_to_file(
                        finding, f"research_findings_{timestamp}.json", format="json"
                    )

                if table_output:
                    OutputFormatter.save_to_file(
                        finding, f"research_findings_{timestamp}.txt", format="table"
                    )

        finally:
            await runner.cleanup()

    except KeyboardInterrupt:
        print("\n\n[!] Research interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
