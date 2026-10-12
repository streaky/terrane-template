# template

A small, pure Terrane template engine for rendering trusted templates with explicitly supplied values. It supports interpolation, conditionals, list loops, includes, and registered widgets; it is not a full Jinja implementation.

## Run the demo

From `demo/`, run `terrane run .`. The demo loads real HTML files from `templates/`
and prints the rendered page.

## Use the package

Declare the sibling package and filesystem capability in the consuming package manifest:

```toml
[terrane-dependencies]
template = { path = "../template" }

[profile]
capabilities = ["filesystem"]
```

Import the public API from `/streaky/template`. Create an `instance template-engine;`, assign values with `assign` or `assign-complex`, register template search directories with `add-path`, and render source with `render` or a file with `fetch`. `render-compiled` accepts a `compiled-template` returned by `compile-template`; compile once to reuse parsed templates. `display` fetches and prints with a trailing newline; `fetch` returns the rendered string without printing. See the reference manual in `docs/src/manual.yaml`.

The short package name is `template`; its manifest identity is `streaky/template`,
matching its namespace as required for a Terrane library.

## Safety and limits

The default follows Jinja's recommended filename-based selection: `.html`, `.htm`,
and `.xml` templates autoescape (case-insensitively); other file names do not.
String templates autoescape by default. Includes select their own policy by file
name, rather than inheriting the parent's escaping mode.

Use `engine.set-autoescape; true` or `engine.set-autoescape; false` to override
selection for every template. `engine.select-autoescape;` restores filename
selection. `engine.set-string-autoescape; false` changes only the unnamed/string
default, leaving file selection unchanged.

Templates are trusted code: authors control literal output and may invoke widgets.
HTML escaping replaces `&`, `<`, `>`, `"`, and `'`; `|safe` bypasses it and `|escape`
always applies it, including in plain-text templates or with autoescaping disabled.
This is HTML escaping only, not JavaScript, CSS, or URL-context escaping.
Widget output is inserted verbatim; handlers must escape untrusted values for
their output context. A plain-text include in an HTML page is also inserted
verbatim, so use an HTML template or explicit escaping when that output needs it.

The engine does not sandbox template authors. Template files are limited to 1 MiB and must be valid UTF-8. Search roots use the package filesystem capability and are trusted directories; resolved symlinks are not separately sandboxed, so do not put untrusted paths or files in a root. Appended roots are searched newest-first; `add-path` with `push=false` prepends a lower-priority root. No automatic render cache is provided. Includes and nested control flow are limited to 64 levels.

## Verify the package

From `packages/template`, run:

```sh
terrane test --argument "$PWD/tests/fixtures" .
```

Terrane runs each test in a fresh working directory. The argument supplies the
read-only fixture root; tests that write invalid/oversized inputs do so in their
isolated working directories.
