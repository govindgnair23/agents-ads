"""Amazon/Walmart full-agent-shopping scenarios: revenue and profit separately.

All dollar inputs are USD billions; no live data downloads or random sampling.
Run `python competitive_scenarios.py` to validate and export results/figures.
The companion QMD explains sources, accounting, assumptions, and limitations.
"""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import csv
import itertools
import json
import math

import numpy as np
import matplotlib.pyplot as plt

# Frozen annual disclosures: Amazon FY2025; Walmart FY2026 to Jan 31, 2026.
AMAZON_REVENUE = 716.924
AMAZON_ADS = 68.635
AMAZON_SELLER_SERVICES = 172.162
AMAZON_GMV = 830.0                  # Marketplace Pulse estimate, not revenue.
AMAZON_SELLER_GMV = 575.0
AMAZON_OPERATING_INCOME = 79.975
AMAZON_NON_AWS_INCOME = 34.369
WALMART_REVENUE = 713.163
WALMART_ADS = 6.4                   # Disclosure: "nearly" 6.4; rounded input.
WALMART_OPERATING_INCOME = 29.825

SOURCES = {
    "amazon_10k": "https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm",
    "walmart_results": "https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-26-000032/earningsreleasefy26q4.htm",
    "amazon_gmv": "https://www.marketplacepulse.com/articles/amazon-gmv-surpassed-800-billion-in-2025",
    "walmart_search_ads": "https://www.walmartconnect.com/solutions/sponsored-products",
}

@dataclass(frozen=True)
class Assumptions:
    adoption: float = 1.0
    amazon_onsite_ad_share: float = 0.70
    walmart_onsite_ad_share: float = 0.50
    amazon_lost_ad_contribution: float = 0.70
    walmart_lost_ad_contribution: float = 0.70
    amazon_recovery_target: float = 1.0
    amazon_fee_cap: float = 0.06
    transfer_to_walmart_bn: float = 0.0
    amazon_commerce_contribution: float = 0.05
    walmart_commerce_contribution: float = 0.05
    amazon_transfer_marketplace_share: float = AMAZON_SELLER_GMV / AMAZON_GMV
    walmart_transfer_marketplace_share: float = 0.20
    amazon_legacy_take: float = AMAZON_SELLER_SERVICES / AMAZON_SELLER_GMV
    walmart_legacy_take: float = 0.15
    walmart_ad_revenue_booking_share: float = 0.50
    amazon_extra_agent_cost_bn: float = 0.50
    walmart_extra_agent_cost_bn: float = 0.50


