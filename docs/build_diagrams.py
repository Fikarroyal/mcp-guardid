"""Regenerates the README diagrams and colored Lucide icons.

    npm install lucide-static   (in any temp folder)
    python docs/build_diagrams.py /path/to/node_modules/lucide-static/icons

Icons are the real Lucide paths (ISC license), embedded so the README renders
identically on GitHub, in editors, and offline.
"""
import re
import sys
from pathlib import Path

ICON_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/lu/node_modules/lucide-static/icons")
OUT = Path(__file__).resolve().parent
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"


def icon_inner(name: str) -> str:
    svg = (ICON_DIR / f"{name}.svg").read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
    return inner.strip()


def write_icon(name: str, color: str) -> None:
    body = icon_inner(name)
    (OUT / "icons" / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def icon_at(name: str, x: float, y: float, size: float, color: str) -> str:
    s = size / 24
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{icon_inner(name)}</g>')


# ------------------------------------------------------------------ pipeline
STAGES = [
    ("Understand", "#3452E1", "#EBEFFD", [
        ("user-round", "Request", ["Natural language,", "Indonesian or English"]),
        ("scan-text", "Intent", ["Rules for risky verbs,", "embeddings for the rest"]),
        ("radar", "Retrieval", ["Top K tools from the", "semantic vector index"]),
    ]),
    ("Decide", "#7C3AED", "#F3EDFE", [
        ("users", "Role and context", ["Who is asking and", "which target is meant"]),
        ("gauge", "Risk", ["LOW, MEDIUM, HIGH", "or CRITICAL"]),
        ("lock-keyhole", "Permission", ["Server side RBAC by", "the Policy Engine"]),
        ("arrow-down-wide-narrow", "Ranking", ["FinalScore from six", "weighted signals"]),
    ]),
    ("Act", "#EA580C", "#FFF1E8", [
        ("badge-check", "Approval gate", ["HIGH and CRITICAL wait", "for a human decision"]),
        ("server-cog", "Execution", ["MCP Gateway with schema", "check and timeout"]),
        ("clipboard-list", "Evidence", ["Every result gets an", "execution ID"]),
    ]),
    ("Verify and record", "#059669", "#E6F6F0", [
        ("shield-check", "Verifier", ["Evidence, injection and", "policy checks"]),
        ("message-square-text", "Answer", ["Written only from the", "collected evidence"]),
        ("scroll-text", "Audit trail", ["Immutable record of", "every step"]),
    ]),
]


def build_pipeline() -> str:
    W, colw, gap, pad = 1200, 270, 30, 15
    cardh, cardgap, top = 88, 14, 78
    H = top + 4 * (cardh + cardgap) + 14
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
           '<defs><filter id="sh" x="-5%" y="-5%" width="110%" height="120%"><feDropShadow dx="0" dy="1.5" stdDeviation="2" flood-color="#0F1524" flood-opacity="0.10"/></filter></defs>',
           f'<rect width="{W}" height="{H}" rx="18" fill="#F7F8FA"/>']
    n = 0
    for ci, (title, color, tint, steps) in enumerate(STAGES):
        x = pad + ci * (colw + gap)
        col_h = 46 + len(steps) * (cardh + cardgap) + 6
        out.append(f'<rect x="{x}" y="14" width="{colw}" height="{H - 28}" rx="14" fill="{tint}"/>')
        out.append(f'<rect x="{x + 14}" y="26" width="{colw - 28}" height="30" rx="15" fill="{color}"/>')
        out.append(f'<text x="{x + colw / 2}" y="46" text-anchor="middle" fill="#fff" font-size="13.5" font-weight="700" letter-spacing="0.4">{title.upper()}</text>')
        if ci < len(STAGES) - 1:
            ax = x + colw + gap / 2
            out.append(f'<path d="M{ax - 6},{41} L{ax + 6},{41} M{ax + 1},{35} L{ax + 7},{41} L{ax + 1},{47}" stroke="#94A3B8" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        for si, (icon, name, lines) in enumerate(steps):
            n += 1
            cy = top + si * (cardh + cardgap)
            cx = x + 12
            cw = colw - 24
            out.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{cardh}" rx="12" fill="#fff" filter="url(#sh)"/>')
            out.append(f'<rect x="{cx}" y="{cy}" width="5" height="{cardh}" rx="2.5" fill="{color}"/>')
            out.append(f'<rect x="{cx + 18}" y="{cy + 22}" width="44" height="44" rx="12" fill="{color}"/>')
            out.append(icon_at(icon, cx + 18 + 10, cy + 22 + 10, 24, "#FFFFFF"))
            out.append(f'<text x="{cx + 76}" y="{cy + 30}" font-size="14" font-weight="700" fill="#161D2E">{name}</text>')
            for li, line in enumerate(lines):
                out.append(f'<text x="{cx + 76}" y="{cy + 50 + li * 15}" font-size="11.5" fill="#5B6478">{line}</text>')
            out.append(f'<circle cx="{cx + cw - 20}" cy="{cy + 20}" r="11" fill="{tint}"/>')
            out.append(f'<text x="{cx + cw - 20}" y="{cy + 24.2}" text-anchor="middle" font-size="11" font-weight="700" fill="{color}">{n}</text>')
            if si < len(steps) - 1:
                mx = cx + cw / 2
                out.append(f'<path d="M{mx - 5},{cy + cardh + 3} L{mx},{cy + cardh + 9} L{mx + 5},{cy + cardh + 3}" stroke="{color}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>')
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------- risk
TIERS = [
    ("LOW", "#059669", "#E6F6F0", "circle-check", ["ping_device", "check_http", "check_database"],
     ["Runs immediately", "when the role allows it"]),
    ("MEDIUM", "#D97706", "#FEF3E2", "eye", ["search_logs", "query_incident_history"],
     ["Runs when the role allows", "it and the context is valid"]),
    ("HIGH", "#EA580C", "#FFF1E8", "triangle-alert", ["restart_database", "clear_cache"],
     ["Always needs an explicit", "approval record"]),
    ("CRITICAL", "#DC2626", "#FDECEC", "octagon-alert", ["delete_database", "shutdown_server"],
     ["Approval, elevated role", "and extra verification"]),
]


def build_risk() -> str:
    W, H, colw, gap, pad = 1200, 330, 264, 32, 24
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
           '<defs><filter id="sh" x="-5%" y="-5%" width="110%" height="120%"><feDropShadow dx="0" dy="1.5" stdDeviation="2" flood-color="#0F1524" flood-opacity="0.10"/></filter></defs>',
           f'<rect width="{W}" height="{H}" rx="18" fill="#F7F8FA"/>']
    for i, (name, color, tint, icon, tools, rule) in enumerate(TIERS):
        x = pad + i * (colw + gap)
        out.append(f'<rect x="{x}" y="24" width="{colw}" height="{H - 48}" rx="14" fill="#fff" filter="url(#sh)"/>')
        out.append(f'<rect x="{x}" y="24" width="{colw}" height="62" rx="14" fill="{color}"/>')
        out.append(f'<rect x="{x}" y="60" width="{colw}" height="26" fill="{color}"/>')
        out.append(icon_at(icon, x + 20, 42, 26, "#FFFFFF"))
        out.append(f'<text x="{x + 56}" y="62" font-size="17" font-weight="800" fill="#fff" letter-spacing="0.6">{name}</text>')
        if i < len(TIERS) - 1:
            ax = x + colw + gap / 2
            out.append(f'<path d="M{ax - 6},{55} L{ax + 6},{55} M{ax + 1},{49} L{ax + 7},{55} L{ax + 1},{61}" stroke="#94A3B8" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        out.append(f'<text x="{x + 20}" y="116" font-size="10.5" font-weight="700" fill="#8A93A6" letter-spacing="0.8">EXAMPLE TOOLS</text>')
        for ti, t in enumerate(tools):
            out.append(f'<rect x="{x + 20}" y="{126 + ti * 26}" width="{len(t) * 7.4 + 18}" height="21" rx="10.5" fill="{tint}"/>')
            out.append(f'<text x="{x + 29}" y="{140.5 + ti * 26}" font-size="11.5" font-family="ui-monospace, Menlo, Consolas, monospace" fill="{color}" font-weight="600">{t}</text>')
        out.append(f'<text x="{x + 20}" y="{H - 74}" font-size="10.5" font-weight="700" fill="#8A93A6" letter-spacing="0.8">RULE</text>')
        for li, line in enumerate(rule):
            out.append(f'<text x="{x + 20}" y="{H - 56 + li * 16}" font-size="12.5" fill="#161D2E" font-weight="500">{line}</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    (OUT / "img" / "pipeline.svg").write_text(build_pipeline())
    (OUT / "img" / "risk.svg").write_text(build_risk())
    palette = {
        "shield-check": "#059669", "route": "#3452E1", "boxes": "#3452E1", "key-round": "#D97706",
        "user-cog": "#7C3AED", "users": "#7C3AED", "scroll-text": "#059669", "book-open": "#3452E1",
        "flask-conical": "#EA580C", "shield-alert": "#DC2626", "layout-grid": "#3452E1",
        "triangle-alert": "#EA580C", "badge-check": "#059669", "terminal": "#3452E1", "rocket": "#7C3AED",
        "brain-circuit": "#7C3AED", "database": "#3452E1", "cpu": "#EA580C", "server-cog": "#EA580C",
        "lock-keyhole": "#7C3AED", "gauge": "#D97706", "clipboard-list": "#059669", "settings-2": "#64748B",
        "folder-clock": "#3452E1", "play": "#059669", "radar": "#3452E1", "message-square-text": "#059669",
    }
    for n, c in palette.items():
        write_icon(n, c)
    print("built", len(palette), "icons and 2 diagrams")
