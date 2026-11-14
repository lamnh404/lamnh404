#!/usr/bin/env python3
"""Render the neofetch-style profile cards (dark + light SVG).

Stats come from the GitHub GraphQL API when GITHUB_TOKEN is set; otherwise the
last values found in the existing SVG are kept, so a local run never wipes them.
Stdlib only, so the workflow needs no dependency install.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USER = "lamnh404"
BIRTHDAY = dt.date(2005, 4, 4)
ROOT = Path(__file__).resolve().parent.parent
LINE_WIDTH = 64

ASCII = r"""
                  o
          o       |       o
           \    .-+-.    /
            \ .'  |  '. /
             X    |    X
            / \   |   / \
      o----+---\--+--/---+----o
           |    '(@)'    |
      o----+---/--+--\---+----o
            \ /   |   \ /
             X    |    X
            / '.  |  .' \
           /    '-+-'    \
          o       |       o
                  o

           k8s :: aws :: iac
""".strip("\n").split("\n")

THEMES = {
    "dark": {"bg": "#161b22", "text": "#c9d1d9", "key": "#ffa657",
             "value": "#a5d6ff", "dim": "#616e7f", "ok": "#3fb950"},
    "light": {"bg": "#f6f8fa", "text": "#24292f", "key": "#953800",
              "value": "#0a3069", "dim": "#8c959f", "ok": "#1a7f37"},
}


def uptime(today: dt.date) -> str:
    years = today.year - BIRTHDAY.year
    months = today.month - BIRTHDAY.month
    days = today.day - BIRTHDAY.day
    if days < 0:
        months -= 1
        prev_month_end = today.replace(day=1) - dt.timedelta(days=1)
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, first: 100, privacy: PUBLIC) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch_stats(token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    u = payload["data"]["user"]
    cc = u["contributionsCollection"]
    return {
        "repos": u["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "commits": cc["totalCommitContributions"],
        "contribs": cc["contributionCalendar"]["totalContributions"],
    }


def previous_stats() -> dict:
    svg = ROOT / "dark_mode.svg"
    if not svg.exists():
        return {}
    found = re.findall(r'<tspan id="(\w+)"[^>]*>([^<]*)</tspan>', svg.read_text())
    return dict(found)


def build_lines(stats: dict, today: dt.date) -> list:
    """Each line is a list of (style, text) segments."""
    def kv(key, value, stat_id=None):
        dots = LINE_WIDTH - len(key) - len(str(value)) - 4
        return [("key", key), ("text", ":"), ("dim", " " + "." * max(dots, 1) + " "),
                ("value", str(value), stat_id)]

    def pair(k1, id1, k2, id2):
        v1, v2 = str(stats.get(id1, "-")), str(stats.get(id2, "-"))
        right = f"{k2}: {v2}"
        dots = LINE_WIDTH - len(k1) - len(v1) - len(right) - 9
        return [("key", k1), ("text", ":"), ("dim", " " + "." * max(dots, 1) + " "),
                ("value", v1, id1), ("dim", "  |  "), ("key", k2), ("text", ": "),
                ("value", v2, id2)]

    def header(title):
        return [("text", f"- {title} " + "-" * (LINE_WIDTH - len(title) - 3))]

    s = lambda k: stats.get(k, "-")
    return [
        [("key", "lamnh404"), ("text", "@"), ("key", "github")],
        [("text", "-" * LINE_WIDTH)],
        kv("Role", "DevOps Engineer @ Stack Tech"),
        kv("Education", "HCMUT - Computer Science (Honors)"),
        kv("Uptime", uptime(today)),
        kv("Location", "Ho Chi Minh City, Vietnam"),
        kv("Goal", "Site Reliability / Platform Engineer"),
        [],
        kv("Cloud", "AWS (EKS, VPC, IAM, S3, ALB), OpenStack"),
        kv("IaC", "Terraform, Terragrunt, Ansible, Helm"),
        kv("Delivery", "GitLab CI, GitHub Actions, Argo CD, Rollouts"),
        kv("Scaling", "Karpenter, HPA, KEDA"),
        kv("Observability", "Prometheus, Grafana, Loki, Mimir, Tempo"),
        kv("Security", "Trivy, Gitleaks, Checkov, Kyverno, ESO"),
        kv("Languages", "Bash, Python, Java"),
        [],
        header("Certifications"),
        kv("AWS Solutions Architect - Associate", "986 / 1000"),
        kv("Certified Kubernetes Administrator", "in progress"),
        [],
        header("Contact"),
        kv("Email", "lamcaonhat0404@gmail.com"),
        kv("LinkedIn", "Cao Nhat Lam"),
        [],
        header("GitHub Stats"),
        pair("Repos", "repos", "Stars", "stars"),
        pair("Commits (1y)", "commits", "Followers", "followers"),
        kv("Contributions (1y)", s("contribs"), "contribs"),
    ]


def render(theme: dict, lines: list) -> str:
    font, lh = 16, 20
    left_x, right_x, top = 15, 390, 30
    height = top + max(len(lines), len(ASCII)) * lh + 10
    width = right_x + int(LINE_WIDTH * font * 0.6) + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,'
        f"'Courier New',monospace\" width=\"{width}\" height=\"{height}\" font-size=\"{font}px\">",
        "<style>"
        f".key{{fill:{theme['key']}}}.value{{fill:{theme['value']}}}"
        f".dim{{fill:{theme['dim']}}}.text{{fill:{theme['text']}}}"
        "text,tspan{white-space:pre}</style>",
        f'<rect width="{width}" height="{height}" fill="{theme["bg"]}" rx="15"/>',
        f'<text x="{left_x}" y="{top}" fill="{theme["text"]}">',
    ]
    for i, row in enumerate(ASCII):
        out.append(f'<tspan x="{left_x}" y="{top + i * lh}">{escape(row)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{right_x}" y="{top}" fill="{theme["text"]}">')
    for i, segs in enumerate(lines):
        if not segs:
            continue
        parts = []
        for seg in segs:
            style, text = seg[0], escape(str(seg[1]))
            stat_id = seg[2] if len(seg) > 2 else None
            id_attr = f' id="{stat_id}"' if stat_id else ""
            parts.append(f'<tspan class="{style}"{id_attr}>{text}</tspan>')
        out.append(f'<tspan x="{right_x}" y="{top + i * lh}">{"".join(parts)}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    stats = previous_stats()
    if token:
        try:
            stats = fetch_stats(token)
        except Exception as exc:  # keep last known values rather than failing the card
            print(f"warning: stats fetch failed, keeping previous values: {exc}", file=sys.stderr)
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
    lines = build_lines(stats, today)
    for name, theme in THEMES.items():
        (ROOT / f"{name}_mode.svg").write_text(render(theme, lines))
    print(f"rendered cards: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
