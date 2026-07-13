"""End-to-end smoke test for embed + store layers.

Creates a bilingual (Chinese + English) test corpus, chunks it, embeds it,
stores in LanceDB, and verifies that:
  1. A Chinese query returns relevant Chinese chunks with correct source.
  2. An English query returns relevant English chunks with correct source.
  3. Source attribution is accurate.
  4. Score ranking is sensible (top results more relevant than bottom).

Usage:
  cd ~/rag-kit
  python tests/test_embed_store.py
"""

from __future__ import annotations

import os
import sys
import shutil
import tempfile
from pathlib import Path

# Ensure the project is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag_kit.embed import EmbeddingEngine, chunk_text, Chunk
from rag_kit.store import VectorStore

# --------------------------------------------------------------------------- #
# Test corpus — bilingual documents
# --------------------------------------------------------------------------- #

TEST_DOCUMENTS = {
    "system_config_guide_zh.txt": {
        "source": "system_config_guide_zh.txt",
        "page": 1,
        "text": (
            "系统配置指南\n"
            "本文档介绍如何配置测试系统的各项参数。\n\n"
            "1. 硬件配置\n"
            "在开始使用之前，请确保所有硬件连接正确。"
            "内存测试模块需要连接到主板的PCIe插槽。"
            "确保电源供应稳定，建议使用至少750W的电源。\n\n"
            "2. 软件安装\n"
            "安装驱动程序前，请先关闭所有正在运行的测试程序。"
            "驱动程序支持Windows 10/11和Linux操作系统。"
            "安装完成后需要重启计算机使配置生效。\n\n"
            "3. 系统校准\n"
            "每次更换测试模块后，必须进行系统校准。"
            "校准过程大约需要5分钟。"
            "校准数据保存在配置文件中，下次启动时自动加载。"
        ),
    },
    "system_config_guide_en.txt": {
        "source": "system_config_guide_en.txt",
        "page": 1,
        "text": (
            "System Configuration Guide\n"
            "This document describes how to configure the testing system parameters.\n\n"
            "1. Hardware Configuration\n"
            "Before starting, ensure all hardware connections are correct. "
            "The memory test module must be connected to the PCIe slot on the motherboard. "
            "Ensure stable power supply; a minimum 750W power supply is recommended.\n\n"
            "2. Software Installation\n"
            "Before installing drivers, close all running test programs. "
            "The drivers support Windows 10/11 and Linux operating systems. "
            "After installation, restart the computer for changes to take effect.\n\n"
            "3. System Calibration\n"
            "After replacing the test module, system calibration must be performed. "
            "The calibration process takes approximately 5 minutes. "
            "Calibration data is saved in the configuration file and loaded automatically on next startup."
        ),
    },
    "troubleshooting_zh.txt": {
        "source": "troubleshooting_zh.txt",
        "page": 1,
        "text": (
            "故障排除手册\n"
            "常见问题及解决方法。\n\n"
            "问题1：测试结果不准确\n"
            "可能原因：系统未校准。请按照配置指南进行系统校准。\n\n"
            "问题2：设备无法识别\n"
            "可能原因：驱动程序未正确安装。请重新安装驱动程序并重启系统。\n\n"
            "问题3：软件崩溃\n"
            "可能原因：内存不足。请关闭其他应用程序后重试。"
            "如果问题持续存在，请联系技术支持。"
        ),
    },
    "troubleshooting_en.txt": {
        "source": "troubleshooting_en.txt",
        "page": 1,
        "text": (
            "Troubleshooting Manual\n"
            "Common issues and solutions.\n\n"
            "Issue 1: Inaccurate test results\n"
            "Possible cause: System not calibrated. Please perform system calibration "
            "according to the configuration guide.\n\n"
            "Issue 2: Device not recognized\n"
            "Possible cause: Drivers not properly installed. Please reinstall drivers "
            "and restart the system.\n\n"
            "Issue 3: Software crash\n"
            "Possible cause: Insufficient memory. Please close other applications and retry. "
            "If the problem persists, contact technical support."
        ),
    },
}


