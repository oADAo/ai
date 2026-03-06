from voice_perfect.script import split_sentences, strip_fillers_for_match


def test_split_sentences_handles_zh_and_length():
    text = "你好，今天來測試。這是一個很長很長很長很長很長很長的句子需要切分"
    chunks = split_sentences(text, max_len=12)
    assert len(chunks) >= 3
    assert any("你好" in c for c in chunks)


def test_split_sentences_handles_ascii_period_after_normalization():
    text = "第一句。第二句。第三句"
    chunks = split_sentences(text, max_len=50)
    assert len(chunks) == 3


def test_strip_fillers_for_match_removes_common_fillers():
    assert strip_fillers_for_match("嗯 這個 我們開始") == "我們開始"
