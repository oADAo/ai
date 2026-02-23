from voice_perfect.align import align_segments_to_script


def test_align_prefers_later_duplicate_for_single_script_sentence():
    asr_segments = [
        {"text": "今天我們介紹產品"},
        {"text": "嗯今天我們介紹產品"},
    ]
    script = ["今天我們介紹產品"]

    result = align_segments_to_script(asr_segments, script, match_threshold=50)
    alignment = result["alignment"]

    matched = [x for x in alignment if x["operation"] == "MATCH"]
    deleted = [x for x in alignment if x["operation"] == "DELETE"]

    assert len(matched) == 1
    assert matched[0]["asr_index"] == 1
    assert any(d["asr_index"] == 0 for d in deleted)


def test_align_coverage_exposed():
    asr_segments = [{"text": "第一句"}, {"text": "第二句"}]
    script = ["第一句", "第二句"]
    result = align_segments_to_script(asr_segments, script, match_threshold=40)
    assert result["script_coverage"] > 0.9
