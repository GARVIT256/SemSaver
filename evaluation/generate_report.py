"""
generate_report.py  —  SemSaver Evaluation HTML Report Generator
=================================================================
Reads evaluation/enhanced_results.json + evaluation/results.json
and writes evaluation/report.html  (self-contained, no dependencies).
"""

import json
from pathlib import Path
from datetime import datetime

ROOT        = Path(__file__).resolve().parent.parent
EVAL_DIR    = ROOT / "evaluation"
ENH_RESULTS = EVAL_DIR / "enhanced_results.json"
OLD_RESULTS = EVAL_DIR / "results.json"
OUT_HTML    = EVAL_DIR / "report.html"

# ── Load data ─────────────────────────────────────────────────────────────────
with open(ENH_RESULTS, encoding="utf-8") as f:
    enh = json.load(f)

old_metrics = {}
if OLD_RESULTS.exists():
    with open(OLD_RESULTS, encoding="utf-8") as f:
        old_data = json.load(f)
    old_metrics = old_data.get("metrics", {})

metrics  = enh["metrics"]
results  = enh["results"]
overall  = metrics["overall"]
per_cat  = metrics["per_category"]
ret      = metrics.get("retrieval_metrics", {})
base_ret = ret.get("base_model", {})
ft_ret   = ret.get("finetuned_model", {})
delta_ret= ret.get("delta", {})

now = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── Category counts ────────────────────────────────────────────────────────────
cat_labels = {"factual":"Factual","multi_hop":"Multi-hop","conceptual":"Conceptual","comparison":"Comparison"}

# ── Old results data (groq vs semsaver) ───────────────────────────────────────
old_g  = old_metrics.get("gemini", {})
old_ss = old_metrics.get("semsaver", {})
old_g_acc  = old_g.get("average_accuracy", 0)
old_ss_acc = old_ss.get("average_accuracy", 0)

# ── Build Q table rows ─────────────────────────────────────────────────────────
table_rows = ""
for r in results[:30]:  # show first 30 in report
    f1_llm = r['llm_token_f1']
    sem_llm = r['llm_semantic_sim']
    b1_llm  = r['llm_bleu1']
    cat     = cat_labels.get(r['category'], r['category'])
    win_cls = "win" if f1_llm >= 0.5 else ("partial" if f1_llm >= 0.25 else "loss")
    table_rows += f"""
    <tr>
      <td class="q-cell">{r['question'][:70]}{"..." if len(r['question'])>70 else ""}</td>
      <td><span class="cat cat-{r['category']}">{cat}</span></td>
      <td class="score {win_cls}">{f1_llm:.3f}</td>
      <td class="score">{sem_llm:.3f}</td>
      <td class="score">{b1_llm:.3f}</td>
    </tr>"""

# ── Retrieval rows ─────────────────────────────────────────────────────────────
ret_rows = ""
for k in ["Recall@1","Recall@3","Recall@5","MRR","separation_gap"]:
    bv = base_ret.get(k, "—")
    fv = ft_ret.get(k, "—")
    dv = delta_ret.get(k, None)
    delta_html = f'<span class="{"delta-pos" if dv and dv>0 else "delta-neg"}">{dv:+.4f}</span>' if dv is not None else "—"
    ret_rows += f"<tr><td>{k}</td><td>{bv}</td><td>{fv if fv else '—'}</td><td>{delta_html}</td></tr>"

