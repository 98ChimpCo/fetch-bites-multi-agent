#!/usr/bin/env python3
"""
layout_agent.py — Iterative template-parity tuner for Fetch.Bites

What it does
------------
- Imports your PDF generator directly (no Appium/Instagram).
- Generates an output PDF from a small recipe fixture.
- Rasterizes both the TEMPLATE PDF and the OUTPUT PDF.
- Compares SSIM (structural similarity) per named regions (title, desc, stats, ingredients, directions, notes).
- Nudges JSON layout values (desc_leading, header row_gaps, stats padding, directions step_gap, column split).
- Repeats until thresholds are met or max iterations is reached.

Run
---
pip install pillow pymupdf scikit-image reportlab
python src/utils/tools/layout_agent.py \
  --repo-root . \
  --template "pdfs/pdf-recipe-card-template - Lovable.pdf" \
  --layout "pdfs/layout.v2.json" \
  --fixture src/utils/tools/recipe_fixture.json \
  --out pdfs/agent_out.pdf \
  --threshold 0.985 \
  --max-iters 8
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Tuple

import fitz  # PyMuPDF
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim

parser = argparse.ArgumentParser()
parser.add_argument("--repo-root", default=".", help="Repository root so we can import src.*")
parser.add_argument("--template", required=True, help="Path to template PDF")
parser.add_argument("--layout", required=True, help="Path to layout.v2.json (will be modified iteratively)")
parser.add_argument("--fixture", required=True, help="Path to recipe fixture JSON")
parser.add_argument("--out", default="pdfs/agent_out.pdf", help="Where to write the output PDF")
parser.add_argument("--threshold", type=float, default=0.985, help="SSIM threshold to consider 'matching'")
parser.add_argument("--max-iters", type=int, default=8, help="Maximum tuning iterations")
args = parser.parse_args()

repo_root = Path(args.repo_root).resolve()
sys.path.insert(0, str(repo_root))
os.environ.setdefault("LAYOUT_VERSION", "v2")
os.environ["LAYOUT_CONFIG"] = str(Path(args.layout).resolve())
os.makedirs(Path(args.out).parent, exist_ok=True)

# Import your generator
from src.agents.pdf_generator import PDFGenerator  # noqa: E402

def read_json(p: Path) -> Dict:
    with open(p, "r") as f:
        return json.load(f)

def write_json(p: Path, data: Dict):
    tmp = p.with_suffix(".tmp.json")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(p)

def render_first_page_to_png(pdf_path: Path) -> Image.Image:
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    zoom = fitz.Matrix(2, 2)  # 2x scale for crisper comparison
    pix = page.get_pixmap(matrix=zoom, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def crop_region(img: Image.Image, bbox: Tuple[float, float, float, float], upscale=2.0) -> Image.Image:
    x0, y0, x1, y1 = bbox
    return img.crop((int(x0*upscale), int(y0*upscale), int(x1*upscale), int(y1*upscale)))

def compute_ssim(a_img: Image.Image, b_img: Image.Image) -> float:
    a = np.array(a_img.convert("L"))
    b = np.array(b_img.convert("L"))
    if a.shape != b.shape:
        b = np.array(Image.fromarray(b).resize((a.shape[1], a.shape[0])))
    return float(ssim(a, b))

def nudge(value: float, delta: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, value + delta)))

def adjust_layout(layout: Dict, scores: Dict[str, float]):
    """Heuristic JSON-only nudges toward higher SSIM."""
    target = args.threshold
    # Header/description
    if scores.get("desc", 1.0) < target:
        layout.setdefault("header", {})
        layout["header"]["desc_leading"] = int(nudge(layout["header"].get("desc_leading", 16), +1, 12, 26))
        layout["header"].setdefault("row_gaps", {})
        layout["header"]["row_gaps"]["title_desc"] = int(nudge(layout["header"]["row_gaps"].get("title_desc", 8), +1, 0, 24))
        layout["header"]["row_gaps"]["meta_rows"] = int(nudge(layout["header"]["row_gaps"].get("meta_rows", 6), +1, 0, 24))
    # Stats
    if scores.get("stats", 1.0) < target:
        layout.setdefault("stats", {})
        pad = layout["stats"].setdefault("padding", {"t": 24, "b": 24, "x": 14})
        pad["x"] = int(nudge(pad.get("x", 14), +1, 6, 28))
        pad["t"] = int(nudge(pad.get("t", 24), +1, 6, 36))
        pad["b"] = int(nudge(pad.get("b", 24), +1, 6, 36))
    # Directions spacing
    if scores.get("directions", 1.0) < target:
        d = layout.setdefault("directions", {})
        d["step_gap"]    = int(nudge(d.get("step_gap", 12), +1, 6, 28))
        d["line_height"] = int(nudge(d.get("line_height", 14), +1, 10, 28))
        d["num_offset_y"]= int(nudge(d.get("num_offset_y", -4), +1, -8, 8))
    # Columns split (only if ingredients or directions are low)
    if min(scores.get("ingredients", 1.0), scores.get("directions", 1.0)) < target:
        cols = layout.setdefault("columns", {"left_pct": 0.4, "right_pct": 0.6})
        left = float(cols.get("left_pct", 0.4))
        left = nudge(left, +0.01, 0.30, 0.50)
        cols["left_pct"] = round(left, 3)
        cols["right_pct"] = round(1.0 - left, 3)

def measure_regions(template_pdf: Path, output_pdf: Path, layout: Dict) -> Dict[str, float]:
    t_img = render_first_page_to_png(template_pdf)
    o_img = render_first_page_to_png(output_pdf)
    boxes = layout.get("detected_bboxes", {})

    # Derive an approximate stats area based on columns and margins, if not provided.
    page_w = layout.get("page", {}).get("width", 612)
    margins = layout.get("page", {}).get("margins", {"l": 40, "t": 40, "r": 40, "b": 40})
    left_pct = layout.get("columns", {}).get("left_pct", 0.4)
    right_x0 = margins["l"] + (page_w - margins["l"] - margins["r"]) * left_pct
    stats_bbox = boxes.get("stats_bbox") or (right_x0, 170, page_w - margins["r"], 270)

    regions = {
        "title": boxes.get("title_bbox"),
        "desc": boxes.get("desc_bbox"),
        "ingredients": boxes.get("ingredients_bbox"),
        "directions": boxes.get("directions_bbox"),
        "notes": boxes.get("notes_bbox"),
        "stats": stats_bbox,
    }
    scores = {}
    for name, bbox in regions.items():
        if not bbox:
            continue
        t_crop = crop_region(t_img, bbox, upscale=2.0)
        o_crop = crop_region(o_img, bbox, upscale=2.0)
        try:
            scores[name] = compute_ssim(t_crop, o_crop)
        except Exception:
            scores[name] = 0.0
    return scores

def generate_once(output_pdf: Path, fixture_path: Path) -> Path:
    with open(fixture_path, "r") as f:
        recipe = json.load(f)
    gen = PDFGenerator(output_dir=str(Path(output_pdf).parent))
    out_path, _meta = gen.generate_pdf(recipe, image_path=None, post_url=recipe.get("source", {}).get("url"))
    out_path = Path(out_path)
    if out_path != output_pdf:
        shutil.copy2(out_path, output_pdf)
    return output_pdf

def main():
    layout_path = Path(args.layout)
    template_pdf = Path(args.template)
    output_pdf = Path(args.out)
    fixture_path = Path(args.fixture).resolve()

    layout = read_json(layout_path)

    for i in range(1, args.max_iters + 1):
        print(f"[layout_agent] Iteration {i}/{args.max_iters}")
        os.environ["LAYOUT_CONFIG"] = str(layout_path.resolve())

        # 1) Generate once
        generate_once(output_pdf, fixture_path)

        # 2) Score regions
        scores = measure_regions(template_pdf, output_pdf, layout)
        print("[layout_agent] Scores:", scores)

        # 3) Check threshold
        present = [v for v in scores.values() if v is not None]
        if present and all(v >= args.threshold for v in present):
            print("[layout_agent] ✅ Threshold met for all measured regions. Stopping.")
            break

        # 4) Nudge JSON & save
        adjust_layout(layout, scores)
        write_json(layout_path, layout)
        print("[layout_agent] Updated layout.json written.")

    print(f"[layout_agent] Final output at: {output_pdf}")

if __name__ == "__main__":
    main()