def evaluate(p=Assumptions()):
    """First-order counterfactual, at fixed prices and aggregate goods spending.

    Positive T moves merchandise spending Amazon -> Walmart; negative reverses.
    Transfer is already realized at p.adoption; it is not multiplied by adoption.
    New fees recover an ad-contribution target, not lost legacy commerce profit.
    Fee cap is an assumed constraint; no demand or seller-exit curve is estimated.
    """
    values = asdict(p)
    fraction_names = [name for name in values if name not in {
        "transfer_to_walmart_bn", "amazon_extra_agent_cost_bn",
        "walmart_extra_agent_cost_bn"}]
    for name in fraction_names:
        if not 0 <= values[name] <= 1:
            raise ValueError(f"{name} must be in [0, 1]")
    if min(p.amazon_extra_agent_cost_bn, p.walmart_extra_agent_cost_bn) < 0:
        raise ValueError("Extra agent costs must be nonnegative")
    t = p.transfer_to_walmart_bn
    if t > AMAZON_GMV or -t > WALMART_REVENUE:
        raise ValueError("Transfer exceeds the broad donor scale")

    a_ad_loss = AMAZON_ADS * p.adoption * p.amazon_onsite_ad_share
    w_ad_loss = WALMART_ADS * p.adoption * p.walmart_onsite_ad_share
    a_ad_profit_loss = a_ad_loss * p.amazon_lost_ad_contribution
    w_ad_profit_loss = w_ad_loss * p.walmart_lost_ad_contribution

    # Only marketplace merchandise creates an Amazon SELLER fee base.
    fee_base = AMAZON_SELLER_GMV - p.amazon_transfer_marketplace_share * t
    if fee_base <= 0:
        raise ValueError("Remaining Amazon marketplace fee base must be positive")
    fee_target = p.amazon_recovery_target * a_ad_profit_loss
    fees = min(fee_target, p.amazon_fee_cap * fee_base)
    fee_rate = fees / fee_base

    # First-party merchandise is recognized gross; marketplace services net.
    a_recognition = (1-p.amazon_transfer_marketplace_share
                     + p.amazon_transfer_marketplace_share*p.amazon_legacy_take)
    w_recognition = (1-p.walmart_transfer_marketplace_share
                     + p.walmart_transfer_marketplace_share*p.walmart_legacy_take)
    a_commerce_revenue_delta = -t * a_recognition
    w_commerce_revenue_delta = t * w_recognition
    a_revenue_delta = -a_ad_loss + fees + a_commerce_revenue_delta
    # Walmart ads can be recognized as revenue OR a reduction of cost of sales.
    w_revenue_delta = (-p.walmart_ad_revenue_booking_share*w_ad_loss
                       + w_commerce_revenue_delta)

    a_profit_delta = (-a_ad_profit_loss + fees
                      - t*p.amazon_commerce_contribution
                      - p.amazon_extra_agent_cost_bn)
    w_profit_delta = (-w_ad_profit_loss + t*p.walmart_commerce_contribution
                      - p.walmart_extra_agent_cost_bn)
    w_breakeven = ((w_ad_profit_loss+p.walmart_extra_agent_cost_bn)
                  / p.walmart_commerce_contribution
                  if p.walmart_commerce_contribution else None)

    return {
        **values,
        "amazon_ad_revenue_lost_bn": a_ad_loss,
        "walmart_ad_economic_income_lost_bn": w_ad_loss,
        "amazon_ad_profit_lost_bn": a_ad_profit_loss,
        "walmart_ad_profit_lost_bn": w_ad_profit_loss,
        "amazon_remaining_seller_gmv_bn": fee_base,
        "amazon_fee_target_bn": fee_target,
        "amazon_new_fees_bn": fees,
        "amazon_new_fee_rate": fee_rate,
        "amazon_fee_target_shortfall_bn": fee_target-fees,
        "amazon_revenue_per_transferred_dollar": a_recognition,
        "walmart_revenue_per_transferred_dollar": w_recognition,
        "amazon_commerce_revenue_delta_bn": a_commerce_revenue_delta,
        "walmart_commerce_revenue_delta_bn": w_commerce_revenue_delta,
        "amazon_revenue_delta_bn": a_revenue_delta,
        "walmart_revenue_delta_bn": w_revenue_delta,
        "walmart_revenue_delta_low_bn": -w_ad_loss+w_commerce_revenue_delta,
        "walmart_revenue_delta_high_bn": w_commerce_revenue_delta,
        "amazon_revenue_after_bn": AMAZON_REVENUE+a_revenue_delta,
        "walmart_revenue_after_bn": WALMART_REVENUE+w_revenue_delta,
        "amazon_revenue_change_pct": a_revenue_delta/AMAZON_REVENUE,
        "walmart_revenue_change_pct": w_revenue_delta/WALMART_REVENUE,
        "amazon_profit_delta_bn": a_profit_delta,
        "walmart_profit_delta_bn": w_profit_delta,
        "amazon_operating_income_after_bn": AMAZON_OPERATING_INCOME+a_profit_delta,
        "amazon_non_aws_income_after_bn": AMAZON_NON_AWS_INCOME+a_profit_delta,
        "walmart_operating_income_after_bn": WALMART_OPERATING_INCOME+w_profit_delta,
        "walmart_profit_breakeven_transfer_bn": w_breakeven,
        "amazon_merchandise_spending_delta_bn": -t,
        "walmart_merchandise_spending_delta_bn": t,
        "combined_merchandise_spending_delta_bn": 0.0,
    }