# ── Per-category chart data ───────────────────────────────────────────────────
cat_names  = [cat_labels.get(c,c) for c in per_cat]
cat_f1_llm = [per_cat[c]["llm_token_f1"] for c in per_cat]
cat_sem_llm= [per_cat[c]["llm_semantic_sim"] for c in per_cat]
cat_counts = [per_cat[c]["count"] for c in per_cat]

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SemSaver Evaluation Report — {now}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  :root {{
    --bg: #0a0e1a; --surface: #111827; --card: #1a2235;
    --border: #1e2d45; --accent: #6366f1; --accent2: #8b5cf6;
    --green: #10b981; --amber: #f59e0b; --red: #ef4444;
    --text: #e2e8f0; --muted: #64748b; --white: #fff;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }}
  .hero {{ background:linear-gradient(135deg,#1a1f3c 0%,#0f1729 60%,#1a0a2e 100%);
           padding:60px 40px 50px; text-align:center; border-bottom:1px solid var(--border); }}
  .hero h1 {{ font-size:2.6rem; font-weight:700;
              background:linear-gradient(90deg,#a78bfa,#6366f1,#38bdf8); -webkit-background-clip:text;
              -webkit-text-fill-color:transparent; background-clip:text; }}
  .hero p  {{ color:var(--muted); margin-top:10px; font-size:1rem; }}
  .badge   {{ display:inline-block; background:rgba(99,102,241,.18); color:#a78bfa;
              border:1px solid rgba(99,102,241,.3); border-radius:20px; padding:4px 14px;
              font-size:.78rem; margin-top:14px; }}
  .container {{ max-width:1200px; margin:0 auto; padding:40px 24px; }}
  h2 {{ font-size:1.4rem; font-weight:600; color:var(--white); margin:40px 0 16px;
        display:flex; align-items:center; gap:10px; }}
  h2::before {{ content:''; display:block; width:4px; height:22px;
                background:linear-gradient(var(--accent),var(--accent2)); border-radius:2px; }}
  /* KPI cards */
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; }}
  .kpi {{ background:var(--card); border:1px solid var(--border); border-radius:14px;
           padding:22px; text-align:center; transition:.2s; }}
  .kpi:hover {{ border-color:var(--accent); transform:translateY(-2px); }}
  .kpi .val {{ font-size:2.2rem; font-weight:700; margin:8px 0 4px; }}
  .kpi .lbl {{ color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; }}
  .kpi .sub {{ font-size:.75rem; color:var(--muted); margin-top:4px; }}
  .c-green {{ color:var(--green); }} .c-amber {{ color:var(--amber); }}
  .c-blue  {{ color:#38bdf8; }}     .c-purple{{ color:#a78bfa; }}
  /* Comparison bars */
  .compare-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  .compare-card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:24px; }}
  .compare-card h3 {{ font-size:1rem; color:var(--muted); margin-bottom:16px; }}
  .bar-row {{ margin:10px 0; }}
  .bar-row .bar-label {{ font-size:.82rem; color:var(--text); margin-bottom:4px; display:flex; justify-content:space-between; }}
  .bar-bg {{ height:10px; background:rgba(255,255,255,.06); border-radius:5px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:5px; transition:width .6s ease; }}
  .b-accent {{ background:linear-gradient(90deg,var(--accent),var(--accent2)); }}
  .b-green  {{ background:linear-gradient(90deg,var(--green),#059669); }}
  /* Table */
  .tbl-wrap {{ overflow-x:auto; background:var(--card); border:1px solid var(--border);
               border-radius:14px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
  th {{ background:rgba(99,102,241,.12); color:var(--muted); padding:12px 14px;
        text-align:left; font-weight:500; font-size:.78rem; text-transform:uppercase;
        letter-spacing:.05em; border-bottom:1px solid var(--border); }}
  td {{ padding:11px 14px; border-bottom:1px solid rgba(30,45,69,.6); vertical-align:middle; }}
  tr:last-child td {{ border:none; }}
  tr:hover td {{ background:rgba(99,102,241,.05); }}
  .q-cell {{ max-width:360px; color:var(--text); }}
  .score {{ font-weight:600; text-align:center; }}
  .win     {{ color:var(--green); }}
  .partial {{ color:var(--amber); }}
  .loss    {{ color:var(--red); }}
  .cat {{ display:inline-block; padding:2px 10px; border-radius:12px; font-size:.73rem; font-weight:500; }}
  .cat-factual    {{ background:rgba(99,102,241,.15); color:#a78bfa; }}
  .cat-multi_hop  {{ background:rgba(245,158,11,.12); color:#f59e0b; }}
  .cat-conceptual {{ background:rgba(56,189,248,.12); color:#38bdf8; }}
  .cat-comparison {{ background:rgba(16,185,129,.12); color:#10b981; }}
  /* Retrieval table */
  .delta-pos {{ color:var(--green); font-weight:600; }}
  .delta-neg {{ color:var(--red);   font-weight:600; }}
  /* Section divider */
  .divider {{ border:none; border-top:1px solid var(--border); margin:10px 0 30px; }}
  /* Canvas */
  .chart-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  .chart-card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:24px; }}
  .chart-card h3 {{ font-size:.9rem; color:var(--muted); margin-bottom:16px; text-transform:uppercase; letter-spacing:.05em; }}
  canvas {{ max-width:100%; }}
  /* Footer */
  .footer {{ text-align:center; color:var(--muted); font-size:.78rem; padding:30px; margin-top:60px;
             border-top:1px solid var(--border); }}
  @media(max-width:700px) {{
    .compare-grid,.chart-grid {{ grid-template-columns:1fr; }}
    .hero h1 {{ font-size:1.8rem; }}
  }}
</style>
</head>
<body>

<div class="hero">
  <h1>SemSaver Evaluation Report</h1>
  <p>Fine-tuned Embedding Model &amp; LLM Comparison · {now}</p>
  <span class="badge">86 Questions · 9 Chapters · 5 Metrics</span>
</div>

<div class="container">

  <!-- ── KPI Summary ── -->
  <h2>At a Glance</h2>
  <div class="kpi-grid">
    <div class="kpi">
      <div class="lbl">LLM Token F1</div>
      <div class="val c-blue">{overall['llm_avg_token_f1']:.3f}</div>
      <div class="sub">on 86 questions</div>
    </div>
    <div class="kpi">
      <div class="lbl">LLM Semantic Sim</div>
      <div class="val c-purple">{overall['llm_avg_semantic_sim']:.3f}</div>
      <div class="sub">cosine · MiniLM</div>
    </div>
    <div class="kpi">
      <div class="lbl">LLM BLEU-1</div>
      <div class="val c-amber">{overall['llm_avg_bleu1']:.3f}</div>
      <div class="sub">unigram precision</div>
    </div>
    <div class="kpi">
      <div class="lbl">Embedding Recall@1</div>
      <div class="val c-green">{base_ret.get('Recall@1',0):.3f}</div>
      <div class="sub">base MiniLM · 86 Q corpus</div>
    </div>
    <div class="kpi">
      <div class="lbl">Embedding MRR</div>
      <div class="val c-green">{base_ret.get('MRR',0):.3f}</div>
      <div class="sub">mean reciprocal rank</div>
    </div>
    <div class="kpi">
      <div class="lbl">Pos–Neg Gap</div>
      <div class="val c-blue">{base_ret.get('separation_gap',0):.3f}</div>
      <div class="sub">embedding separation</div>
    </div>
    <div class="kpi">
      <div class="lbl">LLM Avg Latency</div>
      <div class="val c-amber">{overall['llm_avg_latency_s']:.2f}s</div>
      <div class="sub">Groq Llama-3.3-70b</div>
    </div>
    <div class="kpi">
      <div class="lbl">Total Questions</div>
      <div class="val c-purple">86</div>
      <div class="sub">30 orig + 56 Chapter9</div>
    </div>
  </div>

  <!-- ── Original SemSaver vs Groq ── -->
  <h2>Original Evaluation: SemSaver RAG vs LLM (30 Qs)</h2>
  <div class="compare-grid">
    <div class="compare-card">
      <h3>Average Accuracy Score (keyword-overlap scorer)</h3>
      <div class="bar-row">
        <div class="bar-label"><span>Groq LLM (no RAG)</span><span>{old_g_acc:.4f}</span></div>
        <div class="bar-bg"><div class="bar-fill b-accent" style="width:{old_g_acc*100:.1f}%"></div></div>
      </div>
      <div class="bar-row">
        <div class="bar-label"><span>SemSaver RAG</span><span>{old_ss_acc:.4f}</span></div>
        <div class="bar-bg"><div class="bar-fill b-green" style="width:{old_ss_acc*100:.1f}%"></div></div>
      </div>
    </div>
    <div class="compare-card">
      <h3>Score Breakdown (30 questions)</h3>
      <div class="bar-row">
        <div class="bar-label"><span>Exact Match (1.0) — LLM</span><span>{old_g.get('exact_match',0)}</span></div>
        <div class="bar-bg"><div class="bar-fill b-accent" style="width:{old_g.get('exact_match',0)/30*100:.1f}%"></div></div>
      </div>
      <div class="bar-row">
        <div class="bar-label"><span>Exact Match (1.0) — SemSaver</span><span>{old_ss.get('exact_match',0)}</span></div>
        <div class="bar-bg"><div class="bar-fill b-green" style="width:{old_ss.get('exact_match',0)/30*100:.1f}%"></div></div>
      </div>
      <div class="bar-row">
        <div class="bar-label"><span>Partial Match (0.5) — LLM</span><span>{old_g.get('partial_match',0)}</span></div>
        <div class="bar-bg"><div class="bar-fill b-accent" style="width:{old_g.get('partial_match',0)/30*100:.1f}%"></div></div>
      </div>
      <div class="bar-row">
        <div class="bar-label"><span>Partial Match (0.5) — SemSaver</span><span>{old_ss.get('partial_match',0)}</span></div>
        <div class="bar-bg"><div class="bar-fill b-green" style="width:{old_ss.get('partial_match',0)/30*100:.1f}%"></div></div>
      </div>
    </div>
  </div>

  <!-- ── Enhanced metrics ── -->
  <h2>Enhanced Metrics: LLM Baseline (86 Qs, Chapter1–9)</h2>
  <div class="compare-grid">
    <div class="compare-card">
      <h3>Token F1 by Category</h3>
      {"".join(f'''<div class="bar-row">
        <div class="bar-label"><span>{cat_labels.get(c,c)} ({per_cat[c]["count"]})</span><span>{per_cat[c]["llm_token_f1"]:.3f}</span></div>
        <div class="bar-bg"><div class="bar-fill b-accent" style="width:{per_cat[c]["llm_token_f1"]*100:.1f}%"></div></div>
      </div>''' for c in per_cat)}
    </div>
    <div class="compare-card">
      <h3>Semantic Similarity by Category</h3>
      {"".join(f'''<div class="bar-row">
        <div class="bar-label"><span>{cat_labels.get(c,c)}</span><span>{per_cat[c]["llm_semantic_sim"]:.3f}</span></div>
        <div class="bar-bg"><div class="bar-fill b-green" style="width:{per_cat[c]["llm_semantic_sim"]*100:.1f}%"></div></div>
      </div>''' for c in per_cat)}
    </div>
  </div>

  <!-- ── Retrieval metrics ── -->
  <h2>Embedding Model — Retrieval Metrics</h2>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>Metric</th><th>Base Model (all-MiniLM-L6-v2)</th>
        <th>Fine-Tuned Model</th><th>Delta (FT − Base)</th>
      </tr></thead>
      <tbody>{ret_rows}</tbody>
    </table>
  </div>
  {"<p style='color:var(--amber);font-size:.82rem;margin-top:10px;'>* Fine-tuned model not found at finetuning/semsaver-ft-model — run <code>python finetuning/train.py</code> first.</p>" if not ft_ret else ""}

  <!-- ── Question table ── -->
  <h2>Per-Question Results (first 30 shown)</h2>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>Question</th><th>Category</th>
        <th>Token F1</th><th>Semantic Sim</th><th>BLEU-1</th>
      </tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>

  <!-- ── Charts ── -->
  <h2>Visual Analysis</h2>
  <div class="chart-grid">
    <div class="chart-card">
      <h3>Retrieval Recall@K — Base Model</h3>
      <canvas id="recallChart"></canvas>
    </div>
    <div class="chart-card">
      <h3>Token F1 by Question Category</h3>
      <canvas id="catChart"></canvas>
    </div>
  </div>

  <!-- ── Methodology ── -->
  <h2>Methodology</h2>
  <div class="compare-card" style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px;">
    <table style="font-size:.85rem;">
      <thead><tr><th>Metric</th><th>Description</th><th>Why it matters</th></tr></thead>
      <tbody>
        <tr><td><strong>Token F1</strong></td><td>Harmonic mean of token-level precision &amp; recall</td><td>Penalises both verbosity and incompleteness</td></tr>
        <tr><td><strong>BLEU-1</strong></td><td>Unigram precision with brevity penalty</td><td>Classic MT metric; rewards key-word coverage</td></tr>
        <tr><td><strong>Semantic Similarity</strong></td><td>Cosine similarity of MiniLM embeddings</td><td>Captures meaning beyond exact word overlap</td></tr>
        <tr><td><strong>Recall@K</strong></td><td>Fraction of queries where correct answer is in top-K</td><td>Core retrieval quality indicator</td></tr>
        <tr><td><strong>MRR</strong></td><td>Mean Reciprocal Rank of the first correct hit</td><td>Rewards ranking the correct chunk highest</td></tr>
        <tr><td><strong>Sep. Gap</strong></td><td>Mean (pos_sim − neg_sim) across all queries</td><td>Measures how well the model separates relevant vs irrelevant</td></tr>
      </tbody>
    </table>
  </div>

</div>

<div class="footer">
  SemSaver Evaluation Report &nbsp;·&nbsp; Generated {now} &nbsp;·&nbsp;
  86 questions from Chapter1–9 PDFs &nbsp;·&nbsp; Model: Groq Llama-3.3-70b + all-MiniLM-L6-v2
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#1e2d45';

// Recall@K chart
new Chart(document.getElementById('recallChart'), {{
  type:'bar',
  data:{{
    labels:['Recall@1','Recall@3','Recall@5','MRR'],
    datasets:[{{
      label:'Base Model',
      data:[{base_ret.get('Recall@1',0)},{base_ret.get('Recall@3',0)},{base_ret.get('Recall@5',0)},{base_ret.get('MRR',0)}],
      backgroundColor:['rgba(99,102,241,.7)','rgba(99,102,241,.7)','rgba(99,102,241,.7)','rgba(139,92,246,.7)'],
      borderRadius:6
    }}{(f''',{{
      label:'Fine-Tuned',
      data:[{ft_ret.get('Recall@1',0)},{ft_ret.get('Recall@3',0)},{ft_ret.get('Recall@5',0)},{ft_ret.get('MRR',0)}],
      backgroundColor:['rgba(16,185,129,.7)','rgba(16,185,129,.7)','rgba(16,185,129,.7)','rgba(16,185,129,.7)'],
      borderRadius:6
    }}''' if ft_ret else '')}
  ]
  }},
  options:{{scales:{{y:{{beginAtZero:true,max:1,ticks:{{callback:v=>v.toFixed(2)}}}}}},plugins:{{legend:{{labels:{{color:'#94a3b8'}}}}}}}}
}});

// Category Token F1
new Chart(document.getElementById('catChart'), {{
  type:'bar',
  data:{{
    labels:{json.dumps(cat_names)},
    datasets:[
      {{label:'Token F1', data:{json.dumps(cat_f1_llm)}, backgroundColor:'rgba(99,102,241,.7)', borderRadius:6}},
      {{label:'Semantic Sim', data:{json.dumps(cat_sem_llm)}, backgroundColor:'rgba(56,189,248,.7)', borderRadius:6}}
    ]
  }},
  options:{{scales:{{y:{{beginAtZero:true,max:1}}}},plugins:{{legend:{{labels:{{color:'#94a3b8'}}}}}}}}
}});
</script>
</body>
</html>"""

OUT_HTML.write_text(HTML, encoding="utf-8")
print(f"Report saved -> {OUT_HTML}")
