import json
import logging
import subprocess
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

# =============================
# Chargement configuration
# =============================
with open("df_h_mail.json") as f:
    config = json.load(f)

# =============================
# Logging
# =============================
logging.basicConfig(
        filename=config["logging"]["file"],
        level=getattr(logging, config["logging"]["level"]),
        format="%(asctime)s %(levelname)s %(message)s"
        )

logging.info("Script démarré")

# =============================
# Exécution df -h
# =============================
try:
    resultat = subprocess.check_output(["df", "-h"], universal_newlines=True)
    logging.info("df -h exécuté avec succès")
except Exception as e:
    logging.error("Erreur df -h : %s", e)
    raise

lignes = resultat.strip().split("\n")
entrees = []

for ligne in lignes[1:]:
    cols = ligne.split()
    if cols[-1] in config["filesystem"]["mountpoints"]:
        entrees.append(cols)

if not entrees:
    for ligne in lignes[1:]:
        cols = ligne.split()
        if cols[-1] == "/":
            entrees.append(cols)
            break
# =============================
# HTML table
# =============================
rows = ""
for c in entrees:
    rows += f"""
    <tr style="text-align:center;">
        <td>{c[5]}</td>
        <td>{c[0]}</td>
        <td>{c[1]}</td>
        <td>{c[2]}</td>
        <td>{c[3]}</td>
        <td>{c[4]}</td>
    </tr>
    """

table_html = f"""
<table border="1" width="800" align="center" cellpadding="8" cellspacing="0">
<tr style="background-color:#0a1f44;color:white;text-align:center;">
<th>Mounted</th><th>Filesystem</th><th>Size</th><th>Used</th><th>Avail</th><th>Use%</th>
</tr>
{rows}
</table>
"""
# =============================
# Email
# =============================
msg = EmailMessage()
msg["Subject"] = config["email"]["subject"]
msg["From"] = config["email"]["from"]
msg["To"] = ", ".join(config["email"]["to"])


logo_cid = make_msgid()[1:-1]


msg.add_alternative(f"""
<html>
<body>
<h2 style="text-align:center" >Disk Usage Report</h2>
<!-- HEADER -->
<table width="800" align="center" cellpadding="0" cellspacing="0"
       style="background-color:#1f4fd8;border-radius:10px 10px 0 0;">
       <tr>
       <td style="padding:20px;text-align:center;">
           <img src="cid:{logo_cid}" width="180" alt="SMART 2D Services"
                    style="display:block;margin:auto;">
                        <p style="color:white;font-size:16px;margin-top:10px;">
                                Les contenus des répertoires
<span style="background:black;padding:6px;border-radius:4px;font-weight:bold;">/root</span>
                                                et
                                                        <span style="background:black;padding:6px;border-radius:4px;font-weight:bold;">/var</span>
                                                                (df -h)
                                                                    </p>
                                                                    </td>
                                                                    </tr>
                                                                    </table>
{table_html}
<p style="font-size:10px;color:gray;text-align:center;">
Rapport généré automatiquement — Smart2D
</p>
</body>
</html>
""", subtype="html")

logo_path = Path(config["email"]["logo_path"])
if logo_path.exists():
    with open(logo_path, "rb") as img:
        msg.add_attachment(
                img.read(),
                maintype="image",
                subtype="png",
 filename="logo.png",
                cid=logo_cid
                )

        # =============================
# SMTP
# =============================
try:
    context = (
            ssl._create_unverified_context()
            if not config["smtp"]["verify_tls"]
            else ssl.create_default_context()
            )

    with smtplib.SMTP(config["smtp"]["host"], config["smtp"]["port"]) as server:
        server.ehlo()
        if config["smtp"]["use_starttls"]:
            server.starttls(context=context)
            server.ehlo()
        server.send_message(msg)

    logging.info("Email envoyé avec succès")

except Exception as e:
    logging.error("Erreur SMTP : %s", e)
    raise