def named_cases():
    """Illustrative favorable/adverse states, not mathematical global bounds."""
    base = Assumptions()
    specs = [
        ("Amazon favorable / Walmart loses orders", replace(base,
            amazon_onsite_ad_share=.50, walmart_onsite_ad_share=.80,
            amazon_lost_ad_contribution=.50, walmart_lost_ad_contribution=.90,
            transfer_to_walmart_bn=-20, amazon_commerce_contribution=.06,
            walmart_commerce_contribution=.06,
            amazon_extra_agent_cost_bn=.20, walmart_extra_agent_cost_bn=.20)),
        ("No purchase shift / fee substitution", base),
        ("Walmart favorable / Amazon loses orders", replace(base,
            amazon_onsite_ad_share=.90, walmart_onsite_ad_share=.20,
            amazon_lost_ad_contribution=.90,
            amazon_recovery_target=.25, amazon_fee_cap=.02,
            transfer_to_walmart_bn=50, walmart_commerce_contribution=.08,
            amazon_extra_agent_cost_bn=1.0, walmart_extra_agent_cost_bn=.20)),
        ("Both lose advertising / difficult recovery", replace(base,
            amazon_onsite_ad_share=.90, walmart_onsite_ad_share=.80,
            amazon_lost_ad_contribution=.90, walmart_lost_ad_contribution=.90,
            amazon_recovery_target=.25, amazon_fee_cap=.02,
            amazon_extra_agent_cost_bn=2.0, walmart_extra_agent_cost_bn=2.0)),
    ]
    return [{"scenario": name, **evaluate(p)} for name, p in specs]


def sensitivity_grid():
    # Conditional sensitivity only. Repeated outcomes do not imply probabilities.
    axes = {
        "amazon_onsite_ad_share": [.50, .70, .90],
        "walmart_onsite_ad_share": [.20, .50, .80],
        "amazon_fee_cap": [.02, .04, .06],
        "transfer_to_walmart_bn": [-20, 0, 20, 50, 100],
        "walmart_commerce_contribution": [.02, .05, .08],
        "walmart_transfer_marketplace_share": [.20, .80, 1.0],
    }
    return [evaluate(replace(Assumptions(), **dict(zip(axes, values))))
            for values in itertools.product(*axes.values())]


def seller_comparison(fee_rate, amazon_tacos=.10, walmart_tacos=.04,
                      removal=1.0):
    """Change in contribution per original revenue dollar; prices held fixed.

    Assumes all modeled seller ads are discovery ads, no Walmart replacement fee,
    and no non-ad cost changes. Does not estimate either channel's baseline profit.
    """
    a_gain = removal*amazon_tacos-fee_rate
    w_gain = removal*walmart_tacos
    return {"amazon_original_tacos": amazon_tacos,
            "walmart_original_tacos": walmart_tacos,
            "amazon_replacement_fee_rate": fee_rate,
            "amazon_seller_contribution_change": a_gain,
            "walmart_seller_contribution_change": w_gain,
            "change_in_walmart_advantage": w_gain-a_gain}


def validate():
    base = Assumptions()
    zero = evaluate(replace(base, adoption=0, transfer_to_walmart_bn=0,
                            amazon_extra_agent_cost_bn=0, walmart_extra_agent_cost_bn=0))
    for field in ["amazon_revenue_delta_bn", "walmart_revenue_delta_bn",
                  "amazon_profit_delta_bn", "walmart_profit_delta_bn"]:
        assert math.isclose(zero[field], 0, abs_tol=1e-12)
    for row in named_cases()+sensitivity_grid():
        assert row["amazon_new_fees_bn"] <= row["amazon_fee_target_bn"]+1e-10
        assert row["amazon_new_fee_rate"] <= row["amazon_fee_cap"]+1e-10
        assert math.isclose(row["amazon_merchandise_spending_delta_bn"]+
                            row["walmart_merchandise_spending_delta_bn"], 0, abs_tol=1e-12)
        assert row["walmart_revenue_delta_low_bn"]-1e-10 <= row["walmart_revenue_delta_bn"]
        assert row["walmart_revenue_delta_bn"] <= row["walmart_revenue_delta_high_bn"]+1e-10
    recover = evaluate(replace(base, amazon_fee_cap=1, transfer_to_walmart_bn=0,
                               amazon_extra_agent_cost_bn=0))
    assert math.isclose(recover["amazon_profit_delta_bn"], 0, abs_tol=1e-10)
    assert math.isclose(recover["amazon_revenue_delta_bn"],
                        -recover["amazon_ad_revenue_lost_bn"]*
                        (1-base.amazon_lost_ad_contribution), abs_tol=1e-10)
    t = evaluate(replace(base, transfer_to_walmart_bn=10))
    assert math.isclose(t["amazon_remaining_seller_gmv_bn"],
                        AMAZON_SELLER_GMV-10*base.amazon_transfer_marketplace_share)
    bookings = [evaluate(replace(base, walmart_ad_revenue_booking_share=h)) for h in [0, .5, 1]]
    assert len({r["walmart_profit_delta_bn"] for r in bookings}) == 1
    for beta, expected in [(0, 1), (1, .15)]:
        r = evaluate(replace(base, walmart_transfer_marketplace_share=beta))
        assert math.isclose(r["walmart_revenue_per_transferred_dollar"], expected)
    r = evaluate(base)
    breakeven = evaluate(replace(base, transfer_to_walmart_bn=r["walmart_profit_breakeven_transfer_bn"]))
    assert math.isclose(breakeven["walmart_profit_delta_bn"], 0, abs_tol=1e-10)
    assert seller_comparison(.07)["change_in_walmart_advantage"] > 0
    assert math.isclose(seller_comparison(.06)["change_in_walmart_advantage"], 0, abs_tol=1e-12)
    assert seller_comparison(.04)["change_in_walmart_advantage"] < 0
    return "All accounting, fee-cap, zero-shock, booking, and break-even checks passed"


