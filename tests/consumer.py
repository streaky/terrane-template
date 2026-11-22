"""Behavioral checks for the native template consumer protocol."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from contextlib import contextmanager

PACKAGE = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / 'consumer-fixtures'
WORKSPACE = PACKAGE / '.trn' / 'consumer-regression'
TERRANE = Path(os.environ.get('TERRANE', shutil.which('terrane') or PACKAGE.parents[1] / 'target/debug/terrane')).resolve()
REQUEST = json.dumps({'format': 1, 'declarations': []})


@contextmanager
def stable_workspace_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run([str(TERRANE), 'build', 'consumer/package.toml'],
                                cwd=PACKAGE, check=True, stdout=subprocess.PIPE, text=True)
        cls.consumer = Path(result.stdout.strip())

    def invoke(self, args, cwd):
        result = subprocess.run([str(self.consumer), *args], input=REQUEST, text=True,
                                capture_output=True, cwd=cwd, timeout=20, check=True)
        return json.loads(result.stdout)

    def test_cli_rejects_missing_duplicate_and_unknown_options(self):
        cases = [([], '--namespace'),
                 (['--namespace', 'generated/test'], '--root'),
                 (['--namespace', 'generated/test', '--root', '.'], '--template'),
                 (['--namespace', 'generated/test', '--namespace', 'generated/again'], '--namespace'),
                 (['--unknown'], '--unknown'), (['--root'], '--root'),
                 (['--namespace', 'generated/test', '--runtime-root', ''], '--runtime-root')]
        with tempfile.TemporaryDirectory() as cwd:
            for args, option in cases:
                with self.subTest(args=args):
                    response = self.invoke(args, cwd)
                    self.assertEqual(response['generated_sources'], [])
                    self.assertIn(option, response['diagnostics'][0]['message'])

    def test_malformed_static_inputs_report_locations(self):
        cases = [
            ('malformed-entry', ('entry.html at byte 2', 'invalid if condition')),
            ('missing-include', ('missing.html', 'included by template entry.html at byte 2')),
            ('malformed-include', ('child.html at byte 4', 'included by template entry.html at byte 2')),
        ]
        for fixture, expected in cases:
            with self.subTest(fixture=fixture):
                response = self.invoke(
                    ['--namespace', 'generated/test', '--root', '.',
                     '--template', 'entry.html'], FIXTURES / fixture)
                message = response['diagnostics'][0]['message']
                for fragment in expected:
                    self.assertIn(fragment, message)
                self.assertEqual(response['generated_sources'], [])

    def test_transitive_include_only_invalidation(self):
        source = FIXTURES / 'invalidation'
        with stable_workspace_lock(PACKAGE / '.trn' / 'consumer-regression.lock'):
            for relative in ('package.toml', 'src/main.trn', 'templates/literal.txt',
                             'templates/partial.txt'):
                path = source / relative
                destination = WORKSPACE / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                content = path.read_bytes()
                if not destination.exists() or destination.read_bytes() != content:
                    destination.write_bytes(content)

            def render():
                built = subprocess.run([str(TERRANE), 'build', str(WORKSPACE)],
                                       text=True, capture_output=True, timeout=120)
                self.assertEqual(built.returncode, 0, built.stderr)
                self.assertNotIn('warning', built.stderr.lower())
                with tempfile.TemporaryDirectory() as cwd:
                    result = subprocess.run([built.stdout.strip()], cwd=cwd,
                                            capture_output=True, timeout=20, check=True)
                return result.stdout

            self.assertEqual(render(), b'first\n')
            state = WORKSPACE / '.trn/consumer-state/build/literal/source.json'
            unchanged = state.stat().st_ino
            self.assertEqual(render(), b'first\n')
            self.assertEqual(state.stat().st_ino, unchanged)

            partial = WORKSPACE / 'templates/partial.txt'
            try:
                partial.write_bytes(b'second')
                self.assertEqual(render(), b'second\n')
            finally:
                partial.write_bytes((source / 'templates/partial.txt').read_bytes())


if __name__ == '__main__':
    unittest.main()
