from voice_perfect.script import split_sentences


def test_split_sentences_handles_zh_and_length():
    text = "你好，今天來測試。這是一個很長很長很長很長很長很長的句子需要切分"
    chunks = split_sentences(text, max_len=12)
    assert len(chunks) >= 3
    assert any("你好" in c for c in chunks)
