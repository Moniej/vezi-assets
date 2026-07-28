"""LIM-3 diagnosis (owner directive, 2026-07-28): verify -- not assume --
whether prompt-label leakage / full-sequence loss masking explains the
entity_recognition "Coca-Cola" collapse observed in LIM-3's benchmark.
READ-ONLY: imports the real, unmodified training.py/dataset_loader.py code
and inspects real tensors for real registered examples. Makes no change to
the training pipeline.

  lim_training/venv/Scripts/python.exe scripts/lim/diagnose_training_pipeline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

BASE_MODEL_DIR = ROOT / "lim_training" / "qwen3_4b_model"


def main():
    from ngxrot.lim import dataset_loader, registry
    from ngxrot.lim.training import _JsonlExampleDataset, _format_example_text

    con_lim = registry.init_registry()
    resolved, examples = dataset_loader.load_examples(con_lim, "entity_recognition",
                                                       "entity_recognition-v1.0.0")
    print(f"Loaded {len(examples)} accepted examples from {resolved}\n")

    from unsloth import FastLanguageModel
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(BASE_MODEL_DIR), max_seq_length=256, load_in_4bit=True, dtype=None)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("=== 1. Tokenizer configuration actually in effect at training time ===")
    print(f"  pad_token       = {tokenizer.pad_token!r}  (id={tokenizer.pad_token_id})")
    print(f"  eos_token       = {tokenizer.eos_token!r}  (id={tokenizer.eos_token_id})")
    print(f"  padding_side    = {tokenizer.padding_side!r}")
    print(f"  pad_token_id == eos_token_id ? {tokenizer.pad_token_id == tokenizer.eos_token_id}")

    print("\n=== 2. Prompt construction: exact text fed to the tokenizer ===")
    ex0 = examples[0]
    full_text = _format_example_text(ex0, tokenizer.eos_token)
    print(repr(full_text))

    print("\n=== 3. Where does the RESPONSE start, in raw characters? ===")
    response_marker = "### Response:\n"
    marker_pos = full_text.index(response_marker) + len(response_marker)
    prompt_only = full_text[:marker_pos]
    response_only = full_text[marker_pos:]
    print(f"  prompt_only  chars=[0:{marker_pos}]: {prompt_only!r}")
    print(f"  response_only chars=[{marker_pos}:]: {response_only!r}")

    print("\n=== 4. Tokenize prompt-only vs full text to find the exact response TOKEN boundary ===")
    prompt_ids = tokenizer(prompt_only, add_special_tokens=True)["input_ids"]
    n_prompt_tokens = len(prompt_ids)
    print(f"  n_prompt_tokens (instruction+context+'### Response:\\n') = {n_prompt_tokens}")

    print("\n=== 5. Build the REAL training example exactly as _JsonlExampleDataset does ===")
    ds = _JsonlExampleDataset([ex0], tokenizer, max_length=256)
    item = ds[0]
    input_ids = item["input_ids"]
    attention_mask = item["attention_mask"]
    labels = item["labels"]
    print(f"  input_ids.shape = {tuple(input_ids.shape)}")
    print(f"  attention_mask.shape = {tuple(attention_mask.shape)}")
    print(f"  labels.shape = {tuple(labels.shape)}")

    n_total = input_ids.shape[0]
    n_real_tokens = int(attention_mask.sum().item())
    n_pad_tokens = n_total - n_real_tokens
    print(f"\n  n_total_positions = {n_total}")
    print(f"  n_real_tokens (attention_mask==1) = {n_real_tokens}")
    print(f"  n_pad_tokens (attention_mask==0) = {n_pad_tokens}  "
         f"({100*n_pad_tokens/n_total:.1f}% of the sequence)")

    pad_is_left = bool(attention_mask[0].item() == 0 and attention_mask[-1].item() == 1)
    pad_is_right = bool(attention_mask[0].item() == 1 and attention_mask[-1].item() == 0)
    print(f"  padding location: {'LEFT' if pad_is_left else ('RIGHT' if pad_is_right else 'MIXED/NONE')}")
    print(f"  attention_mask first 10: {attention_mask[:10].tolist()}")
    print(f"  attention_mask last 10:  {attention_mask[-10:].tolist()}")

    print("\n=== 6. Are labels masked (-100) anywhere? Prompt tokens? Padding tokens? ===")
    n_masked = int((labels == -100).sum().item())
    print(f"  n_positions_with_label==-100 = {n_masked}  (0 means NO masking is applied anywhere)")
    print(f"  labels == input_ids everywhere? {bool((labels == input_ids).all().item())}")

    print("\n=== 7. Decode: what does the model, look at the FIRST n_prompt_tokens of the "
         "actual label sequence, and confirm those are prompt tokens (not masked) ===")
    decoded_label_prompt_region = tokenizer.decode(
        [t for t in labels[:n_prompt_tokens].tolist() if t >= 0])
    print(f"  labels[0:{n_prompt_tokens}] decoded (should be the INSTRUCTION+CONTEXT text, "
         f"proving the model is supervised to reconstruct the prompt, not just the response):")
    print(f"  {decoded_label_prompt_region!r}")

    print("\n=== 7b. Decode the REAL content region (last n_real_tokens positions) to confirm "
         "where the prompt/response actually landed given left-padding ===")
    real_region = labels[-n_real_tokens:]
    print(f"  labels[-{n_real_tokens}:] decoded: {tokenizer.decode(real_region.tolist())!r}")
    print(f"  fraction of the 256-length label sequence that is pure padding token "
         f"(unmasked, contributing to loss) = {100*n_pad_tokens/n_total:.1f}%")

    print("\n=== 8. Data collator / Trainer inputs ===")
    from transformers import Trainer, TrainingArguments
    # Mirror training.py's real run_training(): a Trainer is never built on
    # the raw quantized base model there either -- get_peft_model() always
    # runs first. Reproduced here only so this diagnostic's own Trainer()
    # call doesn't hit validate_quantization_for_training(); not a change to
    # any pipeline file.
    peft_model = FastLanguageModel.get_peft_model(
        model, r=8, lora_alpha=16, lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        use_gradient_checkpointing="unsloth", random_state=42)
    args = TrainingArguments(output_dir=str(ROOT / "lim_training" / "runs" / "_diagnose_tmp"),
                             per_device_train_batch_size=1, max_steps=1, report_to=[], disable_tqdm=True)
    trainer = Trainer(model=peft_model, args=args, train_dataset=ds)
    print(f"  trainer.data_collator = {trainer.data_collator!r}")
    batch = trainer.get_train_dataloader()
    first_batch = next(iter(batch))
    print(f"  first collated batch keys: {list(first_batch.keys())}")
    print(f"  collated input_ids.shape: {tuple(first_batch['input_ids'].shape)}")
    print(f"  collated labels equal per-example labels? "
         f"{bool((first_batch['labels'][0] == labels).all().item())}")
    print(f"  'position_ids' explicitly present in batch? {'position_ids' in first_batch}")

    print("\n=== 9. Reproducible experiment: does the SAME degenerate output reappear "
         "with a masked-prompt oracle comparison? (read-only -- computed here, not "
         "written back to training.py) ===")
    # Build what response-only-masked labels WOULD have looked like, purely for
    # comparison printout -- proves what a correct implementation would do,
    # without changing any pipeline file.
    would_be_labels = input_ids.clone()
    would_be_labels[:n_prompt_tokens] = -100
    n_supervised_would_be = int((would_be_labels != -100).sum().item())
    n_supervised_actual = int((labels != -100).sum().item())
    print(f"  ACTUAL n_label_positions_supervised (this run's real training data) = {n_supervised_actual}")
    print(f"  RESPONSE-ONLY-MASKED n_label_positions_would_be_supervised = {n_supervised_would_be}")
    print(f"  fraction of supervised signal that was PROMPT/PADDING, not response, in the "
         f"actual run = {100*(1 - n_supervised_would_be/n_supervised_actual):.1f}%")


if __name__ == "__main__":
    main()
