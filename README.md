# template

A small, pure Terrane template engine with ahead-of-time Terrane source generation and an optional runtime parser. It supports interpolation, conditionals, list loops, includes, and registered widgets; it is not a full Jinja implementation.

## Build and run the demo

From `packages/template` in the compiler checkout:

```sh
sh build-consumer.sh
../../target/debug/terrane run demo
```

The helper builds a native Terrane consumer and installs it under the ignored `.trn/consumers/` directory. The demo's configured templates become ordinary Terrane functions before compilation; the resulting binary renders them without reading the template files.

## Configure an application

For an application beside this package, use:

```toml
[terrane-dependencies]
template = { path = "../template" }

[profile]
capabilities = ["filesystem"]

[consumers.template]
command = "../template/.trn/consumers/template"
args = ["--namespace", "generated/template/my-app", "--root", "templates", "--template", "page.html"]
declarations = ["/my-app::main"]
```

Adjust the paths and namespace for the application. Consumer commands and template roots are resolved from the consuming package's directory. Terrane requires a nonempty declaration selection; the application's canonical `main` is a convenient selection anchor, and the template consumer does not require annotations on it.

Repeat `--root` for search roots (later roots win), and `--template` for entry templates. Only those entries and their recursively discovered literal includes are compiled. Roots are **not** scanned indiscriminately: unrelated files remain runtime-only. Malformed templates, invalid names, and missing includes diagnose during the build. Include cycles can be compiled; rendering rejects excessive include/control nesting at depth 64.

The configured namespace exports a factory:

```terrane
from /generated/template/my-app import make-template-engine
from /streaky/template import text-value

engine = make-template-engine;
engine.assign; 'title', (text-value; 'A page')
html = engine.fetch; 'page.html'
```

The generated functions contain literal output, direct root/field lookups, and native Terrane `if`/`while` control flow—not a stored token stream or a runtime expression parser. The factory registers those functions and the runtime search roots in an independent engine. Rebuild the application after changing an ahead-of-time template; the consumer executable only needs rebuilding when its implementation changes.

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

`render(source)` always parses runtime source, regardless of the fetch mode. For reusable interpreted data, `parse-template(source, name='')` returns a `parsed-template`, and `render-parsed` renders it against current assignments. This avoids reparsing that supplied source but is **not** ahead-of-time compilation or an automatic file cache.

## Values and escaping

Import values and the engine from `/streaky/template`. Use `assign`, `assign-complex`, `append`, and `assigned` for instance-local data; `register-widget` accepts callbacks. `fetch` returns text; `display` prints it with a trailing newline. See `docs/src/manual.yaml` for the complete API and syntax reference.

Both modes follow Jinja's recommended autoescape selection: `.html`, `.htm`, and `.xml` names enable escaping case-insensitively, other files disable it, and string templates enable it by default. `set-autoescape(true|false)` forces a policy, `select-autoescape()` restores filename selection, and `set-string-autoescape` controls the unnamed-template default. Rendering uses the engine's current policy, not a setting frozen at build time.

`|safe` bypasses escaping; `|escape` forces HTML escaping even in dynamic/plain-text templates or when autoescaping is off. HTML escaping replaces `&`, `<`, `>`, `"`, and `'`; it is not JavaScript, CSS, or URL-context escaping. Widgets and includes are inserted verbatim, so a text include inside an HTML page is not escaped by its parent. Widget callbacks must escape untrusted data for their output context.

## Safety and limits

Template source and search roots are trusted. The engine does not sandbox template authors. Files are bounded to 1 MiB and strict UTF-8; relative names reject NUL, absolute paths, backslashes, colons, empty components, `.` and `..`. Search roots may contain symlinks and are not a filesystem sandbox. Runtime `add-path` changes dynamic search precedence, not the already-generated inventory. Assignments, widgets, and escaping settings remain mutable in either mode.

## Profile both rendering paths

`benchmarks/render` is an equal-work native workload: each iteration renders an
interpolated page and a nested-loop/include page, then reports an output checksum.
It accepts `compiled` or `dynamic`; the optional `short` argument uses 20 iterations
instead of 100,000 for allocation captures.

From `packages/template`, with the native consumer built and the profiling collectors
available:

```sh
terrane=../../target/debug/terrane
for mode in compiled dynamic; do
  "$terrane" profile record --cpu --embed-sources --retain-arguments \
    -o ".trn/profile-$mode-cpu.trnprof" benchmarks/render -- "$mode"
  "$terrane" profile record --allocations --embed-sources --retain-arguments \
    -o ".trn/profile-$mode-allocations.trnprof" benchmarks/render -- "$mode" short
done
"$terrane" profile show .trn/profile-compiled-allocations.trnprof \
  --compare .trn/profile-dynamic-allocations.trnprof --limit 10
```

Keep CPU and allocation evidence separate: allocation collection is instrumented.
Compare matching iteration counts and output checksums, and inspect partial/dropped
evidence before interpreting totals. The short workload avoids the current allocation
event bound for this benchmark. CPU attribution may be unavailable even when aggregate
capture timing and native allocation stacks are useful. Captures are ignored build
artifacts under `.trn/`; retain them for subsequent inspection.

## Verify

From `packages/template`:

```sh
sh build-consumer.sh
../../target/debug/terrane test --argument "$PWD/tests/fixtures" .
../../target/debug/terrane test --argument "$PWD/tests/compiled/templates" tests/compiled
```

The arguments provide read-only fixture roots because Terrane runs tests in isolated working directories. Runtime-write cases write only in those directories. The second suite exercises real generated render functions against the dynamic implementation.

The short package/dependency name is `template`; its manifest identity and public namespace are `streaky/template`.
