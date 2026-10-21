#!/usr/bin/env python3
"""
Generate a professional, academic 16:9 PowerPoint presentation for BTP Mid-Evaluation.
Student: Chirag Sharma (S20240010223)
Advisor: Dr. Bheemappa Halavar
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PPTX = os.path.join(SCRIPT_DIR, "BTP_Mid_Evaluation_Chirag_Sharma.pptx")

# Color Palette (Dark Theme / Academic Blue)
BG_DARK       = RGBColor(11, 19, 43)    # #0B132B
CARD_SURFACE  = RGBColor(30, 41, 59)    # #1E293B
PRIMARY_BLUE  = RGBColor(56, 189, 248)  # #38BDF8
ACCENT_GREEN  = RGBColor(16, 185, 129)  # #10B981
PURPLE_LIGHT  = RGBColor(168, 85, 247)  # #A855F7
AMBER_COLOR   = RGBColor(245, 158, 11)  # #F59E0B
TEXT_WHITE    = RGBColor(255, 255, 255) # #FFFFFF
TEXT_MUTED    = RGBColor(148, 163, 184) # #94A3B8
BORDER_COLOR  = RGBColor(51, 65, 85)    # #334155

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

def create_base_slide(title_text, tag_text, slide_num):
    slide = prs.slides.add_slide(blank_layout)

    # 1. Background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_DARK
    bg.line.fill.background()

    # 2. Top Accent Line
    top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.06))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = PRIMARY_BLUE
    top_bar.line.fill.background()

    # 3. Slide Header
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.8))
    tf = header_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.name = "Arial"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE

    # Tag Badge
    if tag_text:
        tag_box = slide.shapes.add_textbox(Inches(10.2), Inches(0.4), Inches(2.3), Inches(0.4))
        ttf = tag_box.text_frame
        tp = ttf.paragraphs[0]
        tp.alignment = PP_ALIGN.RIGHT
        tp.text = f"[{tag_text.upper()}]"
        tp.font.name = "Arial"
        tp.font.size = Pt(11)
        tp.font.bold = True
        tp.font.color.rgb = ACCENT_GREEN

    # 4. Slide Footer
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.733), Inches(0.4))
    ftf = footer_box.text_frame
    fp = ftf.paragraphs[0]
    fp.text = f"Chirag Sharma (S20240010223)  |  Guide: Dr. Bheemappa Halavar  |  IIIT Sri City  |  Slide {slide_num} of 7"
    fp.font.name = "Arial"
    fp.font.size = Pt(10)
    fp.font.color.rgb = TEXT_MUTED

    return slide

def add_card(slide, left, top, width, height, title, items, title_color=PRIMARY_BLUE):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = CARD_SURFACE
    card.line.color.rgb = BORDER_COLOR
    card.line.width = Pt(1)

    tb = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.15), width - Inches(0.3), height - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True

    if title:
        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = "Arial"
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = title_color
        p0.space_after = Pt(10)

    for item in items:
        p = tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.name = "Arial"
        p.font.size = Pt(11)
        p.font.color.rgb = TEXT_WHITE
        p.space_after = Pt(6)

# ==============================================================================
# SLIDE 1: Title Slide
# ==============================================================================
s1 = prs.slides.add_slide(blank_layout)
bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
bg1.fill.solid()
bg1.fill.fore_color.rgb = BG_DARK
bg1.line.fill.background()

top_bar1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.08))
top_bar1.fill.solid()
top_bar1.fill.fore_color.rgb = PRIMARY_BLUE
top_bar1.line.fill.background()

# Badge
badge = s1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.733), Inches(0.5))
btf = badge.text_frame
bp = btf.paragraphs[0]
bp.alignment = PP_ALIGN.CENTER
bp.text = "BACHELOR THESIS PROJECT (BTP) — MID-EVALUATION REVIEW"
bp.font.name = "Arial"
bp.font.size = Pt(12)
bp.font.bold = True
bp.font.color.rgb = PRIMARY_BLUE

# Title
tbox = s1.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.733), Inches(1.8))
ttf = tbox.text_frame
ttf.word_wrap = True
tp = ttf.paragraphs[0]
tp.alignment = PP_ALIGN.CENTER
tp.text = "Zero-Overhead Prefetch-Resilient LLC\nReplacement Policy for Multicore Systems"
tp.font.name = "Arial"
tp.font.size = Pt(32)
tp.font.bold = True
tp.font.color.rgb = TEXT_WHITE

# Subtitle
stbox = s1.shapes.add_textbox(Inches(0.8), Inches(3.6), Inches(11.733), Inches(0.8))
stf = stbox.text_frame
stp = stf.paragraphs[0]
stp.alignment = PP_ALIGN.CENTER
stp.text = "Eliminating Multicore Cache Thrashing & Speculative Pollution with Zero Extra Hardware Storage"
stp.font.name = "Arial"
stp.font.size = Pt(15)
stp.font.color.rgb = TEXT_MUTED

# Meta Card 1 (Student)
mc1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.3), Inches(4.7), Inches(4.0), Inches(1.6))
mc1.fill.solid()
mc1.fill.fore_color.rgb = CARD_SURFACE
mc1.line.color.rgb = BORDER_COLOR
mct1 = s1.shapes.add_textbox(Inches(2.5), Inches(4.8), Inches(3.6), Inches(1.4))
mtf1 = mct1.text_frame
p = mtf1.paragraphs[0]
p.text = "PRESENTER"
p.font.size = Pt(10)
p.font.bold = True
p.font.color.rgb = TEXT_MUTED
p2 = mtf1.add_paragraph()
p2.text = "Chirag Sharma"
p2.font.size = Pt(16)
p2.font.bold = True
p2.font.color.rgb = TEXT_WHITE
p3 = mtf1.add_paragraph()
p3.text = "Roll No: S20240010223 | B.Tech CSE"
p3.font.size = Pt(11)
p3.font.color.rgb = PRIMARY_BLUE

# Meta Card 2 (Advisor)
mc2 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.0), Inches(4.7), Inches(4.0), Inches(1.6))
mc2.fill.solid()
mc2.fill.fore_color.rgb = CARD_SURFACE
mc2.line.color.rgb = BORDER_COLOR
mct2 = s1.shapes.add_textbox(Inches(7.2), Inches(4.8), Inches(3.6), Inches(1.4))
mtf2 = mct2.text_frame
p = mtf2.paragraphs[0]
p.text = "PROJECT ADVISOR"
p.font.size = Pt(10)
p.font.bold = True
p.font.color.rgb = TEXT_MUTED
p2 = mtf2.add_paragraph()
p2.text = "Dr. Bheemappa Halavar"
p2.font.size = Pt(16)
p2.font.bold = True
p2.font.color.rgb = TEXT_WHITE
p3 = mtf2.add_paragraph()
p3.text = "Dept. of Computer Science & Engineering"
p3.font.size = Pt(11)
p3.font.color.rgb = ACCENT_GREEN

# Footer
f1 = s1.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.733), Inches(0.4))
f1.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
f1.text_frame.paragraphs[0].text = "Indian Institute of Information Technology, Sri City (IIIT Sri City)  •  Slide 1 of 7"
f1.text_frame.paragraphs[0].font.size = Pt(10)
f1.text_frame.paragraphs[0].font.color.rgb = TEXT_MUTED

# ==============================================================================
# SLIDE 2: Motivation & Background
# ==============================================================================
s2 = create_base_slide("1. Motivation: The Prefetching Dilemma in Shared LLCs", "Background", 2)
add_card(s2, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.1),
         "The Hardware Prefetching Dilemma", [
             "Latency Hiding: Hardware prefetchers (AMPM, IP-Stride, SPP) hide DRAM latency for regular stride & streaming memory accesses (403.gcc, 470.lbm).",
             "Accuracy Collapse: For irregular, graph, and pointer-chasing patterns (429.mcf), prefetch accuracy collapses to under 0.5%.",
             "Speculative Flood: Useless prefetch blocks flood the Last-Level Cache (LLC), generating heavy memory traffic without ever receiving a single hit.",
             "Cache Pollution: Speculative data evicts active demand lines, causing thrashing in shared multi-core setups."
         ], PRIMARY_BLUE)

add_card(s2, Inches(6.9), Inches(1.4), Inches(5.6), Inches(5.1),
         "Multicore Thrashing & Policy Blindness", [
             "Prefetch-Oblivious Policies: Standard LRU and SRRIP treat speculative prefetches with the exact same high priority as demand fills.",
             "Cross-Core Thrashing: In a shared 4-core LLC, inaccurate prefetches from one core (e.g., mcf) prematurely evict active lines of co-running cores.",
             "Severe IPC Collapse: Under cross-core pointer contention, neighbor cores suffer up to 50%+ IPC degradation.",
             "Core Thesis: We need a mechanism that renders the LLC resilient against speculative prefetch pollution without adding hardware tables."
         ], AMBER_COLOR)

# ==============================================================================
# SLIDE 3: Literature Review & Critical Research Gaps
# ==============================================================================
s3 = create_base_slide("2. Literature Review & Identified Research Gaps", "Prior Art", 3)
add_card(s3, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.1),
         "State-of-the-Art Approaches", [
             "Drishti (MICRO 2025): Addresses LLC slicing using per-core GPHT tables & sampled cache selection. Note: Clarified with authors that Drishti is an architectural framework, not a standalone replacement policy; replacement policies must handle prefetch vs. demand.",
             "PACMan (IEEE CAL 2023): Prefetch-aware cache management via accuracy tracking counters and sampling logic.",
             "DRRIP (ISCA 2010): Dynamic RRIP with set-dueling PSEL counters (16 Bytes overhead, 32 leader sets).",
             "SHiP (ISCA 2011): Signature-based hit predictor requiring an 8,192-entry SHCT table (2,048 Bytes / 2 KB of dedicated SRAM!)."
         ], PURPLE_LIGHT)

add_card(s3, Inches(6.9), Inches(1.4), Inches(5.6), Inches(5.1),
         "Critical Research Gaps Identified", [
             "Heavy Hardware Overhead: Prior art requires non-trivial storage budgets (up to 2 KB SRAM for SHiP) and complex hashing/training logic.",
             "Area & Latency Penalties: Dedicated predictor tables consume precious chip area, dynamic energy, and access latency in the critical cache pipeline.",
             "Research Question: Can a lightweight, zero-overhead replacement policy achieve comparable or superior prefetch resilience with ZERO extra storage bits?",
             "Design Goal: Provide robust protection for multicore workloads purely by modulating insertion priority and promotion on hit."
         ], ACCENT_GREEN)

# ==============================================================================
# SLIDE 4: Proposed Policy Architecture
# ==============================================================================
s4 = create_base_slide("3. Proposed Policy Architecture: Demoted Insertion & Hit Promotion", "Core Mechanism", 4)
add_card(s4, Inches(0.8), Inches(1.4), Inches(6.2), Inches(5.1),
         "Three Architectural Principles", [
             "1. Demoted Initial Insertion:\n   • Demand fills insert at standard MRU priority (RRPV = 2).\n   • Speculative prefetch fills insert at distant priority (near-LRU / RRPV = 3).\n   • Useless prefetches sit in the victim position and exit immediately on the next fill without evicting active demand data.",
             "2. Self-Adaptive Hit Promotion:\n   • When a prefetched block receives a cache hit, it is promoted to MRU (RRPV = 0).\n   • Line is reclassified as verified demand data, shielding it from eviction.",
             "3. PA-Adaptive Extension (0.75 Bytes):\n   • 6-bit saturating counter (+3 on prefetch hit, -1 on eviction).\n   • Toggles prefetch insertion between RRPV=2 (streaming) and RRPV=3 (noise filtering).",
             "Zero Storage Cost: Uses existing access_type::PREFETCH pipeline hint."
         ], PRIMARY_BLUE)

chart_use_path = os.path.join(SCRIPT_DIR, "chart_prefetch_usefulness.png")
if os.path.exists(chart_use_path):
    s4.shapes.add_picture(chart_use_path, Inches(7.3), Inches(1.5), width=Inches(5.2))
    cap = s4.shapes.add_textbox(Inches(7.3), Inches(5.5), Inches(5.2), Inches(1.0))
    cp = cap.text_frame.paragraphs[0]
    cp.alignment = PP_ALIGN.CENTER
    cp.text = "Self-Adaptive Filtering: Useful prefetches hit and promote (>50% in gcc), while pointer noise (<0.5% in mcf) is safely pruned without polluting the LLC."
    cp.font.name = "Arial"
    cp.font.size = Pt(10)
    cp.font.color.rgb = TEXT_MUTED

# ==============================================================================
# SLIDE 5: 4-Core Results
# ==============================================================================
s5 = create_base_slide("4. ChampSim 4-Core Heterogeneous Workload Results", "Evaluation", 5)

chart_ipc_path = os.path.join(SCRIPT_DIR, "chart_4core_all_cpus_ipc.png")
if os.path.exists(chart_ipc_path):
    s5.shapes.add_picture(chart_ipc_path, Inches(0.8), Inches(1.5), width=Inches(5.4))

add_card(s5, Inches(6.6), Inches(1.4), Inches(5.9), Inches(5.1),
         "Key Performance Breakthroughs (20M Sim)", [
             "Workload Mix: 403.gcc (Stride) + 429.mcf (Pointer) + 600.perlbench (Compute) + 471.omnetpp (Graph Traversal) on 8MB shared LLC.",
             "CPU 0 (gcc): IPC increases from 0.4248 to 2.1800 (5.13x Speedup / +413% Boost) because useful prefetches hit and promote to MRU.",
             "CPU 1 (mcf): Low-priority insertion prevents mcf's inaccurate pointer noise from thrashing the shared LLC; IPC improves from 0.0743 to 0.0993 (+33.6%).",
             "CPU 2 (perlbench): Working set preserved with stable IPC at 2.019 (protected from cross-core interference).",
             "CPU 3 (omnetpp): Cross-core cache pollution suppressed; IPC increases from 0.2566 to 0.3207 (+25.0%).",
             "Hardware Cost: ZERO extra bits (0 Bytes storage overhead)."
         ], ACCENT_GREEN)

# ==============================================================================
# SLIDE 6: State-of-the-Art Comparison
# ==============================================================================
s6 = create_base_slide("5. Quantitative Comparison Against State-of-the-Art", "Benchmarking", 6)

chart_pareto_path = os.path.join(SCRIPT_DIR, "chart_storage_vs_misses.png")
if os.path.exists(chart_pareto_path):
    s6.shapes.add_picture(chart_pareto_path, Inches(0.8), Inches(1.5), width=Inches(5.4))

# Add Table
table_shape = s6.shapes.add_table(8, 4, Inches(6.5), Inches(1.5), Inches(6.0), Inches(4.0))
tbl = table_shape.table

headers = ["Policy", "LLC Misses", "Hit Rate", "Storage Cost"]
for c, h in enumerate(headers):
    cell = tbl.cell(0, c)
    cell.fill.solid()
    cell.fill.fore_color.rgb = RGBColor(15, 23, 42)
    p = cell.text_frame.paragraphs[0]
    p.text = h
    p.font.name = "Arial"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = PRIMARY_BLUE

rows_data = [
    ("Baseline LRU", "15,720", "73.80%", "0 Bytes"),
    ("Baseline SRRIP", "15,682", "73.86%", "0 Bytes"),
    ("DRRIP (Set Dueling)", "15,617", "73.97%", "16 Bytes"),
    ("SHiP (8K SHCT)", "14,589", "75.68%", "2,048 Bytes (2 KB)"),
    ("PA-LRU (Ours)", "15,528", "74.12%", "0 Bytes (Zero Cost)"),
    ("PA-SRRIP (Ours)", "15,507", "74.15%", "0 Bytes (Zero Cost)"),
    ("PA-Adaptive (Ours)", "15,503", "74.16%", "0.75 Bytes (6 bits)")
]

for r, row in enumerate(rows_data, start=1):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_SURFACE if r % 2 == 0 else RGBColor(24, 34, 49)
        p = cell.text_frame.paragraphs[0]
        p.text = val
        p.font.name = "Arial"
        p.font.size = Pt(9.5)
        p.font.color.rgb = ACCENT_GREEN if "Ours" in row[0] else TEXT_WHITE
        if "Ours" in row[0]:
            p.font.bold = True

cap6 = s6.shapes.add_textbox(Inches(6.5), Inches(5.8), Inches(6.0), Inches(0.8))
cp6 = cap6.text_frame.paragraphs[0]
cp6.text = "Pareto Efficiency: PA-SRRIP and PA-Adaptive deliver miss reduction over standard SRRIP and DRRIP while eliminating the 2 KB dedicated SRAM storage cost of SHiP."
cp6.font.name = "Arial"
cp6.font.size = Pt(10)
cp6.font.color.rgb = TEXT_MUTED

# ==============================================================================
# SLIDE 7: 1-Month Roadmap
# ==============================================================================
s7 = create_base_slide("6. 1-Month Milestone Roadmap to Final Evaluation", "Timeline & Targets", 7)

add_card(s7, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.1),
         "Completed Milestones & Near-Term Goals", [
             "Mid-Evaluation Milestone (Completed Today):\n • Implemented PA-LRU, PA-SRRIP, and PA-Adaptive modules.\n • ChampSim 1-core and 4-core evaluation framework verified.\n • 5.13x speedup proven on heterogeneous multicore mixes.",
             "Week 1 (Oct 22 - Oct 28): Multicore Scaling on GPU Node:\n • Execute 8-core and 16-core shared LLC simulations under severe pointer contention (mcf × 8, mcf × 16).\n • Benchmark aggressive prefetchers: SPP, AMPM, IP-Stride, Bingo.",
             "Week 2 (Oct 29 - Nov 05): Drishti Slicing & Interconnect:\n • Model per-slice prefetch awareness accounting for ring/mesh non-uniform cache access (NUCA) latencies.\n • Evaluate synergy with Drishti's per-core GPHT reuse tables."
         ], PRIMARY_BLUE)

add_card(s7, Inches(6.9), Inches(1.4), Inches(5.6), Inches(5.1),
         "Full Benchmarks & Final Deliverables", [
             "Week 3 (Nov 06 - Nov 12): Full SPEC 2017 Expansion:\n • Scale evaluation across 15+ SPEC CPU traces (lbm, milc, namd, bzip2, xalancbmk, leela, wrf).\n • Conduct long simulation runs (100M - 200M instructions per core) on the server.",
             "Week 4 (Nov 13 - End Eval): Thesis Defense & Final Submission:\n • Comprehensive Energy-Delay Product (EDP), weighted speedup, and fairness index analysis.\n • Final BTP Thesis defense and research paper draft submission.",
             "End-Evaluation Target: A complete, publishable research thesis demonstrating zero-overhead prefetch-resilient LLC management across 16-core sliced architectures."
         ], ACCENT_GREEN)

prs.save(OUTPUT_PPTX)
print(f"Presentation successfully created at: {OUTPUT_PPTX}")
