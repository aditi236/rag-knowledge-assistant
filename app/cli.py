"""Command-line interface: ingest a folder, ask a question, or show index stats."""
import argparse
from pathlib import Path

from app.config import Settings
from app.loader import load_directory
from app.rag import build_pipeline


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
        result = pipeline.ask(args.question)
        print(result.answer)
        for number, citation in enumerate(result.citations, start=1):
            print(f"  [{number}] {citation.source} (chunk {citation.chunk_index}, score {citation.score})")


if __name__ == "__main__":
    main()
