# ==============================================================
# main.py — CLI Entry Point for Testing
# ==============================================================

import sys
from src.graph.workflow import run_agent


def run_cli():
    """
    Interactive CLI to test the customer service agent.
    Type your question, get an answer.
    Type 'exit' to quit.
    """
    print("=" * 60)
    print("  🎧 Customer Service Agent — CLI Test Mode")
    print("  Supports Arabic & English")
    print("  Type 'exit' to quit")
    print("=" * 60)

    customer_id = None
    cid = input("\n👤 Enter your customer ID (press Enter to skip): ").strip()
    if cid.isdigit():
        customer_id = int(cid)
        print(f"✅ Customer ID set: {customer_id}")

    print()

    while True:
        try:
            message = input("💬 Your message: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

        if not message:
            continue

        if message.lower() in ("exit", "quit", "خروج"):
            print("👋 Goodbye!")
            break

        print("\n⏳ Thinking...\n")
        result = run_agent(message=message, customer_id=customer_id)

        print(f"{'─' * 55}")
        print(f"🎯 Intent      : {result['intent']}")
        print(f"⚡ Action      : {result['action_taken']}")
        print(f"🤖 LLM Used    : {result['llm_used']}")
        print(f"{'─' * 55}")
        print(f"💬 Answer:\n\n{result['answer']}")
        print(f"{'─' * 55}\n")


if __name__ == "__main__":
    run_cli()