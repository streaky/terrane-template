"""Behavioral checks for the built native template consumer (build-consumer.sh first)."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
CONSUMER = PACKAGE / '.trn/consumers/template'
REQUEST = json.dumps({'format': 1, 'declarations': []})


class ConsumerTests(unittest.TestCase):
    def invoke(self, args, cwd):
        result = subprocess.run([str(CONSUMER), *args], input=REQUEST, text=True,
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
        compiler = Path(os.environ.get('TERRANE', str(PACKAGE.parents[1] / 'target/debug/terrane'))).resolve()
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / 'src').mkdir()
            (app / 'templates').mkdir()
            literal = "template-lookup|bool-value|empty-value|é é|'\\\n\r\tend"
            (app / 'templates/literal.txt').write_text(literal)
            (app / 'templates/condition.txt').write_text('{% if "a|b" %}q{% endif %}{% if true %}t{% endif %}{% if none %}bad{% endif %}')
            manifest = f'''package = "consumer-regression"
artifact = "executable"
[namespaces]
consumer-regression = "src"
[profile]
capabilities = ["filesystem"]
[terrane-dependencies]
template = {{ path = {json.dumps(os.path.relpath(PACKAGE, app))} }}
'''
            for name in ('literal', 'condition'):
                args = ['--namespace', f'generated/regression/{name}', '--root',
                        'templates', '--template', f'{name}.txt']
                manifest += f'\n[consumers.{name}]\ncommand = {json.dumps(str(CONSUMER))}\nargs = {json.dumps(args)}\ndeclarations = ["/consumer-regression::main"]\n'
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
            built = subprocess.run([str(compiler), 'build', str(app)], text=True,
                                   capture_output=True, timeout=120)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertNotIn('warning', built.stderr.lower())
            with tempfile.TemporaryDirectory() as cwd:
                result = subprocess.run([built.stdout.strip()], cwd=cwd,
                                        capture_output=True, timeout=20, check=True)
            self.assertEqual(result.stdout, (literal + '\nqt\n').encode())


if __name__ == '__main__':
    unittest.main()
