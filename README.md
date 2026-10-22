# template

A small, pure Terrane template engine with ahead-of-time Terrane source generation and an optional runtime parser. It supports interpolation, conditionals, list loops, includes, and registered widgets; it is not a full Jinja implementation.

## Build and run the demo

From `packages/template` in the compiler checkout:

```sh
../../target/debug/terrane run demo
```

The library exports its native generator through `consumer-tools`; Terrane builds and
refreshes that tool as needed. The demo's configured templates become ordinary Terrane
functions before compilation; the resulting binary renders them without reading the template files.

## Configure an application

For an application beside this package, use:

```toml
[terrane-dependencies.streaky.template]
path = "../template"

[profile]
capabilities = ["filesystem"]

[consumers.template]
tool = "streaky/template::template"
args = ["--namespace", "generated/template/my-app", "--root", "templates", "--runtime-root", "templates", "--template", "page.html"]
declarations = ["/my-app::main"]
```

Adjust the namespace for the application. Build roots (`--root`) resolve from the consuming package's directory and are not embedded in the factory. Optional, repeatable `--runtime-root` values configure separate runtime search paths; relative runtime roots resolve from the process working directory. With no runtime roots supplied, configure dynamic loading with `engine.add-path` in the application. Terrane requires a nonempty declaration selection; the application's canonical `main` is a convenient selection anchor, and the template consumer does not require annotations on it.

Repeat `--root` for search roots (later roots win), and `--template` for entry templates. Only those entries and their recursively discovered literal includes are compiled. Roots are **not** scanned indiscriminately: unrelated files remain runtime-only. Malformed templates, invalid names, and missing includes diagnose during the build. Include cycles can be compiled; rendering rejects excessive include/control nesting at depth 64.

The configured namespace exports a factory:

```terrane
from /generated/template/my-app import make-template-engine
from /streaky/template import text-value

engine = make-template-engine;
engine.assign; 'title', (text-value; 'A page')
html = engine.fetch; 'page.html'
```

The generated functions contain literal output, direct root/field lookups, and native Terrane `if`/`while` control flow—not a stored token stream or a runtime expression parser. The factory registers those functions and only explicitly supplied runtime roots in an independent engine. Normal application builds keep the consumer executable current. The consumer resolves entries and recursive includes, reuses generated source when its arguments and loaded template contents are unchanged, and regenerates when those inputs change. It does not invalidate generation for unrelated caller metadata.

## Compiled and dynamic modes

Every engine defaults to `compiled`. A directly constructed `instance template-engine;` has no compiled inventory until renderers are registered; normally use the generated factory above.

```terrane
html = engine.fetch; 'page.html'              # compiled
preview = engine.fetch; 'page.html', 'dynamic' # reread and parse this call
engine.set-mode; 'dynamic'                    # runtime parsing by default
html = engine.fetch; 'page.html', 'compiled'  # compiled override for this call
engine.set-mode; 'compiled'
```

`fetch(name, mode='default')` and `display(name, mode='default')` accept `default`, `compiled`, or `dynamic`. The default inherits the engine setting; an override does not change it. Includes follow the selected mode and retain their own filename's escaping policy. Compiled lookup never silently falls back to disk. Use dynamic mode for files created, changed, or selected only at runtime; each dynamic fetch rereads them.

`render(source)` always parses runtime source, regardless of the fetch mode; its includes follow the engine's current mode. For reusable interpreted data, `parse-template(source, name='')` returns a `parsed-template`, and `render-parsed` renders it against current assignments with the same include policy. This avoids reparsing that supplied source but is **not** ahead-of-time compilation or an automatic file cache. Public parsed-program rendering and generation validate syntax and complete control-block structure before use.

## Values and escaping

Import values and the engine from `/streaky/template`. Use `assign`, `assign-complex`, `append`, and `assigned` for instance-local data; `register-widget` accepts callbacks. `fetch` returns text; `display` prints it with a trailing newline. See `docs/src/manual.yaml` for the complete API and syntax reference.

