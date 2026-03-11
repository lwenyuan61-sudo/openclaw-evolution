from core.engine import WorkflowEngine
import sys

# Make Windows console output robust
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <workflow.yaml>")
        sys.exit(2)
    wf_path = sys.argv[1]
    engine = WorkflowEngine()
    result = engine.run_from_file(wf_path)
    print("\n=== FINAL RESULT ===")
    print(result)


if __name__ == "__main__":
    main()
