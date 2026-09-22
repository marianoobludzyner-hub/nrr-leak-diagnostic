#!/usr/bin/env python3
"""
NRR Leak Diagnostic
Obludzyner & Co. | Post-sales advisory for B2B SaaS | https://obludzyner.com

An open-source, simplified version of the 7-question diagnostic used at
obludzyner.com/diagnostic. Estimates the ARR you are leaking to churn and
undergenerated expansion, and gives a directional read on how systematic
your post-sales motion is.

Zero dependencies. Python 3.8+. Runs fully offline -- nothing you enter
here is sent anywhere.

Usage:
    Interactive:      python3 diagnostic.py
    Non-interactive:   python3 diagnostic.py --arr 5000000 --churn 15 --expansion 8 \
                            --q1 1 --q2 1 --q3 1 --q4 2 --q5 2 --q6 1 --json
"""

import argparse
import json
import sys

CHURN_BASELINE = 0.05      # "system" churn floor Obludzyner & Co. uses for B2B SaaS up to $10M ARR
EXPANSION_POTENTIAL = 0.20  # expansion-as-%-of-ARR ceiling used for the same segment

# Peer benchmarks: directional medians from SaaS Capital 2025 Retention Survey,
# Benchmarkit 2025 B2B SaaS Performance Metrics report, and ChartMogul benchmark data.
# Your own cohort data is always the better benchmark than any of these.
BENCHMARKS = {
    "churn_peer_median": 0.09,
    "churn_horizontal_median": 0.12,
    "nrr_peer_median": 1.02,
    "nrr_peer_top_quartile": 1.14,
    "nrr_horizontal_median": 1.01,
}

QUESTIONS = [
    {
        "key": "renewal_visibility",
        "label": "Renewal visibility",
        "prompt": "How do renewals typically go in your company?",
        "options": [
            "We see them coming and manage them proactively",
            "We usually know a few weeks before but scramble",
            "Renewals keep surprising us even when relationships seem fine",
            "We have lost accounts we did not see coming",
        ],
    },
    {
        "key": "expansion_motion",
        "label": "Expansion motion",
        "prompt": "How does expansion (upsell / cross-sell) happen in your company?",
        "options": [
            "CSMs identify and drive expansion systematically",
            "It happens occasionally when the customer asks",
            "It only happens when leadership gets involved",
            "It rarely happens at all",
        ],
    },
    {
        "key": "commercial_mandate",
        "label": "Commercial mandate",
        "prompt": "Does your CS team see protecting ARR as their primary responsibility?",
        "options": [
            "Yes, clearly. They own retention and expansion metrics",
            "Somewhat. They focus on satisfaction more than revenue",
            "No. They are a support and relationship function",
            "I am not sure they think about it that way",
        ],
    },
    {
        "key": "arr_risk_visibility",
        "label": "ARR risk visibility",
        "prompt": "How visible is your ARR risk at any given moment?",
        "options": [
            "We have a health model with early warning signals",
            "We have some signals but nothing systematic",
            "We rely on gut feel and account knowledge",
            "We find out when something breaks",
        ],
    },
    {
        "key": "founder_dependency",
        "label": "Founder dependency",
        "prompt": "How often do you personally show up on accounts?",
        "options": [
            "Rarely. The team handles everything",
            "For strategic accounts only, by design",
            "More than I should. The team escalates too much",
            "I am still the main relationship on key accounts",
        ],
    },
    {
        "key": "system_scalability",
        "label": "System scalability",
        "prompt": "What best describes your post-sales situation right now?",
        "options": [
            "We have a system and it scales with the business",
            "We have processes but they depend on specific people",
            "We are figuring it out as we grow",
            "Post-sales did not keep up with our growth",
        ],
    },
]

TIER_LABELS = ["Strong", "Partial", "Weak", "Critical"]


def score_option(index: int) -> int:
    """Option 0 (best) scores 3, option 3 (worst) scores 0."""
    return 3 - index


def tier_for(index: int) -> str:
    return TIER_LABELS[index]


def band_label(total: int, max_score: int = 18) -> str:
    pct = total / max_score
    if pct >= 0.85:
        return "Systematic"
    if pct >= 0.55:
        return "Partially systematic"
    if pct >= 0.30:
        return "Reactive"
    return "Critical"


