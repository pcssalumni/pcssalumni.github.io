"""Offline regression checks for the reported injection and recovery boundary."""
import tempfile
import unittest
import urllib.request
from pathlib import Path
from recovery_http import RestrictedRedirect, validate_url, open_recovery
from secure_site import audit_tree, safe_reference


class SecurityTests(unittest.TestCase):
    def test_public_urls(self):
        for value in ('https://www.pcssalumni.com/', '//urshort.live/ad', 'javascript:alert(1)',
                      'java\nscript:alert(1)', '/sydvgas.php', '/sydvgas%2ephp', 'https://pcssalumni.com:443/PDF/x.pdf'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe_reference(value)
        safe_reference('https://web.archive.org/web/20220505212957/https://pcssalumni.com/')

    def test_redirect_destinations(self):
        handler = RestrictedRedirect('wordpress')
        request = urllib.request.Request('https://www.pcssalumni.com/wp-json/wp/v2/pages')
        for target in ('https://urshort.live/ads', 'http://www.pcssalumni.com/wp-json/wp/v2/pages',
                       'https://www.pcssalumni.com/sydvgas.php', 'https://www.pcssalumni.com/wp-content/uploads/../sydvgas.php'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, 'Found', {}, target)
        redirected = handler.redirect_request(request, None, 302, 'Found', {}, 'https://pcssalumni.com/wp-json/wp/v2/pages')
        self.assertEqual(redirected.host, 'pcssalumni.com')
        with self.assertRaises(ValueError):
            open_recovery('https://urshort.live/ads', scope='wordpress', timeout=1)
        validate_url('https://web.archive.org/web/20220505212957id_/http://pcssalumni.com/PDF/YB-1930.pdf', 'wayback')
        with self.assertRaises(ValueError):
            validate_url('https://www.pcssalumni.com/PDF/x.pdf', 'wayback')

    def test_publication_rejects_injection(self):
        attacks = [
            '<meta http-equiv="refresh" content="0;url=https://example.org">',
            '<script>location.replace("https://example.org")</script>',
            '<script id="quarto-html-after-body">location.replace("https://example.org")</script>',
            '<script src="https://example.org/ad.js"></script>',
            '<script src="assets/unreviewed.js"></script>',
            '<img src="x.png" onerror="alert(1)">',
            '<a href="jav&#x61;script:alert(1)">link</a>',
            '<iframe srcdoc="ads"></iframe>',
            '<base href="https://example.org/">',
            '<?php echo "injection"; ?>',
            '<!-- sydvgas.php -->',
            '<script src="site_libs/unreviewed.js"></script>',
        ]
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            page = site / 'index.html'
            for attack in attacks:
                page.write_text('<html><head></head><body>' + attack + '</body></html>', encoding='utf-8')
                with self.subTest(attack=attack), self.assertRaises(ValueError):
                    audit_tree(site, write_csp=True)

    def test_csp_and_nested_php(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            page = site / 'index.html'
            page.write_text('<html><head></head><body><script src="assets/site.js"></script></body></html>', encoding='utf-8')
            with self.assertRaises(ValueError):
                audit_tree(site)
            self.assertEqual(audit_tree(site, write_csp=True), 1)
            self.assertEqual(audit_tree(site), 1)
            self.assertIn("object-src &#x27;none&#x27;", page.read_text())
            nested = site / 'assets' / 'sydvgas.php'
            nested.parent.mkdir()
            nested.write_text('malware')
            with self.assertRaises(ValueError):
                audit_tree(site)


if __name__ == '__main__':
    unittest.main()
