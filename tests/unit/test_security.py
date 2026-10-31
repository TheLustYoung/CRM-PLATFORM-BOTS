import socket
import unittest
from unittest.mock import patch
from backend.services.security import normalize_url, public_addresses, safe_filename, is_public_ip, DomainError
from backend.services.limits import Policy
from backend.api.schemas import Upload, SelectFormat
from pydantic import ValidationError


class URLSecurityTests(unittest.TestCase):
    def test_rejects_dangerous_schemes_and_authorities(self):
        for url in ["file:///etc/passwd", "ftp://example.com/a", "http://user:pass@example.com", "http://localhost/", "http://example.com:8080", "https://example.com\\@127.0.0.1", "https://example.com/\nX", "http://[::1]/", "http://127.0.0.1", "http://169.254.169.254/latest/meta-data", "http://10.0.0.1/", "http://224.0.0.1/"]:
            with self.subTest(url=url), self.assertRaises(DomainError):
                normalize_url(url, resolve=False)

    def test_normalizes_public_url(self):
        self.assertEqual(normalize_url("https://EXAMPLE.com/video?id=2#fragment", False), "https://example.com/video?id=2")

    def test_blocks_mixed_public_private_dns_answers(self):
        answers = [(socket.AF_INET, 1, 6, "", ("8.8.8.8", 443)), (socket.AF_INET, 1, 6, "", ("127.0.0.1", 443))]
        with patch("socket.getaddrinfo", return_value=answers), self.assertRaises(DomainError):
            public_addresses("public.example", 443)

    def test_rechecks_dns_on_every_request(self):
        public = [(socket.AF_INET, 1, 6, "", ("8.8.8.8", 443))]
        private = [(socket.AF_INET, 1, 6, "", ("192.168.1.1", 443))]
        with patch("socket.getaddrinfo", side_effect=[public, private]):
            self.assertEqual(public_addresses("rebind.example", 443), ["8.8.8.8"])
            with self.assertRaises(DomainError):
                public_addresses("rebind.example", 443)

    def test_obfuscated_loopback_uses_dns_result(self):
        answers = [(socket.AF_INET, 1, 6, "", ("127.0.0.1", 80))]
        with patch("socket.getaddrinfo", return_value=answers), self.assertRaises(DomainError):
            normalize_url("http://2130706433/")

    def test_nonpublic_ipv6(self):
        for address in ["::1", "::", "fc00::1", "fe80::1", "ff02::1", "::ffff:127.0.0.1", "100.64.0.1", "0.0.0.0"]:
            with self.subTest(address=address):
                self.assertFalse(is_public_ip(address))

    def test_dns_errors_are_safe(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("provider details")):
            with self.assertRaisesRegex(DomainError, "^invalid_url$"):
                normalize_url("https://unknown.example")


class FileAndPolicyTests(unittest.TestCase):
    def test_filename_cannot_escape_directory(self):
        for value in ["../../secret.pdf", "C:\\Users\\x\\report.pdf", "/etc/passwd", "../..", "x\r\nContent-Type: text/html"]:
            name = safe_filename(value)
            self.assertNotIn("/", name)
            self.assertNotIn("\\", name)
            self.assertNotIn("\r", name)
            self.assertNotIn("\n", name)
            self.assertTrue(name)

    def test_file_name_length(self):
        self.assertLessEqual(len(safe_filename("a" * 500)), 180)

    def test_policy_rejects_unsafe_limits(self):
        for values in [{"retention_days": 0}, {"max_upload_bytes": 20_000_000}, {"daily_jobs": 0}, {"enabled_platforms": ["unknown"]}]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                Policy(**values)

    def test_callback_index_and_uuid_validation(self):
        with self.assertRaises(ValidationError):
            SelectFormat(user_id=1, metadata_id="../other", index=-1)

    def test_file_size_must_be_positive(self):
        with self.assertRaises(ValidationError):
            Upload(user_id=1, request_key="m1", file_id="1", name="a.pdf", size=0)


if __name__ == "__main__":
    unittest.main()
