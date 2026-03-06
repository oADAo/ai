# voice_perfect

本地離線的「對照文稿」口播 WAV 自動剪輯工具（加強 AI 對齊版）。

## 系統需求
- Python 3.10+
- ffmpeg / ffprobe 在 PATH 中可執行
- 本機可安裝 `faster-whisper` 模型

## 安裝
```bash
pip install -r requirements.txt
```

## CLI
```bash
python -m voice_perfect --audio input.wav --script script.txt --out out_dir
```

可選參數：
- `--run-ffmpeg`
- `--model` (default: `small`)
- `--language` (default: `zh`)
- `--silence-db` (default: `-35`)
- `--silence-dur` (default: `0.35`)
- `--pad` (default: `0.08`)
- `--merge-gap` (default: `0.20`)
- `--max-seg-sec` (default: `12`)
- `--match-threshold` (default: `60`，越高越嚴格)
- `--min-script-coverage` (default: `0.55`)
- `--min-keep-ratio` (default: `0.35`)

## 智能強化重點
1. 中英文混合 normalization + 改善分句（支援 `.` 句尾）
2. 對齊時會弱化口頭禪（嗯/呃/這個/那個…）影響
3. 若 ASR 提供詞級時間戳，MATCH 段會嘗試裁掉段首段尾 filler
4. 加入品質保護：對齊覆蓋率過低或輸出過短，會自動退回靜音剪輯 fallback（避免被剪到只剩一小段）

## 輸出
在 `out_dir/` 會生成：
- `plan.json`
- `ffmpeg_cmd_mac.sh`
- `ffmpeg_cmd_win.ps1`
- `README_run.md`
- `final.wav`（僅在 `--run-ffmpeg` 啟用時）

## 流程摘要
1. ffmpeg 將輸入 WAV 轉成 16k mono
2. ffmpeg `silencedetect` 解析靜音區段
3. `faster-whisper` 取得 ASR segments + words
4. 文稿 normalization + 切句
5. DP 單調對齊（MATCH/DELETE/INSERT）
6. 由 MATCH 生成 keep intervals（filler trim + pad/merge/split）
7. 產出 plan 與 ffmpeg 命令

## 對齊失敗 fallback
若 ASR/對齊流程失敗，或品質門檻未達，程式會自動退回「只刪長靜音」模式，仍輸出 `plan.json` 與 ffmpeg 指令。

## 測試
```bash
pytest -q
```
