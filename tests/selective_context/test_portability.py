from selective_context.portability.game24_dataset import normalize_rows


def test_game24_builder_preserves_source_revision():
    row = list(normalize_rows([{"Puzzles": "6 2 3 3"}], "nlile/24-game", "pinned-revision"))[0]
    assert row["answer"] == [6, 2, 3, 3]
    assert row["dataset_provenance"]["revision"] == "pinned-revision"
