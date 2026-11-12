"""Disk usage report.

Runs `df`, keeps the mount points listed in the configuration and emails them
as an HTML table. Partitions above the alert threshold are highlighted and the
subject is prefixed with [ALERTE].
"""

import html
import json
import logging
import os
import smtplib
import socket
import ssl
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = Path(os.environ.get("MONITOR_CONFIG", BASE_DIR / "df_h_mail.json"))
# Set when running in Docker with the host filesystem mounted (e.g. -v /:/host:ro).
HOST_ROOT = os.environ.get("HOST_ROOT", "").rstrip("/")
DEFAULT_THRESHOLD = 80
TITLE = "Rapport Utilisation Disque"


@dataclass
class Partition:
    mount: str
    size: str
    used: str
    avail: str
    percent: int


def resolve(path: str) -> Path:
    """Relative paths in the configuration are relative to the script, not to the
    current directory, so the script also works when started by cron."""
    p = Path(path)
    return p if p.is_absolute() else BASE_DIR / p


def load_config(path: Path = CONFIG_FILE) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_df(output: str, mountpoints: list[str], host_root: str = "") -> list[Partition]:
    """Parse `df -h --output=size,used,avail,pcent,target`, in the configured order.

    The mount point is the last column, so it may contain spaces.
    """
    found: dict[str, Partition] = {}
    for line in output.strip().splitlines()[1:]:
        cols = line.split(maxsplit=4)
        if len(cols) < 5:
            continue
        size, used, avail, pcent, target = cols
        if host_root:
            if target != host_root and not target.startswith(host_root + "/"):
                continue
            target = target[len(host_root):] or "/"
        digits = pcent.rstrip("%")
        found[target] = Partition(target, size, used, avail, int(digits) if digits.isdigit() else 0)

    partitions = [found[m] for m in mountpoints if m in found]
    missing = [m for m in mountpoints if m not in found]
    if missing:
        logging.warning("Points de montage introuvables : %s", ", ".join(missing))
    if not partitions and "/" in found:
        logging.warning("Aucun point de montage configuré trouvé, rapport sur /")
        partitions = [found["/"]]
    return partitions


def read_disk_usage(mountpoints: list[str]) -> list[Partition]:
    output = subprocess.check_output(
        ["df", "-h", "--output=size,used,avail,pcent,target"], text=True
    )
    return parse_df(output, mountpoints, HOST_ROOT)


def build_message(config: dict, partitions: list[Partition], logo: bytes | None = None) -> EmailMessage:
    email = config["email"]
    threshold = config.get("alert", {}).get("threshold_percent", DEFAULT_THRESHOLD)
    alerts = [p for p in partitions if p.percent >= threshold]
    organization = email.get("organization", "")
    host = socket.gethostname()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    msg = EmailMessage()
    msg["Subject"] = ("[ALERTE] " if alerts else "") + email["subject"]
    msg["From"] = email["from"]
    msg["To"] = ", ".join(email["to"])

    # Plain-text version for mail clients that do not render HTML.
    lines = [f"{TITLE} - {host} - {now}", ""]
    lines += [
        f"{p.mount:<12} total {p.size:>6}  utilisé {p.used:>6}  dispo {p.avail:>6}  {p.percent}%"
        + ("  <-- ALERTE" if p in alerts else "")
        for p in partitions
    ]
    msg.set_content("\n".join(lines))

    e = html.escape
    cell = "padding:12px 14px;border-bottom:1px solid #e5e7eb;"
    logo_cid = make_msgid()
    logo_html = (
        f'<img src="cid:{logo_cid[1:-1]}" width="320" alt="{e(organization)}" '
        'style="display:block;margin:0 auto 16px;">'
        if logo
        else ""
    )
    alert_html = (
        '<p style="width:768px;margin:16px auto 0;padding:12px 16px;background:#fdecea;'
        'color:#a61b1b;border-radius:6px;font-weight:bold;">'
        f"⚠ Seuil de {threshold} % dépassé : {e(', '.join(p.mount for p in alerts))}</p>"
        if alerts
        else ""
    )
    rows = "".join(
        f'<tr style="{"background:#fdecea;color:#a61b1b;font-weight:bold;" if p in alerts else ""}">'
        f'<td style="{cell}">{e(p.mount)}</td>'
        f'<td style="{cell}">{e(p.size)}</td>'
        f'<td style="{cell}">{e(p.used)}</td>'
        f'<td style="{cell}">{e(p.avail)}</td>'
        f'<td style="{cell}">{p.percent}%</td>'
        "</tr>"
        for p in partitions
    )
    header = "".join(
        f'<th style="padding:14px;text-align:left;">{h}</th>'
        for h in ("PARTITION", "TOTAL", "UTILISÉ", "DISPO", "UTIL%")
    )
    footer = f"Rapport généré automatiquement sur {e(host)} le {now}" + (
        f" — {e(organization)}" if organization else ""
    )

    msg.add_alternative(
        f"""<html><body style="font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
<table width="800" align="center" cellpadding="0" cellspacing="0" style="background:#1f6fb8;border-radius:6px;">
<tr><td style="padding:40px 20px;text-align:center;">{logo_html}
<p style="margin:0;color:#ffffff;font-size:20px;font-weight:bold;">{TITLE}</p></td></tr>
</table>
{alert_html}
<table width="800" align="center" cellpadding="0" cellspacing="0" style="margin-top:28px;border-collapse:collapse;font-size:15px;">
<tr style="background:#0b2f63;color:#ffffff;">{header}</tr>
{rows}
</table>
<p style="font-size:11px;color:#6b7280;text-align:center;margin-top:24px;">{footer}</p>
</body></html>""",
        subtype="html",
    )
    if logo:
        # Inline image, displayed inside the HTML part rather than as an attachment.
        msg.get_payload()[1].add_related(logo, maintype="image", subtype="png", cid=logo_cid)
    return msg


def send(config: dict, msg: EmailMessage) -> None:
    smtp = config["smtp"]
    context = ssl.create_default_context()
    if not smtp.get("verify_tls", True):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP(smtp["host"], smtp["port"], timeout=30) as server:
        server.ehlo()
        if smtp.get("use_starttls", False):
            server.starttls(context=context)
            server.ehlo()
        if smtp.get("username"):
            server.login(smtp["username"], smtp["password"])
        server.send_message(msg)


def main() -> int:
    config = load_config()
    log = config.get("logging", {})
    logging.basicConfig(
        filename=resolve(log.get("file", "df_h_mail.log")),
        encoding="utf-8",
        level=getattr(logging, log.get("level", "INFO")),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.info("Script démarré")
    try:
        partitions = read_disk_usage(config["filesystem"]["mountpoints"])
        logo_path = config["email"].get("logo_path")
        logo = resolve(logo_path).read_bytes() if logo_path and resolve(logo_path).exists() else None
        msg = build_message(config, partitions, logo)
        send(config, msg)
    except Exception:
        logging.exception("Échec de l'envoi du rapport")
        return 1
    logging.info("Rapport envoyé : %s", msg["Subject"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
