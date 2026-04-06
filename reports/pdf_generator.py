from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from dashboards.shared import DISPLAY_NAMES, TIER_LABELS


class PortfolioPDFReport:
    """Base class for all PDF reports."""

    def __init__(self, settings: dict):
        self.settings = settings
        theme = settings.get("theme", {})
        self.dusk_blue = colors.HexColor(
            theme.get("dusk_blue", "#355070")
        )
        self.dusty_lavender = colors.HexColor(
            theme.get("dusty_lavender", "#6d597a")
        )
        self.rosewood = colors.HexColor(
            theme.get("rosewood", "#b56576")
        )
        self.light_coral = colors.HexColor(
            theme.get("light_coral", "#e56b6f")
        )
        self.sage_green = colors.HexColor(
            theme.get("sage_green", "#6b8f71")
        )
        self.light_bronze = colors.HexColor(
            theme.get("light_bronze", "#eaac8b")
        )
        self.accent = self.dusk_blue
        pdf_cfg = settings.get("pdf", {})
        self.version = pdf_cfg.get("version", "V7 MVP")
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()

    def _add_custom_styles(self):
        self.styles.add(
            ParagraphStyle(
                "ReportTitle",
                parent=self.styles["Heading1"],
                fontSize=18,
                textColor=self.accent,
                spaceAfter=12,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=self.accent,
                spaceAfter=8,
            )
        )

    def _build_table(
        self, data: list[list[str]], col_widths: list[float] | None = None
    ) -> Table:
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), self.accent),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, self.dusty_lavender),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white,
                colors.Color(
                    self.light_bronze.red,
                    self.light_bronze.green,
                    self.light_bronze.blue,
                    0.2,
                ),
            ]),
        ]

        # Color Action cells
        action_colors = {
            "BUY": (self.sage_green, colors.white),
            "ADD": (self.dusk_blue, colors.white),
            "HOLD": (self.light_bronze, self.dusk_blue),
            "SELL": (self.light_coral, colors.white),
            "No Score": (
                colors.Color(0.96, 0.90, 0.85),
                self.dusk_blue,
            ),
        }
        header = data[0] if data else []
        if "Action" in header:
            col_idx = header.index("Action")
            for row_idx, row in enumerate(data[1:], start=1):
                action = row[col_idx]
                if action in action_colors:
                    bg, fg = action_colors[action]
                    style.append(
                        ("BACKGROUND", (col_idx, row_idx),
                         (col_idx, row_idx), bg)
                    )
                    style.append(
                        ("TEXTCOLOR", (col_idx, row_idx),
                         (col_idx, row_idx), fg)
                    )

        table.setStyle(TableStyle(style))
        return table

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        canvas.drawString(
            inch, 0.5 * inch, f"{self.version} | Generated {now}"
        )
        canvas.drawRightString(
            doc.pagesize[0] - inch,
            0.5 * inch,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    def _df_to_table_data(
        self, df: pd.DataFrame, columns: list[str]
    ) -> list[list[str]]:
        available = [c for c in columns if c in df.columns]
        header = [
            DISPLAY_NAMES.get(c, c.replace("_", " ").title())
            for c in available
        ]
        rows = []
        for _, row in df.iterrows():
            cells = []
            for c in available:
                val = row[c]
                if pd.isna(val):
                    cells.append("—")
                elif isinstance(val, float):
                    cells.append(f"{val:.2f}")
                elif val == "NO_DATA":
                    cells.append("No Score")
                elif val in TIER_LABELS:
                    cells.append(TIER_LABELS[val])
                else:
                    cells.append(str(val))
            rows.append(cells)
        return [header, *rows]


class DailyPDFReport(PortfolioPDFReport):
    def generate(
        self, df: pd.DataFrame, output_dir: Path
    ) -> Path:
        filename = f"Daily_Report_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
        path = output_dir / filename
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        elements = []
        elements.append(
            Paragraph("Daily Portfolio Report", self.styles["ReportTitle"])
        )
        elements.append(Spacer(1, 12))

        # Summary
        total = df["market_value"].sum()
        elements.append(
            Paragraph(
                f"Portfolio Value: ${total:,.2f} | "
                f"Positions: {len(df)}",
                self.styles["Normal"],
            )
        )
        elements.append(Spacer(1, 12))

        # Decision table
        elements.append(
            Paragraph("Decision Dashboard", self.styles["SectionHeader"])
        )
        cols = [
            "ticker", "score", "ev_adjusted", "risk_score",
            "action", "portfolio_weight_pct", "target_weight_pct",
        ]
        data = self._df_to_table_data(df, cols)
        elements.append(self._build_table(data))
        elements.append(Spacer(1, 12))

        # Risk flags
        sell_threshold = (
            self.settings.get("model", {})
            .get("risk_thresholds", {})
            .get("sell_candidate", 9)
        )
        high_risk = df[df["risk_score"] >= sell_threshold]
        if not high_risk.empty:
            elements.append(
                Paragraph("Risk Flags", self.styles["SectionHeader"])
            )
            for _, row in high_risk.iterrows():
                elements.append(
                    Paragraph(
                        f"<b>{row['ticker']}</b> — Risk {row['risk_score']} "
                        f"| {row.get('action', 'N/A')}",
                        self.styles["Normal"],
                    )
                )
            elements.append(Spacer(1, 12))

        doc.build(elements, onLaterPages=self._footer, onFirstPage=self._footer)
        return path


class WeeklyPDFReport(PortfolioPDFReport):
    def generate(
        self, df: pd.DataFrame, output_dir: Path
    ) -> Path:
        filename = f"Weekly_Report_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
        path = output_dir / filename
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        elements = []
        elements.append(
            Paragraph("Weekly Portfolio Review", self.styles["ReportTitle"])
        )
        elements.append(Spacer(1, 12))

        # Scoring table
        elements.append(
            Paragraph("Portfolio Scoring", self.styles["SectionHeader"])
        )
        cols = [
            "ticker", "score", "ev_adjusted", "risk_score",
            "tier", "action", "portfolio_weight_pct", "target_weight_pct",
        ]
        data = self._df_to_table_data(df, cols)
        elements.append(self._build_table(data))
        elements.append(Spacer(1, 12))

        # Rebalance plan
        from modules.rebalance_engine import calculate_rebalance_plan

        total_value = df["market_value"].sum()
        plan = calculate_rebalance_plan(df, total_value, self.settings)
        active = plan[plan["rebalance_action"] != "HOLD"]
        if not active.empty:
            elements.append(
                Paragraph("Rebalance Plan", self.styles["SectionHeader"])
            )
            rebal_cols = [
                "ticker", "rebalance_action",
                "delta_weight_pct", "delta_value",
            ]
            data = self._df_to_table_data(active, rebal_cols)
            elements.append(self._build_table(data))
            elements.append(Spacer(1, 12))

        # Best ideas
        if df["ev_adjusted"].notna().any():
            elements.append(
                Paragraph("Best Ideas (Top 5)", self.styles["SectionHeader"])
            )
            top5 = df.nlargest(5, "ev_adjusted")
            best_cols = ["ticker", "score", "ev_adjusted", "tier", "action"]
            data = self._df_to_table_data(top5, best_cols)
            elements.append(self._build_table(data))

        doc.build(elements, onLaterPages=self._footer, onFirstPage=self._footer)
        return path


class MonthlyPDFReport(PortfolioPDFReport):
    def generate(
        self, df: pd.DataFrame, output_dir: Path
    ) -> Path:
        filename = f"Monthly_Report_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
        path = output_dir / filename
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        elements = []
        elements.append(
            Paragraph(
                "Monthly Strategic Review", self.styles["ReportTitle"]
            )
        )
        elements.append(Spacer(1, 12))

        # Summary
        total = df["market_value"].sum()
        elements.append(
            Paragraph(
                f"Portfolio Value: ${total:,.2f} | "
                f"Positions: {len(df)}",
                self.styles["Normal"],
            )
        )
        elements.append(Spacer(1, 12))

        # Tier breakdown
        if "tier" in df.columns and df["tier"].notna().any():
            elements.append(
                Paragraph(
                    "Strategic Positioning",
                    self.styles["SectionHeader"],
                )
            )
            tiers = df.groupby("tier").agg(
                positions=("ticker", "count"),
                weight=("portfolio_weight_pct", "sum"),
            ).reset_index()
            data = self._df_to_table_data(
                tiers, ["tier", "positions", "weight"]
            )
            elements.append(self._build_table(data))
            elements.append(Spacer(1, 12))

        # Full portfolio
        elements.append(
            Paragraph("Full Portfolio", self.styles["SectionHeader"])
        )
        cols = [
            "ticker", "market_value", "portfolio_weight_pct",
            "score", "ev_adjusted", "risk_score", "action",
        ]
        data = self._df_to_table_data(df, cols)
        elements.append(self._build_table(data))

        doc.build(elements, onLaterPages=self._footer, onFirstPage=self._footer)
        return path
