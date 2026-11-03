"""Held-out dialogue evaluation for the SANDEV Brain teacher research path.

This evaluates output structure and action-boundary compliance. It deliberately
does not claim to score naturalness, reasoning quality, or LLM-level dialogue;
those require a separate human-reviewed rubric and a larger untouched set.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from sandev_brain import _extract_json, validate_response

_ACTIONS_RE = re.compile(r"aksi\\s+valid\\s*:\\s*([A-Za-z0-9_, -]+)", re.IGNORECASE)


class EvaluationError(ValueError):
    """Raised when an evaluation dataset is malformed."""


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"line {line_number}: invalid JSON") from exc
        messages = row.get("messages") if isinstance(row, dict) else None
        if not isinstance(messages, list) or len(messages) < 2:
            raise EvaluationError(f"line {line_number}: messages must contain at least two entries")
        if any(not isinstance(item, dict) or item.get("role") not in {"system", "user", "assistant"}
               or not isinstance(item.get("content"), str) for item in messages):
            raise EvaluationError(f"line {line_number}: malformed chat message")
        if messages[-1]["role"] != "assistant":
            raise EvaluationError(f"line {line_number}: final message must be the reference assistant answer")
        user_text = " ".join(item["content"] for item in messages if item["role"] == "user")
        match = _ACTIONS_RE.search(user_text)
        if not match:
            raise EvaluationError(f"line {line_number}: user message must declare 'Aksi valid:'")
        valid_actions = [part.strip() for part in re.split(r"[, ]+", match.group(1)) if part.strip()]
        if not valid_actions:
            raise EvaluationError(f"line {line_number}: valid action list is empty")
        try:
            expected = validate_response(messages[-1]["content"], valid_actions)
        except (ValueError, TypeError) as exc:
            raise EvaluationError(f"line {line_number}: invalid reference assistant JSON") from exc
        cases.append({
            "case_id": f"line_{line_number}",
            "messages": messages[:-1],
            "valid_actions": valid_actions,
            "expected": expected,
        })
    if not cases:
        raise EvaluationError("evaluation dataset is empty")
    return cases


def score_prediction(raw: str, expected: Mapping[str, Any],
                     valid_actions: Iterable[str]) -> dict[str, Any]:
    allowed = set(valid_actions)
    parsed: dict[str, Any] | None = None
    normalized: dict[str, Any] | None = None
    parse_error = None
    try:
        parsed = _extract_json(raw)
        normalized = validate_response(raw, list(allowed))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        parse_error = str(exc)

    raw_action = parsed.get("action") if parsed is not None else None
    if raw_action is None:
        action_valid = parsed is not None
    elif isinstance(raw_action, dict):
        kind = raw_action.get("type")
        target = raw_action.get("target", "")
        action_valid = (kind is None or (isinstance(kind, str) and kind in allowed)) and isinstance(target, str)
    else:
        action_valid = False

    predicted_action = normalized.get("action") if normalized is not None else None
    expected_action = expected.get("action")
    say = normalized.get("say", "") if normalized is not None else ""
    return {
        "json_valid": parsed is not None,
        "say_nonempty": isinstance(say, str) and bool(say.strip()),
        "action_valid": action_valid,
        "action_match": predicted_action == expected_action if normalized is not None else False,
        "predicted_action": predicted_action,
        "expected_action": expected_action,
        "say": say,
        "parse_error": parse_error,
    }


def summarize_scores(scores: list[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(scores)
    if not total:
        raise EvaluationError("cannot summarize an empty score list")
    keys = ("json_valid", "say_nonempty", "action_valid", "action_match")
    counts = {key: sum(bool(row.get(key)) for row in scores) for key in keys}
    return {
        "total": total,
        "counts": counts,
        "rates": {key: value / total for key, value in counts.items()},
        "scope": [
            "JSON validity and response structure",
            "non-empty dialogue output",
            "valid-action boundary compliance",
            "exact action agreement with the small authored reference",
        ],
        "not_measured": [
            "naturalness or fluency",
            "semantic correctness of the dialogue",
            "reasoning quality",
            "long-conversation consistency",
            "generalization to unseen language",
        ],
    }


def _generate(model: Any, tokenizer: Any, messages: list[dict[str, str]],
              *, torch: Any, max_new_tokens: int) -> str:
    encoded = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    )
    device = next(model.parameters()).device
    encoded = {key: value.to(device) for key, value in encoded.items()}
    with torch.inference_mode():
        output = model.generate(
            **encoded, max_new_tokens=max_new_tokens, do_sample=False,
            pad_token_id=tokenizer.eos_token_id, use_cache=True,
        )
    prompt_length = encoded["input_ids"].shape[1]
    return tokenizer.decode(output[0, prompt_length:], skip_special_tokens=True)


def evaluate_model(*, data_path: str, model_id: str, adapter_path: str | None,
                   output_dir: str, max_new_tokens: int = 160) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cases = load_cases(data_path)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype="auto", low_cpu_mem_usage=True
    )
    if adapter_path:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter_path)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    results = []
    for case in cases:
        raw = _generate(model, tokenizer, case["messages"], torch=torch,
                        max_new_tokens=max_new_tokens)
        score = score_prediction(raw, case["expected"], case["valid_actions"])
        results.append({
            "case_id": case["case_id"],
            "raw_output": raw,
            **score,
        })

    summary = summarize_scores(results)
    summary.update({"model_id": model_id, "adapter_path": adapter_path})
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (destination / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="smollm/data/eval.jsonl")
    parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-360M-Instruct")
    parser.add_argument("--adapter", default=None, help="Optional trained PEFT adapter directory")
    parser.add_argument("--output-dir", default="outputs/evaluation")
    parser.add_argument("--max-new-tokens", type=int, default=160)
    args = parser.parse_args()
    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    summary = evaluate_model(
        data_path=args.data, model_id=args.model, adapter_path=args.adapter,
        output_dir=args.output_dir, max_new_tokens=args.max_new_tokens,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
