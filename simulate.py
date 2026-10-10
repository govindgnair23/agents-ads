"""Reproducible, first-order Amazon advertising-removal scenario analysis.

Run: MPLCONFIGDIR=/tmp/amazon-mpl python simulate.py
Dollar inputs are billions. Rates are fractions of original seller sales.
These are conditional scenarios, not estimated probabilities or an equilibrium
forecast. Ad attribution does not establish demand incrementality.

Public inputs (FY 2025, latest complete annual period as of 2026-10-09):
Advertising revenue: 68.635; seller-services revenue: 172.162;
consolidated operating profit: 79.975; NA + International profit: 34.369.
https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
Estimated third-party merchandise sales (GMV): 575.
https://www.marketplacepulse.com/articles/amazon-gmv-surpassed-800-billion-in-2025
Seller heterogeneity: many resellers <5% advertising/sales; private label often
>10% (2023 sampled seller P&Ls, not representative population estimates).
https://www.marketplacepulse.com/articles/amazon-takes-a-50-cut-of-sellers-revenue
Managed-advertiser benchmark: median 15%, middle half 10%-21%, 36 US accounts,
H1 2026. Selection bias: not a population or sales-weighted estimate.
https://sellerplex.com/amazon-ppc-benchmarks-2026/

Assumed inputs: third-party sellers fund 70% of all advertising; 80% of relevant
ads disappear; lost contribution is 70% of lost revenue; seller price response
is 50% of net incremental cost; no replacement agent fee; no commerce demand
loss in the base case. None of these assumptions is a public measured estimate.

Fee equivalents are incremental dollars per dollar of original retained sales,
not percentage increases to existing fees. We assume collecting incremental
fees costs negligibly little. The base model fixes quantity and excludes
endogenous demand, existing commission feedback, changes in seller mix, and
agent operating costs. The 20% base-shrink stress assumes the same remaining
seller mix and adds no recovery for lost legacy commerce contribution.
"""
from pathlib import Path
import csv
import itertools
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
A, G = 68.635, 575.0
SHARE, DISRUPTION, CONTRIBUTION, PASS = .7, .8, .7, .5

def model(ad_rate, share=SHARE, disruption=DISRUPTION,
          contribution=CONTRIBUTION, recovery=1., scope='seller',
          base_retained=1., passthrough=PASS, agent_fee=0.):
    exposed_revenue = A * (share if scope == 'seller' else 1.)
    lost_profit = exposed_revenue * disruption * contribution
    added_fees = lost_profit * recovery
    fee_rate = added_fees / (G * base_retained)
    saved_rate = disruption * ad_rate
    price_change = passthrough * (fee_rate + agent_fee - saved_rate)
    return dict(ad_rate=ad_rate, seller_ad_share=share,
                disruption=disruption, contribution=contribution,
                recovery=recovery, scope=scope, base_retained=base_retained,
                passthrough=passthrough, agent_fee=agent_fee,
                lost_ad_profit_bn=lost_profit, incremental_fees_bn=added_fees,
                fee_rate=fee_rate, saved_rate=saved_rate,
                price_change=price_change, price_from_100=100*(1+price_change))

def write_csv(name, rows):
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

specs = [
    ('No replacement fees', dict(recovery=0)),
    ('Recover half of lost seller-ad profit', dict(recovery=.5)),
    ('Recover all lost seller-ad profit', dict()),
    ('Recover broad ad losses from sellers', dict(scope='all')),
    ('Broad losses, 20% smaller fee base', dict(scope='all',base_retained=.8)),
]
average_ad_rate = SHARE*A/G
scenarios = [dict(scenario=name, **model(a, **kw))
             for name, kw in specs for a in [0,.03,.05,.10,.15,.20,average_ad_rate]]
write_csv('scenarios.csv', scenarios)

# Deterministic sensitivity grid. Counting signs is NOT a probability estimate.
sweep = [model(a, share=s, disruption=d, contribution=m, recovery=r,
               scope=scope, passthrough=p, agent_fee=k)
         for a,s,d,m,r,scope,p,k in itertools.product(
             [0,.03,.05,.10,.15,.20], [.5,.7,.8], [.5,.8,1.],
             [.5,.7,.9], [0,.5,1.], ['seller','all'], [.25,.5,1.], [0,.01,.03])]
write_csv('sensitivity_grid.csv', sweep)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,
                     'axes.spines.top':False,'axes.spines.right':False})
fig, (ax, bx) = plt.subplots(1,2,figsize=(13,5.6),gridspec_kw={'width_ratios':[1.7,1]})
fig.patch.set_facecolor('#fafbfc')
colors=['#9babc2','#6395cb','#176861','#c38a2a','#b24b4b']
short=['No replacement fees','Half seller-ad profit recovery','Full seller-ad profit recovery',
       'Broad ad-loss recovery','Broad recovery; fee base −20%']
x=np.linspace(0,.20,200)
for (name,kw),label,c in zip(specs,short,colors):
    y=np.array([model(a,**kw)['price_change'] for a in x])*100
    ax.plot(x*100,y,label=label,color=c,linewidth=2.4)
ax.axhline(0,color='#515d6c',linewidth=1)
ax.axvline(average_ad_rate*100,color='#515d6c',linestyle=':',alpha=.7)
ax.text(average_ad_rate*100+.25,4.1,'Assumed sales-weighted\naverage: 8.36%',fontsize=9,color='#515d6c')
ax.set(xlabel='Seller ad spending / all seller sales (%)',
       ylabel='Estimated consumer price change (%)',
       title='Who wins depends on previous ad spending',ylim=(-9,5.1))
ax.grid(axis='y',alpha=.15)
ax.legend(loc='lower left',fontsize=8.5,frameon=False)
vals=[model(average_ad_rate,**kw)['price_change']*100 for _,kw in specs]
labels=['No fees','Half seller\nad recovery','Full seller\nad recovery','Broad ad\nrecovery','Broad + smaller\nfee base']
bx.barh(labels,vals,color=colors,height=.6)
bx.axvline(0,color='#515d6c',linewidth=1)
for i,v in enumerate(vals):
    bx.text(v+(.10 if v>=0 else -.10),i,f'{v:+.2f}%',
            ha='left' if v>=0 else 'right',va='center',fontsize=10)
bx.invert_yaxis()
bx.set(xlim=(-4.3,1.7),xlabel='Estimated price change (%)',
       title='Average seller under assumed ad mix')
bx.grid(axis='x',alpha=.15)
fig.suptitle('Removing Amazon search advertising: conditional scenarios',fontsize=17,fontweight='bold',y=.99)
fig.text(.025,.02,'Assumptions: 80% ad removal · 70% lost contribution · 70% of ads funded by 3P sellers · 50% price pass-through.\nFY2025: USD 68.635bn ads; USD 575bn estimated 3P GMV. Fee-base stress is exogenous. No demand equilibrium or forecast probabilities.',fontsize=9,color='#515d6c')
fig.tight_layout(rect=[0,.10,1,.93])
fig.savefig(OUT/'outcomes.png',dpi=180,facecolor=fig.get_facecolor())
fig.savefig(OUT/'outcomes.pdf',facecolor=fig.get_facecolor())

summary = {'ad_revenue_bn':A,'third_party_gmv_bn':G,
           'assumed_average_ad_rate':average_ad_rate,'grid_scenarios':len(sweep),
           'base_scenarios':[dict(name=name,**model(average_ad_rate,**kw)) for name,kw in specs],
           'broad_profit_margin_sensitivity':[model(.10,contribution=m,scope='all') for m in [.5,.7,.9]]}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