def compute(arr, churn_pct, expansion_pct, answers):
    """
    arr: current ARR in USD
    churn_pct, expansion_pct: as whole numbers, e.g. 15 for 15%
    answers: list of 6 option indices (0-3), one per QUESTIONS entry, in order
    """
    churn = churn_pct / 100
    expansion = expansion_pct / 100

    churn_cost_today = arr * churn
    churn_cost_after = arr * CHURN_BASELINE
    arr_retained = max(churn_cost_today - churn_cost_after, 0)

    expansion_today = arr * expansion
    expansion_potential = arr * EXPANSION_POTENTIAL
    expansion_generated = max(expansion_potential - expansion_today, 0)

    total_leak = arr_retained + expansion_generated

    nrr_today = 100 - churn_pct + expansion_pct
    nrr_at_full_system = 100 - (CHURN_BASELINE * 100) + (EXPANSION_POTENTIAL * 100)

    profile = []
    total_score = 0
    for q, idx in zip(QUESTIONS, answers):
        s = score_option(idx)
        total_score += s
        profile.append({
            "key": q["key"],
            "label": q["label"],
            "answer": q["options"][idx],
            "tier": tier_for(idx),
        })

    return {
        "inputs": {
            "arr": arr,
            "churn_pct": churn_pct,
            "expansion_pct": expansion_pct,
        },
        "financial_case": {
            "churn_cost_today": round(churn_cost_today),
            "churn_cost_after": round(churn_cost_after),
            "arr_retained": round(arr_retained),
            "expansion_today": round(expansion_today),
            "expansion_potential": round(expansion_potential),
            "expansion_generated": round(expansion_generated),
            "total_annual_leak": round(total_leak),
        },
        "nrr": {
            "today_pct": nrr_today,
            "at_full_system_pct": nrr_at_full_system,
        },
        "benchmarks": BENCHMARKS,
        "operating_profile": {
            "score": total_score,
            "max_score": 18,
            "band": band_label(total_score),
            "dimensions": profile,
        },
    }


def bar(value, max_value, width=30):
    filled = int(round((value / max_value) * width)) if max_value else 0
    filled = max(0, min(width, filled))
    return "#" * filled + "-" * (width - filled)


