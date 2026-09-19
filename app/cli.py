"""Command-line interface: ingest a folder, ask a question, or show index stats."""
import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):  # launched as a plain file, e.g. VS Code's "Run Python File" button
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.llm import MissingCredentialsError  # noqa: E402
from app.loader import load_directory  # noqa: E402
from app.rag import build_pipeline  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="index every .txt/.md/.pdf in a folder")
    ingest.add_argument("directory", type=Path)
    ask = commands.add_parser("ask", help="ask a question about the indexed documents")
    ask.add_argument("question")
    commands.add_parser("stats", help="show what is in the index")
    args = parser.parse_args(argv)

    pipeline = build_pipeline(Settings())
    if args.command == "ingest":
        print(pipeline.ingest(load_directory(args.directory)))
    elif args.command == "stats":
        print(pipeline.store.sources())
    else:
        try:
            result = pipeline.ask(args.question)
        except MissingCredentialsError as exc:
            raise SystemExit(f"error: {exc} (or set LLM_PROVIDER=extractive to run offline)") from exc
        print(result.answer)
        for number, citation in enumerate(result.citations, start=1):
            print(f"  [{number}] {citation.source} (chunk {citation.chunk_index}, score {citation.score})")


if __name__ == "__main__":
    main()