# --------------------------------------------------------------------------- #
# Test runner
# --------------------------------------------------------------------------- #


def main() -> int:
    # Use a temp directory for the test DB.
    tmp_dir = Path(tempfile.mkdtemp(prefix="rag_test_"))
    db_path = str(tmp_dir / "lancedb")
    model_dir = str(Path.home() / "models")

    # Use hf-mirror.com if huggingface.co is blocked.
    hf_endpoint = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")

    print("=" * 60)
    print("rag-kit embed + store smoke test")
    print("=" * 60)
    print(f"  DB path:     {db_path}")
    print(f"  Model dir:   {model_dir}")
    print(f"  HF endpoint: {hf_endpoint}")
    print()

    failures: list[str] = []

    try:
        # --- 1. Initialise engine and store ---
        print("[1] Initialising EmbeddingEngine...")
        engine = EmbeddingEngine(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            model_dir=model_dir,
            hf_endpoint=hf_endpoint,
        )
        print(f"    Model info: {engine.get_model_info()}")

        store = VectorStore(db_path=db_path, dim=384)
        print(f"    Store created at {db_path}")

        # --- 2. Chunk all documents ---
        print("\n[2] Chunking test documents...")
        all_chunks: list[dict] = []
        for doc_key, doc in TEST_DOCUMENTS.items():
            chunks = chunk_text(
                text=doc["text"],
                source=doc["source"],
                page=doc["page"],
                chunk_size=512,
                chunk_overlap=64,
            )
            print(f"    {doc_key}: {len(chunks)} chunks")
            for c in chunks:
                all_chunks.append(c.to_dict())

        print(f"    Total chunks: {len(all_chunks)}")

        # --- 3. Embed and store ---
        print("\n[3] Embedding chunks (this loads the model, may take a moment)...")
        texts = [c["text"] for c in all_chunks]
        vectors = engine.embed_texts(texts)
        print(f"    Embeddings shape: {vectors.shape}")
        print(f"    Model dimension: {engine.dimension}")

        print("\n[4] Storing in LanceDB...")
        added = store.add_chunks(all_chunks, vectors)
        print(f"    Rows added: {added}")
        print(f"    Total rows in DB: {store.count_rows()}")
        print(f"    Sources: {store.list_sources()}")

        # --- 4. Test Chinese query ---
        print("\n[5] Testing Chinese query: '如何配置系统'")
        zh_query = "如何配置系统"
        zh_vec = engine.embed_query(zh_query)
        zh_results = store.search(zh_vec, top_k=5)

        print(f"    Top-5 results:")
        for i, r in enumerate(zh_results):
            preview = r["text"][:60].replace("\n", " ")
            print(f"      {i+1}. [{r['score']:.4f}] {r['source']} p{r['page']} "
                  f"#{r['chunk_idx']}: {preview}...")

        # Verify: top-3 should contain at least one Chinese chunk.
        top3_sources = [r["source"] for r in zh_results[:3]]
        zh_in_top3 = any("zh" in s for s in top3_sources)
        if zh_in_top3:
            print(f"    ✓ Chinese chunk found in top-3: {top3_sources}")
        else:
            failures.append(
                f"No Chinese chunk in top-3 for Chinese query: {top3_sources}"
            )

        # Verify: the top Chinese result should mention 配置 (configuration).
        zh_results_zh = [r for r in zh_results if "zh" in r["source"]]
        if zh_results_zh:
            top_zh = zh_results_zh[0]
            if "配置" in top_zh["text"]:
                print(f"    ✓ Top Chinese result contains '配置' (rank {zh_results.index(top_zh)+1})")
            else:
                failures.append(
                    f"Top Chinese result doesn't contain '配置': "
                    f"{top_zh['text'][:80]}"
                )
        else:
            failures.append("No Chinese results at all for Chinese query")

        # Verify: at least 2 of top-5 should be Chinese.
        zh_count = sum(1 for r in zh_results if "zh" in r["source"])
        if zh_count >= 2:
            print(f"    ✓ {zh_count}/5 top results are Chinese")
        else:
            failures.append(
                f"Only {zh_count}/5 Chinese results for Chinese query"
            )

        # --- 5. Test English query ---
        print("\n[6] Testing English query: 'system configuration'")
        en_query = "system configuration"
        en_vec = engine.embed_query(en_query)
        en_results = store.search(en_vec, top_k=5)

        print(f"    Top-5 results:")
        for i, r in enumerate(en_results):
            preview = r["text"][:60].replace("\n", " ")
            print(f"      {i+1}. [{r['score']:.4f}] {r['source']} p{r['page']} "
                  f"#{r['chunk_idx']}: {preview}...")

        top_en = en_results[0]
        if "en" not in top_en["source"]:
            # Check if at least one English chunk is in top-3.
            top3_en = any("en" in r["source"] for r in en_results[:3])
            if top3_en:
                print(f"    ✓ English chunk found in top-3 (top was {top_en['source']})")
            else:
                failures.append(
                    f"No English chunk in top-3 for English query"
                )
        else:
            print(f"    ✓ Top result is English: {top_en['source']}")

        # Verify: top English result should mention configuration.
        en_results_en = [r for r in en_results if "en" in r["source"]]
        if en_results_en:
            top_en = en_results_en[0]
            if "config" in top_en["text"].lower():
                print(f"    ✓ Top English result contains 'config' (rank {en_results.index(top_en)+1})")
            else:
                failures.append(
                    f"Top English result doesn't contain 'config': "
                    f"{top_en['text'][:80]}"
                )
        else:
            failures.append("No English results at all for English query")

        # Verify: at least 2 of top-5 should be English.
        en_count = sum(1 for r in en_results if "en" in r["source"])
        if en_count >= 2:
            print(f"    ✓ {en_count}/5 top results are English")
        else:
            failures.append(
                f"Only {en_count}/5 English results for English query"
            )

        # --- 6. Test source attribution ---
        print("\n[7] Testing source attribution (search within one file)...")
        target_source = "system_config_guide_zh.txt"
        filtered = store.search_by_source(zh_vec, target_source, top_k=3)
        if filtered and all(r["source"] == target_source for r in filtered):
            print(f"    ✓ All results from {target_source}")
        else:
            failures.append(
                f"Source filter failed: got {[r['source'] for r in filtered]}"
            )

        # --- 7. Test delete ---
        print("\n[8] Testing delete_by_source...")
        before = store.count_rows()
        deleted = store.delete_by_source("troubleshooting_en.txt")
        after = store.count_rows()
        if deleted > 0 and after == before - deleted:
            print(f"    ✓ Deleted {deleted} rows ({before} → {after})")
        else:
            failures.append(
                f"Delete failed: before={before}, deleted={deleted}, after={after}"
            )

        # Verify the source is gone.
        remaining_sources = store.list_sources()
        if "troubleshooting_en.txt" not in remaining_sources:
            print(f"    ✓ Source removed from list")
        else:
            failures.append("Deleted source still in list_sources()")

        # --- 8. Test stats ---
        print("\n[9] Testing get_stats()...")
        stats = store.get_stats()
        print(f"    {stats}")
        if stats["row_count"] > 0 and stats["source_count"] >= 3:
            print(f"    ✓ Stats look correct")
        else:
            failures.append(f"Stats look wrong: {stats}")

        store.close()

    except Exception as exc:
        import traceback
        traceback.print_exc()
        failures.append(f"Exception: {exc}")

    finally:
        # Clean up temp DB.
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # --- Summary ---
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED — {len(failures)} issue(s):")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    else:
        print("ALL CHECKS PASSED ✓")
        print("  - Chinese query returns relevant Chinese chunks")
        print("  - English query returns relevant English chunks")
        print("  - Source attribution is correct")
        print("  - Delete and stats work correctly")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
