from kritzellm.core.chunking import MAX_WORDS, Chunk, chunk_blocks


def words(count: int, word: str = "Wort") -> str:
    return " ".join([word] * count)


def sizes(chunks: list[Chunk]) -> list[int]:
    return [len(chunk.text.split()) for chunk in chunks]


def test_a_page_without_text_has_no_chunks() -> None:
    assert chunk_blocks([]) == []
    assert chunk_blocks([("a", " \n ")]) == []


def test_short_blocks_share_a_chunk_as_written() -> None:
    blocks = [("a", "14. März"), ("b", "- Brot\n- Milch"), ("c", "Kaffee mit [?].")]

    assert chunk_blocks(blocks) == [
        Chunk(("a", "b", "c"), "14. März\n\n- Brot\n- Milch\n\nKaffee mit [?].")
    ]


def test_chunks_stay_under_the_maximum_and_keep_the_order() -> None:
    blocks = [(name, words(200, name)) for name in "abc"]

    chunks = chunk_blocks(blocks)

    assert [chunk.block_ids for chunk in chunks] == [("a",), ("b",), ("c",)]
    assert sizes(chunks) == [200, 200, 200]


def test_a_long_block_is_split_evenly() -> None:
    chunks = chunk_blocks([("a", words(800)), ("b", words(10, "Ende"))])

    assert [chunk.block_ids for chunk in chunks] == [("a",), ("a",), ("a", "b")]
    assert sizes(chunks) == [267, 267, 266 + 10]
    assert all(size <= MAX_WORDS for size in sizes(chunks))


def test_a_short_last_chunk_takes_blocks_from_the_one_before() -> None:
    blocks = [("a", words(150)), ("b", words(150)), ("c", words(100))]

    chunks = chunk_blocks(blocks)

    assert [chunk.block_ids for chunk in chunks] == [("a",), ("b", "c")]
    assert sizes(chunks) == [150, 250]


def test_a_short_last_chunk_stays_when_nothing_can_move() -> None:
    chunks = chunk_blocks([("a", words(340)), ("b", words(20))])

    assert [chunk.block_ids for chunk in chunks] == [("a",), ("b",)]
