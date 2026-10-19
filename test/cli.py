#!/usr/bin/env python3
"""CLI filesystem-boundary regressions; requires nixfmt on PATH."""

from pathlib import Path
import subprocess
import tempfile
import unittest


class DirectoryLinksTest(unittest.TestCase):
    def test_directory_links_are_not_traversed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, outside = root / 'repo', root / 'outside'
            repo.mkdir()
            outside.mkdir()
            source = '{x=1;}\n'
            (repo / 'local.nix').write_text(source)
            (outside / 'private.nix').write_text(source)
            (repo / 'escape').symlink_to(outside, target_is_directory=True)
            (repo / 'cycle').symlink_to(repo, target_is_directory=True)
            subprocess.run(['nixfmt', str(repo)], check=True, capture_output=True, timeout=10)
            self.assertEqual((outside / 'private.nix').read_text(), source)
            self.assertNotEqual((repo / 'local.nix').read_text(), source)

    def test_explicit_file_symlink_following_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, link = Path(tmp) / 'target.nix', Path(tmp) / 'link.nix'
            target.write_text('{x=1;}\n')
            link.symlink_to(target)
            subprocess.run(['nixfmt', '--follow-symlinks', str(link)],
                           check=True, capture_output=True, timeout=10)
            self.assertTrue(link.is_symlink())
            self.assertEqual(target.read_text(), '{ x = 1; }\n')


if __name__ == '__main__':
    unittest.main()
