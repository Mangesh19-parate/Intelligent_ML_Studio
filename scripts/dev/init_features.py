from pathlib import Path

base = Path("apps/frontend/src/features")
features = [
    "auth", "projects", "datasets", "diagnostics", "transformations",
    "feature-selection", "experiments", "training", "explainability",
    "model-registry", "deployments", "monitoring", "admin"
]

for f in features:
    p = base / f
    p.mkdir(parents=True, exist_ok=True)
    t = p / "types.ts"
    if not t.exists():
        t.write_text(f"// Types for {f}\nexport interface {f.title().replace('-', '')}State {{\n  status?: string;\n}}\n", encoding="utf-8")
    idx = p / "index.ts"
    if not idx.exists():
        idx.write_text(f"// Feature module: {f}\nexport * from './types';\n", encoding="utf-8")

print("Frontend feature directories initialized successfully.")