def markdown_table(headers, rows):
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"]*len(headers)) + " |")
    for row in rows:
        print("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    print()


def figures(output=None):
    rows = named_cases()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    names = ["Amazon favorable", "No purchase shift", "Walmart favorable", "Both adverse"]
    pos = np.arange(len(names))
    for ax, suffix, title in zip(axes, ["revenue_delta_bn", "profit_delta_bn"],
                                 ["Change in company revenue", "Change in operating contribution"]):
        ax.barh(pos-.16, [r[f"amazon_{suffix}"] for r in rows], .3,
                color="#cd7825", label="Amazon")
        ax.barh(pos+.16, [r[f"walmart_{suffix}"] for r in rows], .3,
                color="#2777ba", label="Walmart")
        ax.set_yticks(pos, names)
        ax.invert_yaxis()
        ax.axvline(0, color="#596273", linewidth=1)
        ax.set(xlabel="USD billions per year", title=title)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle("Full agent takeover: illustrative annual scenarios", fontsize=14)
    fig.tight_layout()
    transfers = np.linspace(-20, 100, 241)
    fig2, ax = plt.subplots(figsize=(8, 4.5))
    for exposure in [.2, .5, .8]:
        changes = [evaluate(replace(Assumptions(), walmart_onsite_ad_share=exposure,
                    transfer_to_walmart_bn=t))["walmart_profit_delta_bn"] for t in transfers]
        ax.plot(transfers, changes, label=f"{exposure:.0%} of Walmart ad income exposed")
    ax.axhline(0, color="#596273", linewidth=1)
    ax.set(xlabel="Merchandise spending transferred Amazon -> Walmart (USD bn)",
           ylabel="Walmart operating contribution change (USD bn)",
           title="Walmart must win enough contribution to offset lost ads")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=.15)
    fig2.tight_layout()
    if output is not None:
        output = Path(output)
        output.mkdir(exist_ok=True)
        for stem, chart in [("company_outcomes", fig), ("walmart_breakeven", fig2)]:
            chart.savefig(output/f"{stem}.png", dpi=180, bbox_inches="tight")
            chart.savefig(output/f"{stem}.pdf", bbox_inches="tight")
    return fig, fig2


def export(output="competition-outputs"):
    output = Path(output)
    output.mkdir(exist_ok=True)
    cases, grid = named_cases(), sensitivity_grid()
    seller_rows = [{"scenario": row["scenario"], **seller_comparison(
        row["amazon_new_fee_rate"], amazon_tacos=a)}
        for row in cases for a in [.03, .10, .15]]
    for name, rows in [("company_scenarios.csv", cases), ("sensitivity_grid.csv", grid),
                       ("seller_comparison.csv", seller_rows)]:
        with (output/name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    summary = {"as_of": "2026-10-11", "units": "USD billions annually",
               "demand": "Fixed goods spending, fixed prices, exogenous retailer allocation",
               "sources": SOURCES, "default_assumptions": asdict(Assumptions()),
               "scenarios": cases, "grid_rows": len(grid), "validation": validate()}
    (output/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = export()
    figures("competition-outputs")
    print(result["validation"])
    print(f"Exported {len(result['scenarios'])} cases and {result['grid_rows']:,} grid rows.")
    for row in result["scenarios"]:
        print(row["scenario"])
        print(f"  Revenue change: Amazon {row['amazon_revenue_delta_bn']:+.2f}bn; "
              f"Walmart {row['walmart_revenue_delta_bn']:+.2f}bn")
        print(f"  Profit change: Amazon {row['amazon_profit_delta_bn']:+.2f}bn; "
              f"Walmart {row['walmart_profit_delta_bn']:+.2f}bn")
