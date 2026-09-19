from app.llm import NOT_FOUND_MESSAGE, build_user_message
from app.loader import Document

LEAVE = Document("leave.md", "Employees receive 25 days of paid annual leave per year.\n\nSick leave is 10 days per year.")
TRAVEL = Document("travel.md", "Hotel stays are capped at 220 dollars per night in London and New York.")


def test_ask_on_empty_index_does_not_call_llm(pipeline, fake_llm):
    answer = pipeline.ask("How much leave do I get?")
    assert not answer.grounded and answer.citations == []
    assert fake_llm.calls == []


def test_ask_retrieves_the_relevant_document_and_cites_it(pipeline, fake_llm):
    pipeline.ingest([LEAVE, TRAVEL])
    answer = pipeline.ask("How many days of annual leave per year?")
    assert answer.grounded and answer.answer == "fake answer [1]"
    assert answer.citations[0].source == "leave.md"
    assert len(fake_llm.calls) == 1


def test_irrelevant_question_short_circuits_without_calling_llm(pipeline, fake_llm):
    pipeline.ingest([LEAVE, TRAVEL])
    answer = pipeline.ask("zebra quantum trombone")
    assert answer.answer == NOT_FOUND_MESSAGE and not answer.grounded
    assert fake_llm.calls == []


def test_reingesting_a_source_replaces_instead_of_duplicating(pipeline):
    pipeline.ingest([LEAVE])
    before = pipeline.store.sources()
    pipeline.ingest([LEAVE])
    assert pipeline.store.sources() == before


def test_ingest_persists_the_index_to_disk(pipeline, settings):
    pipeline.ingest([LEAVE])
    assert (settings.index_dir / "chunks.json").exists() and (settings.index_dir / "vectors.npy").exists()


def test_prompt_numbers_passages_and_includes_the_question(pipeline):
    pipeline.ingest([LEAVE])
    results = pipeline.store.search(pipeline.embedder.embed_query("annual leave"), 3, 0.0)
    message = build_user_message("annual leave?", results)
    assert "[1] (source: leave.md)" in message and message.endswith("Question: annual leave?")


def test_seed_if_empty_indexes_a_folder_only_when_the_index_is_empty(pipeline, tmp_path):
    (tmp_path / "seed.md").write_text("The office opens at nine.", encoding="utf-8")
    pipeline.seed_if_empty(tmp_path)
    assert pipeline.store.sources() == {"seed.md": 1}
    (tmp_path / "later.md").write_text("Another file.", encoding="utf-8")
    pipeline.seed_if_empty(tmp_path)
    assert pipeline.store.sources() == {"seed.md": 1}


def test_seed_if_empty_ignores_a_missing_folder(pipeline, tmp_path):
    pipeline.seed_if_empty(tmp_path / "does-not-exist")
    assert len(pipeline.store) == 0