`template-value.to-string;` returns its raw display text: text unchanged, booleans as
`true`/`false`, and the empty template value as `''`. String `+`, `.concat;`, `.join;`,
and `print;` share that representation. Lists, objects, and unknown kinds raise
`template-error`. Raw display is deliberately separate from HTML escaping; template
interpolation applies the policy and filters below after conversion.

Both modes follow Jinja's recommended autoescape selection: `.html`, `.htm`, and `.xml` names enable escaping case-insensitively, other files disable it, and string templates enable it by default. `set-autoescape(true|false)` forces a policy, `select-autoescape()` restores filename selection, and `set-string-autoescape` controls the unnamed-template default. Rendering uses the engine's current policy, not a setting frozen at build time.

`|safe` bypasses escaping; `|escape` forces HTML escaping even in dynamic/plain-text templates or when autoescaping is off. HTML escaping replaces `&`, `<`, `>`, `"`, and `'` in one pass over the original text, without rescanning inserted entities; existing entities are still escaped (`&amp;` becomes `&amp;amp;`). It is not JavaScript, CSS, or URL-context escaping. Widgets and includes are inserted verbatim, so a text include inside an HTML page is not escaped by its parent. Widget callbacks must escape untrusted data for their output context.

## Safety and limits

Template source and search roots are trusted. The engine does not sandbox template authors. Files are bounded to 1 MiB and strict UTF-8; relative names reject NUL, absolute paths, backslashes, colons, empty components, `.` and `..`. Search roots may contain symlinks and are not a filesystem sandbox. Runtime `add-path` changes dynamic search precedence, not the already-generated inventory. Assignments, widgets, and escaping settings remain mutable in either mode.

Parser/structural failures identify the template and zero-based UTF-8 byte offset. Build-time include failures also identify the first including template and its include offset. Widget callbacks may declare `throws throwable` (or a narrower compatible bound); errors propagate in both modes.

## Profile both rendering paths

`benchmarks/render` is an equal-work native workload: each iteration renders an
interpolated page and a nested-loop/include page, then reports an output checksum.
It accepts `compiled` or `dynamic`; the optional `short` argument uses 20 iterations
instead of 100,000 for allocation captures.

From `packages/template/benchmarks/render`, with the native consumer built and the
profiling collectors available (the benchmark's relative runtime roots require this cwd):

```sh
terrane=../../../../target/debug/terrane
for mode in compiled dynamic; do
  "$terrane" profile record --cpu --embed-sources --retain-arguments \
    -o "../../.trn/profile-$mode-cpu.trnprof" . -- "$mode"
  "$terrane" profile record --allocations --embed-sources --retain-arguments \
    -o "../../.trn/profile-$mode-allocations.trnprof" . -- "$mode" short
done
"$terrane" profile show ../../.trn/profile-compiled-allocations.trnprof \
  --compare ../../.trn/profile-dynamic-allocations.trnprof --limit 10
```

Keep CPU and allocation evidence separate: allocation collection is instrumented.
Compare matching iteration counts and output checksums, and inspect partial/dropped
evidence before interpreting totals. The short workload avoids the current allocation
event bound for this benchmark. CPU attribution may be unavailable even when aggregate
capture timing and native allocation stacks are useful. Captures are ignored build
artifacts under `.trn/`; retain them for subsequent inspection.

Ahead-of-time rendering removes runtime parsing, not all allocation. Context maps use
copy-on-write storage: read-only fetches share backing storage, but adding iterator and
`loop` bindings copies the map's entries to preserve outer scope. Large contexts in
item-dependent loops therefore still have context-size-dependent costs. Generated empty
and literal-only bodies skip creating a loop context.

## Verify

From `packages/template`:

```sh
../../target/debug/terrane test --argument "$PWD/tests/fixtures" .
../../target/debug/terrane test --argument "$PWD/tests/compiled/templates" tests/compiled
python tests/consumer.py
```

The arguments provide read-only fixture roots because Terrane runs tests in isolated working directories. Runtime-write cases write only in those directories. The second suite exercises real generated render functions against the dynamic implementation.

The short package/dependency name is `template`; its manifest identity and public namespace are `streaky/template`.
