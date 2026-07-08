"""Rich console rendering of an AnalysisReport."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.services.call_analysis.schemas import AnalysisReport


def render(report: AnalysisReport) -> None:
    console = Console()

    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold cyan")
    header.add_column()
    if report.call_info:
        header.add_row("Call", report.call_info.get("call_id", ""))
        header.add_row("Direction", str(report.call_info.get("direction", "")))
    if report.stt:
        header.add_row("Duration", f"{report.stt.duration_seconds:.0f}s")
        header.add_row("STT model", f"{report.stt.provider}/{report.stt.model}")
        if report.stt.language:
            header.add_row("Language", report.stt.language)
        if report.stt.topics:
            header.add_row("Topics", ", ".join(report.stt.topics))
        if report.stt.intents:
            header.add_row("Intents", ", ".join(report.stt.intents))
    console.print(Panel(header, title="[bold]Call Analysis[/bold]", border_style="cyan"))

    if report.stt and report.stt.deepgram_summary:
        console.print(Panel(report.stt.deepgram_summary, title="STT Summary", border_style="blue"))

    if report.metrics:
        m = report.metrics
        table = Table(title="Speaker Metrics", border_style="green")
        for col in (
            "Speaker", "Role", "Talk time", "Talk %", "Words", "WPM",
            "Fillers", "Longest monologue", "Interruptions", "Avg response",
        ):
            table.add_column(col)
        for s in m.speakers:
            table.add_row(
                str(s.speaker),
                s.role or "-",
                f"{s.talk_time_seconds:.0f}s",
                _bar(s.talk_time_pct),
                str(s.words),
                f"{s.wpm:.0f}",
                str(s.filler_word_count),
                f"{s.longest_monologue_seconds:.0f}s",
                str(s.interruptions_initiated),
                f"{s.avg_response_latency_seconds:.2f}s" if s.avg_response_latency_seconds is not None else "-",
            )
        console.print(table)
        console.print(
            f"  Silence: [yellow]{m.silence_total_seconds:.0f}s ({m.silence_pct}%)[/yellow]"
            f"  Dead-air events: [yellow]{len(m.dead_air_events)}[/yellow]"
            f"  Turns: {m.turn_count}"
            f"  Overlap: {m.overlap_total_seconds:.1f}s\n"
        )

    if report.crosscheck and report.crosscheck.live_transcript_available:
        c = report.crosscheck
        style = "red" if (c.wer or 0) > 0.3 else "green"
        console.print(
            f"[bold]Transcript cross-check:[/bold] WER [{style}]{c.wer}[/{style}], "
            f"turn alignment {c.turn_alignment_rate}, "
            f"{len(c.discrepancies)} discrepancies"
        )
        for d in c.discrepancies[:10]:
            console.print(f"  [dim]{d.kind}[/dim] live={d.live_text!r} stt={d.stt_text!r}")
        if len(c.discrepancies) > 10:
            console.print(f"  [dim]... and {len(c.discrepancies) - 10} more (see JSON report)[/dim]")

    if report.llm_analysis:
        llm = report.llm_analysis
        body = (
            f"[bold]Outcome:[/bold] {llm.call_outcome}\n"
            f"[bold]Quality score:[/bold] {llm.agent_quality_score}/10 — {llm.agent_quality_rationale}\n"
            f"[bold]Sentiment arc:[/bold] {llm.sentiment_arc}\n\n"
            f"{llm.summary}"
        )
        if llm.action_items:
            body += "\n\n[bold]Action items:[/bold]\n" + "\n".join(f"  • {a}" for a in llm.action_items)
        if llm.compliance_flags:
            body += "\n\n[bold red]Compliance flags:[/bold red]\n" + "\n".join(
                f"  ⚠ {f}" for f in llm.compliance_flags
            )
        console.print(Panel(body, title=f"LLM Analysis ({llm.provider}/{llm.model})", border_style="magenta"))

    for layer in report.skipped_layers:
        console.print(f"[yellow]Skipped:[/yellow] {layer}")
    for warning in report.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


def _bar(pct: float, width: int = 12) -> str:
    filled = int(round(width * pct / 100))
    return f"{'█' * filled}{'░' * (width - filled)} {pct}%"
