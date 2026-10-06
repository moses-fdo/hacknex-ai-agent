import asyncio
import argparse
import sys
import time
from backend.models.schema import RunRequest, ModelSettings, AgentEvent, EventType
from backend.engine.orchestrator import MasterOrchestrator

# ANSI Colors for Terminal Antigravity UI
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
   █████╗ ███████╗████████╗██╗  ██╗███████╗██████╗       ███████╗██╗    ██╗███████╗
  ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗      ██╔════╝██║    ██║██╔════╝
  ███████║█████╗     ██║   ███████║█████╗  ██████╔╝█████╗███████╗██║ █╗ ██║█████╗  
  ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══██╗╚════╝╚════██║██║███╗██║██╔══╝  
  ██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║      ███████║╚███╔███╔╝███████╗
  ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝      ╚══════╝ ╚══╝╚══╝ ╚══════╝
{RESET}{DIM}  Autonomous Software Engineering Multi-Persona Agent (Antigravity-Grade){RESET}
"""

async def run_cli(repo_path: str, issue: str, provider: str):
    print(BANNER)
    print(f"{BOLD}Target Repo:{RESET} {repo_path}")
    print(f"{BOLD}Mission:{RESET}     {issue}")
    print(f"{BOLD}Provider:{RESET}    {provider.upper()}\n")

    orchestrator = MasterOrchestrator()
    queue = orchestrator.event_bus.subscribe()

    async def event_printer():
        while True:
            event: AgentEvent = await queue.get()
            t_str = time.strftime('%H:%M:%S', time.localtime(event.timestamp))

            if event.event_type == EventType.PERSONA_START:
                print(f"\n{BLUE}[{t_str}] ──► {BOLD}{event.persona.value if event.persona else 'Agent'}{RESET} ({event.squad.value if event.squad else ''})")
            elif event.event_type == EventType.THOUGHT:
                p_name = event.persona.value if event.persona else "Engine"
                print(f"  {MAGENTA}💭 [{p_name}]{RESET} {DIM}{event.content}{RESET}")
            elif event.event_type == EventType.TOOL_CALL:
                print(f"  {CYAN}⚡ {event.title}{RESET}: {DIM}{event.content}{RESET}")
            elif event.event_type == EventType.TOOL_RESULT:
                print(f"  {GREEN}✓ {event.title}{RESET}: {event.content}")
            elif event.event_type == EventType.DIFF_GENERATED:
                print(f"\n{YELLOW}{BOLD}─── SURGICAL PATCH PREVIEW ───{RESET}")
                for line in event.content.splitlines():
                    if line.startswith("+"):
                        print(f"{GREEN}{line}{RESET}")
                    elif line.startswith("-"):
                        print(f"{RED}{line}{RESET}")
                    else:
                        print(f"{DIM}{line}{RESET}")
            elif event.event_type == EventType.VERDICT:
                print(f"\n{GREEN}{BOLD}======================================================{RESET}")
                print(f"{GREEN}{BOLD}  {event.title}{RESET}")
                print(f"{GREEN}  {event.content}{RESET}")
                print(f"{GREEN}{BOLD}======================================================{RESET}\n")
            elif event.event_type == EventType.PIPELINE_COMPLETE:
                break

    printer_task = asyncio.create_task(event_printer())

    request = RunRequest(
        repo_path=repo_path,
        issue_description=issue,
        model_settings=ModelSettings(provider_type=provider)
    )

    state = await orchestrator.run(request)
    await printer_task

    print(f"\n{CYAN}{BOLD}─── SCRIBE EXECUTIVE DOSSIER ───{RESET}")
    print(state["final_artifact"].markdown_report)

def main():
    parser = argparse.ArgumentParser(description="Aether-SWE Autonomous Software Engineering Agent")
    parser.add_argument("--repo", default="benchmarks/ecommerce_api", help="Path to target repository")
    parser.add_argument("--issue", default="In app/auth/tokens.py, token expiration validation uses naive local time instead of timezone-aware UTC, causing tokens to prematurely expire. Fix this to use timezone.utc, ensuring all 24 existing tests pass.", help="Task or bug description")
    parser.add_argument("--provider", default="simulation", choices=["anthropic", "openai_compatible", "ollama", "simulation"], help="LLM Provider")
    args = parser.parse_args()

    asyncio.run(run_cli(args.repo, args.issue, args.provider))

if __name__ == "__main__":
    main()
