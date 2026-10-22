"""Behavioral checks for the native template consumer protocol."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
TERRANE = Path(os.environ.get('TERRANE', PACKAGE.parents[1] / 'target/debug/terrane')).resolve()
REQUEST = json.dumps({'format': 1, 'declarations': []})


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

    def test_malformed_entry_reports_name_and_utf8_byte_offset(self):
        with tempfile.TemporaryDirectory() as cwd:
            Path(cwd, 'entry.html').write_text('é{% if not %}')
            response = self.invoke(['--namespace', 'generated/test', '--root', '.',
                                    '--template', 'entry.html'], cwd)
            message = response['diagnostics'][0]['message']
            self.assertIn('entry.html at byte 2', message)
            self.assertIn('invalid if condition', message)
            self.assertEqual(response['generated_sources'], [])

    def test_missing_include_reports_parent_and_include_offset(self):
        with tempfile.TemporaryDirectory() as cwd:
            Path(cwd, 'entry.html').write_text('é{% include "missing.html" %}')
            response = self.invoke(['--namespace', 'generated/test', '--root', '.',
                                    '--template', 'entry.html'], cwd)
            message = response['diagnostics'][0]['message']
            self.assertIn('missing.html', message)
            self.assertIn('included by template entry.html at byte 2', message)
            self.assertEqual(response['generated_sources'], [])

    def test_malformed_include_retains_child_and_parent_locations(self):
        with tempfile.TemporaryDirectory() as cwd:
            Path(cwd, 'entry.html').write_text('é{% include "child.html" %}')
            Path(cwd, 'child.html').write_text('éé{{ bad + expression }}')
            response = self.invoke(['--namespace', 'generated/test', '--root', '.',
                                    '--template', 'entry.html'], cwd)
            message = response['diagnostics'][0]['message']
            self.assertIn('child.html at byte 4', message)
            self.assertIn('included by template entry.html at byte 2', message)
            self.assertEqual(response['generated_sources'], [])

    def test_literal_and_condition_only_units_compile_and_render(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / 'src').mkdir()
            (app / 'templates').mkdir()
            literal = "template-lookup|bool-value|empty-value|é é|'\\\n\r\tend"
            (app / 'templates/literal.txt').write_bytes(literal.encode('utf-8'))
            (app / 'templates/condition.txt').write_text('{% if "a|b" %}q{% endif %}{% if true %}t{% endif %}{% if none %}bad{% endif %}')
            manifest = f'''package = "consumer-regression"
artifact = "executable"
[namespaces]
consumer-regression = "src"
[profile]
capabilities = ["filesystem"]
[terrane-dependencies.streaky.template]
path = {json.dumps(os.path.relpath(PACKAGE, app))}
'''
            for name in ('literal', 'condition'):
                args = ['--namespace', f'generated/regression/{name}', '--root',
                        'templates', '--template', f'{name}.txt']
                manifest += f'\n[consumers.{name}]\ntool = "streaky/template::template"\nargs = {json.dumps(args)}\ndeclarations = ["/consumer-regression::main"]\n'
            (app / 'package.toml').write_text(manifest)
            (app / 'src/main.trn').write_text('''namespace consumer-regression
from /generated/regression/literal import make-template-engine as create-literal
from /generated/regression/condition import make-template-engine as create-condition
function main;
    engine = create-literal;
    print; (engine.fetch; 'literal.txt')
    engine = create-condition;
    print; (engine.fetch; 'condition.txt')
''')
            def render():
                built = subprocess.run([str(TERRANE), 'build', str(app)], text=True,
                                       capture_output=True, timeout=120)
                self.assertEqual(built.returncode, 0, built.stderr)
                self.assertNotIn('warning', built.stderr.lower())
                with tempfile.TemporaryDirectory() as cwd:
                    result = subprocess.run([built.stdout.strip()], cwd=cwd,
                                            capture_output=True, timeout=20, check=True)
                return result.stdout

            self.assertEqual(render(), (literal + '\nqt\n').encode('utf-8'))
            state = app / '.trn/consumer-state/build/literal/source.json'
            unchanged = state.stat().st_ino
            self.assertEqual(render(), (literal + '\nqt\n').encode('utf-8'))
            self.assertEqual(state.stat().st_ino, unchanged)
            (app / 'templates/literal.txt').write_text("{% include 'partial.txt' %}")
            (app / 'templates/partial.txt').write_text('first')
            self.assertEqual(render(), b'first\nqt\n')
            (app / 'templates/partial.txt').write_text('second')
            self.assertEqual(render(), b'second\nqt\n')


if __name__ == '__main__':
    unittest.main()