def render_text(result):
    fc = result["financial_case"]
    nrr = result["nrr"]
    op = result["operating_profile"]
    arr = result["inputs"]["arr"]

    lines = []
    lines.append("=" * 60)
    lines.append("YOUR RESULTS")
    lines.append("=" * 60)
    lines.append(f"Estimated ARR leak per year: ${fc['total_annual_leak']:,}")
    lines.append(
        f"  ${fc['arr_retained']:,} in recoverable churn "
        f"({result['inputs']['churn_pct']}% vs a {int(CHURN_BASELINE*100)}% baseline)"
    )
    lines.append(
        f"  ${fc['expansion_generated']:,} in expansion not generated "
        f"({result['inputs']['expansion_pct']}% vs a {int(EXPANSION_POTENTIAL*100)}% potential)"
    )
    lines.append("")
    lines.append("THE FINANCIAL CASE")
    lines.append(f"  Churn cost today:          ${fc['churn_cost_today']:>12,}  {bar(fc['churn_cost_today'], arr)}")
    lines.append(f"  Churn cost after (system): ${fc['churn_cost_after']:>12,}  {bar(fc['churn_cost_after'], arr)}")
    lines.append(f"  Net ARR retained:          ${fc['arr_retained']:>12,}")
    lines.append(f"  Expansion generated by CS: ${fc['expansion_generated']:>12,}")
    lines.append(f"  Total annual impact:       ${fc['total_annual_leak']:>12,}")
    lines.append("")
    lines.append(f"  NRR today: {nrr['today_pct']:.0f}%   NRR at full system output: {nrr['at_full_system_pct']:.0f}%")
    lines.append("")
    lines.append("BENCHMARKS (directional -- your own cohort data is always better)")
    b = result["benchmarks"]
    lines.append(f"  Your churn:            {result['inputs']['churn_pct']}%")
    lines.append(f"  Peer median churn:     {b['churn_peer_median']*100:.0f}%")
    lines.append(f"  Horizontal SaaS median:{b['churn_horizontal_median']*100:.0f}%")
    lines.append(f"  Your NRR:              {nrr['today_pct']:.0f}%")
    lines.append(f"  Peer median NRR:       {b['nrr_peer_median']*100:.0f}%")
    lines.append(f"  Peer top quartile NRR: {b['nrr_peer_top_quartile']*100:.0f}%")
    lines.append("")
    lines.append(f"OPERATING PROFILE: {op['band']} ({op['score']} of {op['max_score']})")
    for d in op["dimensions"]:
        lines.append(f"  {d['label']:<22} {d['tier']:<9} -> {d['answer']}")
    lines.append("=" * 60)
    lines.append("This is a simplified, open-source version of the diagnostic")
    lines.append("used by Obludzyner & Co. Benchmarks here are directional.")
    lines.append("For a precise, benchmarked Revenue Audit of your own business:")
    lines.append("  https://obludzyner.com")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_svg(result, path):
    fc = result["financial_case"]
    arr = result["inputs"]["arr"]
    b = result["benchmarks"]
    churn_pct = result["inputs"]["churn_pct"]
    nrr_today = result["nrr"]["today_pct"]

    # Two small horizontal bar groups: (1) churn today vs baseline vs peer median,
    # (2) NRR today vs peer median vs top quartile. Pure SVG, no dependencies.
    def hbar_row(y, label, value, max_value, color):
        w = 0 if max_value == 0 else max(2, (value / max_value) * 380)
        return (
            f'<text x="0" y="{y-4}" font-size="12" font-family="sans-serif" fill="#52514e">{label}</text>'
            f'<rect x="0" y="{y}" width="380" height="14" rx="7" fill="#e1e0d9" />'
            f'<rect x="0" y="{y}" width="{w:.1f}" height="14" rx="7" fill="{color}" />'
            f'<text x="{min(w,375)+5}" y="{y+11}" font-size="11" font-family="sans-serif" font-weight="bold" fill="#0b0b0b">{value:.0f}%</text>'
        )

    max_churn = max(churn_pct, b["churn_peer_median"] * 100, b["churn_horizontal_median"] * 100, 20)
    max_nrr = max(nrr_today, b["nrr_peer_median"] * 100, b["nrr_peer_top_quartile"] * 100, 120)

    rows = []
    y = 70
    rows.append(f'<text x="0" y="{y-20}" font-size="15" font-family="sans-serif" font-weight="bold" fill="#0b0b0b">Annual gross revenue churn</text>')
    rows.append(hbar_row(y, "You", churn_pct, max_churn, "#2a78d6"))
    y += 30
    rows.append(hbar_row(y, "Peer median", b["churn_peer_median"] * 100, max_churn, "#c3c2b7"))
    y += 30
    rows.append(hbar_row(y, "Horizontal SaaS median", b["churn_horizontal_median"] * 100, max_churn, "#c3c2b7"))
    y += 30
    rows.append(hbar_row(y, "System baseline", CHURN_BASELINE * 100, max_churn, "#0ca30c"))
    y += 60

    rows.append(f'<text x="0" y="{y-20}" font-size="15" font-family="sans-serif" font-weight="bold" fill="#0b0b0b">Net revenue retention (NRR)</text>')
    rows.append(hbar_row(y, "You", nrr_today, max_nrr, "#2a78d6"))
    y += 30
    rows.append(hbar_row(y, "Peer median", b["nrr_peer_median"] * 100, max_nrr, "#c3c2b7"))
    y += 30
    rows.append(hbar_row(y, "Peer top quartile", b["nrr_peer_top_quartile"] * 100, max_nrr, "#c3c2b7"))
    y += 50

    total_h = y + 40
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 {total_h}" font-family="sans-serif">
<rect x="0" y="0" width="420" height="{total_h}" fill="#fcfcfb" />
<text x="0" y="20" font-size="13" font-family="sans-serif" fill="#52514e">Estimated ARR leak: ${fc['total_annual_leak']:,}/yr</text>
{''.join(rows)}
<text x="0" y="{total_h-10}" font-size="10" font-family="sans-serif" fill="#898781">Obludzyner &amp; Co. | obludzyner.com | open-source diagnostic</text>
</svg>'''
    with open(path, "w") as f:
        f.write(svg)


def prompt_choice(q):
    print(f"\n{q['prompt']}")
    for i, opt in enumerate(q["options"]):
        print(f"  {i}) {opt}")
    while True:
        raw = input("Choose 0-3: ").strip()
        if raw in ("0", "1", "2", "3"):
            return int(raw)
        print("Please enter a number from 0 to 3.")


def run_interactive():
    print("NRR Leak Diagnostic -- Obludzyner & Co. (open-source edition)")
    print("7 questions. Approximate is fine.\n")
    arr = float(input("Current ARR (USD), e.g. 5000000: ").strip() or 0)
    churn_pct = float(input("Annual gross revenue churn (%), e.g. 15: ").strip() or 0)
    expansion_pct = float(input("Expansion revenue last year (% of ARR), e.g. 8: ").strip() or 0)

    answers = [prompt_choice(q) for q in QUESTIONS]

    result = compute(arr, churn_pct, expansion_pct, answers)
    print("\n" + render_text(result))

    svg_path = "diagnostic_result.svg"
    render_svg(result, svg_path)
    print(f"\nChart saved to {svg_path}")


def main():
    parser = argparse.ArgumentParser(description="NRR Leak Diagnostic (open-source)")
    parser.add_argument("--arr", type=float)
    parser.add_argument("--churn", type=float, help="annual gross revenue churn, percent")
    parser.add_argument("--expansion", type=float, help="expansion revenue last year, percent of ARR")
    for i in range(1, 7):
        parser.add_argument(f"--q{i}", type=int, choices=[0, 1, 2, 3])
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--svg", type=str, help="path to write an SVG chart to")
    args = parser.parse_args()

    if args.arr is None:
        run_interactive()
        return

    answers = [getattr(args, f"q{i}") for i in range(1, 7)]
    if args.churn is None or args.expansion is None or any(a is None for a in answers):
        print("Non-interactive mode requires --arr --churn --expansion --q1..--q6", file=sys.stderr)
        sys.exit(1)

    result = compute(args.arr, args.churn, args.expansion, answers)

    if args.svg:
        render_svg(result, args.svg)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result))


if __name__ == "__main__":
    main()
