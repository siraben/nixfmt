#!/usr/bin/env python3
"""Regression tests for the sandbox-to-host import boundary (no Nix needed)."""

from pathlib import Path
import subprocess
import tempfile
import unittest

IMPORTER = Path(__file__).resolve().parents[1] / 'scripts/import-formatted.sh'


class ImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.baseline, self.formatted, self.dest = [self.root / x for x in ('base', 'out', 'repo')]
        for tree in (self.baseline, self.formatted, self.dest):
            (tree / 'sub').mkdir(parents=True)
            (tree / 'sub/file.nix').write_text('{x=1;}\n')
        (self.formatted / 'sub/file.nix').write_text('{ x = 1; }\n')

    def run_import(self, formatted=None):
        subprocess.run(['bash', str(IMPORTER), str(self.baseline),
                        str(formatted or self.formatted), str(self.dest)], check=True, capture_output=True)

    def assert_rejected(self, formatted=None):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_import(formatted)

    def test_only_allowed_contents_are_imported(self):
        subprocess.run(['git', 'init', '-q', str(self.dest)], check=True)
        config = (self.dest / '.git/config').read_bytes()
        hook = self.formatted / '.git/hooks/pre-commit'
        hook.parent.mkdir(parents=True)
        hook.write_text('#!/bin/sh\ntouch ../HOST_EXECUTED\n')
        hook.chmod(0o755)
        (self.formatted / '.git/config').write_text('[core]\n hooksPath = /malicious\n')
        (self.formatted / '.gitattributes').write_text('*.nix filter=evil\n')
        (self.formatted / 'extra.nix').write_text('malicious new path')
        target = self.dest / 'sub/file.nix'
        target.chmod(0o640)
        self.run_import()
        self.assertEqual(target.read_text(), '{ x = 1; }\n')
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.dest / '.git/config').read_bytes(), config)
        self.assertFalse((self.dest / 'extra.nix').exists())
        self.assertFalse((self.dest / '.gitattributes').exists())
        subprocess.run(['git', '-C', str(self.dest), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', 'commit',
                        '--allow-empty', '-m', 'test'], check=True, capture_output=True)
        self.assertFalse((self.root / 'HOST_EXECUTED').exists())

    def test_file_symlink_rejected(self):
        target = self.formatted / 'sub/file.nix'
        target.unlink()
        target.symlink_to(self.baseline / 'sub/file.nix')
        self.assert_rejected()

    def test_directory_symlink_rejected(self):
        (self.formatted / 'sub/file.nix').unlink()
        (self.formatted / 'sub').rmdir()
        (self.formatted / 'sub').symlink_to(self.baseline / 'sub', target_is_directory=True)
        self.assert_rejected()

    def test_output_root_symlink_rejected(self):
        link = self.root / 'link'
        link.symlink_to(self.formatted, target_is_directory=True)
        self.assert_rejected(link)

    def test_special_file_rejected(self):
        import os
        target = self.formatted / 'sub/file.nix'
        target.unlink()
        os.mkfifo(target)
        self.assert_rejected()


if __name__ == '__main__':
    unittest.main()
