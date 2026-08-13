# trust_align Python environment

The project environment is an isolated virtual environment at:

```bash
~/projects/trust_align/.venv
```

Activate it with:

```bash
source ~/projects/trust_align/.venv/bin/activate
```

The repository's `.venv/bin/python` is the authoritative entry point. Use
`python -m pip` from that interpreter when installing or inspecting packages;
the generated pip shebang may retain an old spelling.

## Validated runtime

- OS: Ubuntu 24.04.3 LTS
- Python: 3.12.3
- PyTorch: 2.13.0+cu130
- CUDA runtime exposed by PyTorch: 13.0
- GPUs visible to PyTorch: 4
- GPU smoke test: 256x256 CUDA matrix multiply passed
- `pip check`: no broken requirements

## Installed capability groups

- Scientific/EEG: NumPy, SciPy, Pandas, scikit-learn, MNE, h5py, PyArrow
- Statistics/plots: statsmodels, matplotlib, seaborn, joblib, tqdm
- Modeling: PyTorch, torchvision, torchaudio, einops, `timm==0.4.12`
- Text/data: Transformers, Datasets, Tokenizers, SentencePiece, Accelerate,
  Evaluate, Safetensors
- Configuration/network helpers: PyYAML, Requests, Hugging Face Hub

The LaBraM preparation wrapper imports the required runtime modules above.
The official utility module's optional training dependencies (`tensorboardX`,
`pyhealth`, and `deepspeed`) are not installed; the wrapper intentionally does
not import that utility module. `braindecode` is also absent and is not used.

The exact resolved versions are recorded in
`02_code/environment/requirements-lock.txt`. The environment enables P0/P1
and the minimum EQ-ANMA pipeline; it does not resolve the scientific blockers
listed in the guidance documents (pretraining contamination, checkpoint and
corpus rights, candidate backbone mapping, data-card facts, item-level
definition, or preregistered split decisions).
