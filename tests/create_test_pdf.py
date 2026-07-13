"""Create a test PDF containing a bar chart and a flow diagram.

This PDF is used for acceptance testing of the VLM pipeline:
the VLM should produce coherent text descriptions of each visual
that are then retrievable via the vector DB.
"""

import fitz  # pymupdf
import sys
import os


def create_test_pdf(output_path: str) -> None:
    """Create a PDF with:
    - Page 1: Text introduction + bar chart (revenue by quarter)
    - Page 2: Text + flow diagram (system architecture)
    - Page 3: Text with Chinese content + bar chart (quarterly results)
    """
    doc = fitz.open()

    # ── Page 1: English bar chart ──────────────────────────────────────
    page1 = doc.new_page(width=612, height=792)  # US Letter

    # Title text
    page1.insert_text((72, 50), "Q3 2025 Revenue Report", fontsize=16, fontname="helv")
    page1.insert_text((72, 80), "The following chart shows revenue by quarter:",
                      fontsize=11, fontname="helv")

    # Draw bar chart
    chart_x = 72
    chart_y = 120
    chart_w = 468
    chart_h = 280
    bar_count = 4
    bar_max_h = 220
    bar_values = [45, 62, 78, 91]  # in millions
    bar_labels = ["Q1", "Q2", "Q3", "Q4"]
    bar_colors = [(0.2, 0.4, 0.8), (0.2, 0.6, 0.4), (0.8, 0.5, 0.2), (0.8, 0.2, 0.3)]

    # Chart background
    page1.draw_rect(
        fitz.Rect(chart_x - 10, chart_y - 10, chart_x + chart_w + 10, chart_y + chart_h + 30),
        color=(0.9, 0.9, 0.9), fill=(0.97, 0.97, 0.97),
    )

    # Y-axis
    page1.draw_line(fitz.Point(chart_x, chart_y), fitz.Point(chart_x, chart_y + bar_max_h))
    # X-axis
    page1.draw_line(fitz.Point(chart_x, chart_y + bar_max_h),
                    fitz.Point(chart_x + chart_w, chart_y + bar_max_h))

    # Bars
    bar_width = chart_w / (bar_count * 1.5)
    bar_gap = bar_width * 0.5
    max_val = max(bar_values)

    for i, (val, label, color) in enumerate(zip(bar_values, bar_labels, bar_colors)):
        bx = chart_x + bar_gap + i * (bar_width + bar_gap)
        bh = (val / max_val) * bar_max_h
        by = chart_y + bar_max_h - bh

        # Draw bar
        page1.draw_rect(
            fitz.Rect(bx, by, bx + bar_width, chart_y + bar_max_h),
            color=color, fill=color,
        )

        # Value label above bar
        page1.insert_text(
            (bx + bar_width / 2 - 15, by - 5),
            f"${val}M", fontsize=9, fontname="helv",
        )

        # X-axis label
        page1.insert_text(
            (bx + bar_width / 2 - 10, chart_y + bar_max_h + 15),
            label, fontsize=10, fontname="helv",
        )

    # Axis labels
    page1.insert_text((chart_x - 5, chart_y - 5), "Revenue ($M)",
                      fontsize=9, fontname="helv")
    page1.insert_text((chart_x + chart_w / 2 - 30, chart_y + bar_max_h + 35),
                      "Quarter", fontsize=10, fontname="helv")

    # ── Page 2: Flow diagram ───────────────────────────────────────────
    page2 = doc.new_page(width=612, height=792)

    page2.insert_text((72, 50), "System Architecture", fontsize=16, fontname="helv")
    page2.insert_text((72, 80), "The diagram below shows the data flow through the system:",
                      fontsize=11, fontname="helv")

    # Draw flow diagram boxes and arrows
    diagram_y = 120
    box_w = 140
    box_h = 50
    gap = 40

    boxes = [
        ("Input\nDocuments", (0.3, 0.5, 0.8)),
        ("Text\nExtraction", (0.3, 0.7, 0.4)),
        ("Chunking &\nEmbedding", (0.8, 0.6, 0.2)),
        ("Vector\nDatabase", (0.7, 0.3, 0.3)),
        ("Query\nEngine", (0.5, 0.3, 0.7)),
    ]

    total_w = len(boxes) * box_w + (len(boxes) - 1) * gap
    start_x = (612 - total_w) / 2

    for i, (label, color) in enumerate(boxes):
        bx = start_x + i * (box_w + gap)
        by = diagram_y

        # Draw box
        page2.draw_rect(
            fitz.Rect(bx, by, bx + box_w, by + box_h),
            color=color, fill=color, width=2,
        )

        # Draw label
        lines = label.split("\n")
        for j, line in enumerate(lines):
            page2.insert_text(
                (bx + box_w / 2 - len(line) * 3, by + box_h / 2 + 5 + (j - len(lines) / 2) * 12),
                line, fontsize=9, fontname="helv", color=(1, 1, 1),
            )

        # Draw arrow to next box
        if i < len(boxes) - 1:
            ax_start = bx + box_w
            ax_end = bx + box_w + gap
            ay = by + box_h / 2
            page2.draw_line(fitz.Point(ax_start, ay), fitz.Point(ax_end, ay),
                           color=(0.3, 0.3, 0.3), width=2)
            # Arrowhead
            page2.draw_line(fitz.Point(ax_end - 8, ay - 4), fitz.Point(ax_end, ay),
                           color=(0.3, 0.3, 0.3), width=2)
            page2.draw_line(fitz.Point(ax_end - 8, ay + 4), fitz.Point(ax_end, ay),
                           color=(0.3, 0.3, 0.3), width=2)

    # Label
    page2.insert_text((72, diagram_y + box_h + 40),
                      "Figure 1: System architecture data flow",
                      fontsize=10, fontname="helv")

    # ── Page 3: Chinese bar chart ──────────────────────────────────────
    page3 = doc.new_page(width=612, height=792)

    page3.insert_text((72, 50), "2025年第三季度销售报告", fontsize=16, fontname="helv")
    page3.insert_text((72, 80), "下图显示了各季度的销售额：", fontsize=11, fontname="helv")

    # Draw bar chart (same structure as page 1, different values)
    c_chart_x = 72
    c_chart_y = 120
    c_chart_w = 468
    c_chart_h = 280
    c_bar_max_h = 220
    c_bar_values = [38, 55, 72, 85]
    c_bar_labels = ["Q1", "Q2", "Q3", "Q4"]
    c_bar_colors = [(0.2, 0.4, 0.8), (0.2, 0.6, 0.4), (0.8, 0.5, 0.2), (0.8, 0.2, 0.3)]

    # Chart background
    page3.draw_rect(
        fitz.Rect(c_chart_x - 10, c_chart_y - 10,
                  c_chart_x + c_chart_w + 10, c_chart_y + c_chart_h + 30),
        color=(0.9, 0.9, 0.9), fill=(0.97, 0.97, 0.97),
    )

    # Axes
    page3.draw_line(fitz.Point(c_chart_x, c_chart_y),
                    fitz.Point(c_chart_x, c_chart_y + c_bar_max_h))
    page3.draw_line(fitz.Point(c_chart_x, c_chart_y + c_bar_max_h),
                    fitz.Point(c_chart_x + c_chart_w, c_chart_y + c_bar_max_h))

    # Bars
    c_bar_width = c_chart_w / (len(c_bar_values) * 1.5)
    c_bar_gap = c_bar_width * 0.5
    c_max_val = max(c_bar_values)

    for i, (val, label, color) in enumerate(zip(c_bar_values, c_bar_labels, c_bar_colors)):
        bx = c_chart_x + c_bar_gap + i * (c_bar_width + c_bar_gap)
        bh = (val / c_max_val) * c_bar_max_h
        by = c_chart_y + c_bar_max_h - bh

        page3.draw_rect(
            fitz.Rect(bx, by, bx + c_bar_width, c_chart_y + c_bar_max_h),
            color=color, fill=color,
        )

        page3.insert_text(
            (bx + c_bar_width / 2 - 12, by - 5),
            f"{val}M", fontsize=9, fontname="helv",
        )

        page3.insert_text(
            (bx + c_bar_width / 2 - 8, c_chart_y + c_bar_max_h + 15),
            label, fontsize=10, fontname="helv",
        )

    # Save
    doc.save(output_path)
    doc.close()
    print(f"Test PDF created: {output_path}")
    print(f"  3 pages: English bar chart, flow diagram, Chinese bar chart")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "test_visual.pdf"
    create_test_pdf(out)
