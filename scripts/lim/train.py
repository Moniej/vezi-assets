"""LIM-2: reproducible training CLI. Refuses to start (raises, no run
recorded) if any requested dataset version isn't a registered, integrity
-verified, gate-passing version -- per the owner's "refuse to start
training if any required dataset fails its validation thresholds"
instruction. Every run is fully recorded in the immutable training-run
registry before a single GPU cycle executes.

Every default below (rank, step count, learning rate, base model path)
comes from configs/lim_training_defaults.toml -- the frozen production
baseline per RB-2's formal closure (docs/lim_runs/rb2_closure.md). Pass
the corresponding flag explicitly to override any one of them for a
single-variable experiment (e.g. RB-4's learning-rate sweep); never edit
this file's fallback constants to "default" to something else.

  lim_training/venv/Scripts/python.exe scripts/lim/train.py \
      --dataset self_critique --seed 42

  lim_training/venv/Scripts/python.exe scripts/lim/train.py \
      --dataset extraction@extraction-v1.0.0 --dataset self_critique --seed 7 \
      --lora-r 16   # explicit override, e.g. re-testing a retired rank
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.lim import registry, training, training_registry  # noqa: E402
from ngxrot.lim.dataset_loader import DatasetNotReadyError  # noqa: E402


def _parse_dataset_arg(spec: str) -> tuple[str, str | None]:
    if "@" in spec:
        dtype, version = spec.split("@", 1)
        return dtype, version
    return spec, None


def main():
    defaults = training.load_training_defaults()

    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", action="append", required=True,
                   help="dataset_type or dataset_type@version; repeatable")
    ap.add_argument("--base-model", default=defaults["base_model"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--max-steps", type=int, default=defaults["training"]["max_steps"])
    ap.add_argument("--save-steps", type=int, default=defaults["training"]["save_steps"])
    ap.add_argument("--learning-rate", type=float, default=defaults["training"]["learning_rate"])
    ap.add_argument("--lora-r", type=int, default=defaults["lora"]["r"],
                   help="frozen production default is 8 (RB-2 closure) -- pass this flag "
                        "explicitly only when rank itself is the experiment's variable")
    ap.add_argument("--max-seq-length", type=int, default=defaults["training"]["max_seq_length"])
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    con_lim = registry.init_registry()
    con_train = training_registry.init_registry()

    specs = [_parse_dataset_arg(d) for d in args.dataset]
    print(f"Requested datasets: {specs}")

    # LoRA alpha follows this project's fixed 2*r convention regardless of
    # whether --lora-r was overridden away from the frozen default.
    lora_config = dict(defaults["lora"])
    lora_config["r"] = args.lora_r
    lora_config["lora_alpha"] = args.lora_r * 2

    try:
        result = training.run_training(
            con_lim, con_train, dataset_specs=specs, base_model=args.base_model,
            quantization_config=defaults["quantization"], lora_config=lora_config,
            hyperparameters={"batch_size": defaults["training"]["batch_size"],
                            "gradient_accumulation_steps": defaults["training"]["gradient_accumulation_steps"],
                            "max_steps": args.max_steps, "save_steps": args.save_steps,
                            "learning_rate": args.learning_rate},
            seed=args.seed, max_seq_length=args.max_seq_length, notes=args.notes)
    except DatasetNotReadyError as e:
        print(f"\nREFUSED TO START TRAINING: {e}")
        sys.exit(2)

    print(f"\nRun {result['run_id']} complete.")
    print(f"  n_train={result['n_train']} n_eval={result['n_eval']}")
    print(f"  final_loss={result['final_loss']:.4f}")
    print(f"  eval_metrics={result['eval_metrics']}")
    print(f"  checkpoints under: {result['run_dir']}")

    run = training_registry.get_run(con_train, result["run_id"])
    print(f"\nFull provenance for run {result['run_id']}:")
    print(f"  dataset_versions: {run['dataset_versions']}")
    print(f"  teacher_model_ids: {run['teacher_model_ids']}")
    print(f"  git_commit: {run['git_commit']}")
    print(f"  seed: {run['seed']}")


if __name__ == "__main__":
    main()
