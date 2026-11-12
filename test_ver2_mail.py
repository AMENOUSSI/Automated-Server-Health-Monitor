import unittest

from ver2_mail import Partition, build_message, parse_df

DF_OUTPUT = """\
 Size  Used Avail Use% Mounted on
  20G  6.1G   13G  32% /
 5.0G  135M  4.9G   3% /home
 5.0G  509M  4.5G  10% /boot
 1.9G     0  1.9G   0% /dev/shm
  10G  9.1G  900M  92% /mnt/backup disk
"""

CONFIG = {
    "email": {
        "from": "monitor@example.com",
        "to": ["admin@example.com"],
        "subject": "Rapport Utilisation Disque - srv01",
    },
    "alert": {"threshold_percent": 80},
}


class ParseDfTest(unittest.TestCase):
    def test_keeps_configured_mountpoints_in_order(self):
        rows = parse_df(DF_OUTPUT, ["/home", "/boot"])
        self.assertEqual([r.mount for r in rows], ["/home", "/boot"])
        self.assertEqual(rows[0], Partition("/home", "5.0G", "135M", "4.9G", 3))

    def test_mountpoint_with_spaces(self):
        rows = parse_df(DF_OUTPUT, ["/mnt/backup disk"])
        self.assertEqual(rows[0].percent, 92)

    def test_falls_back_to_root(self):
        self.assertEqual([r.mount for r in parse_df(DF_OUTPUT, ["/missing"])], ["/"])

    def test_host_root_prefix_is_removed(self):
        output = " Size  Used Avail Use% Mounted on\n 20G 6G 13G 32% /host\n 5G 1G 4G 20% /host/home\n 1G 0 1G 0% /etc/hosts\n"
        rows = parse_df(output, ["/", "/home", "/etc/hosts"], host_root="/host")
        self.assertEqual([r.mount for r in rows], ["/", "/home"])


class BuildMessageTest(unittest.TestCase):
    def test_no_alert_below_threshold(self):
        msg = build_message(CONFIG, parse_df(DF_OUTPUT, ["/", "/home"]))
        self.assertEqual(msg["Subject"], "Rapport Utilisation Disque - srv01")
        self.assertNotIn("Seuil", msg.get_body(("html",)).get_content())

    def test_alert_above_threshold(self):
        msg = build_message(CONFIG, parse_df(DF_OUTPUT, ["/", "/mnt/backup disk"]))
        self.assertTrue(msg["Subject"].startswith("[ALERTE] "))
        self.assertIn("ALERTE", msg.get_body(("plain",)).get_content())

    def test_logo_is_inline(self):
        msg = build_message(CONFIG, parse_df(DF_OUTPUT, ["/"]), logo=b"\x89PNG fake")
        html_part = msg.get_payload()[1]
        self.assertEqual(html_part.get_content_type(), "multipart/related")
        self.assertEqual(list(msg.iter_attachments()), [])


if __name__ == "__main__":
    unittest.main()
