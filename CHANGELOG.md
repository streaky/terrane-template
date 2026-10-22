# Changelog

## Unreleased

- Migrate build-time template generation from staged `command` executables to
  `tool = "streaky/template::template"` with canonical
  `[terrane-dependencies.streaky.template]` dependencies. Terrane builds the exported
  tool automatically; remove calls to the deleted `build-consumer.sh`.
- Reuse generated source when consumer arguments and loaded template inputs are
  unchanged. Rebuilding the application after entry/include edits regenerates the
  affected compiled templates through ordinary consumer preparation.
- Keep compiler diagnostics visible when consumer protocol test setup cannot build
  the generator, while capturing the reported executable path from stdout.
- Give `template-value` a standard `to-string` representation shared by interpolation,
  string concatenation, printing, `.concat`, and `.join`, preserving strict container
  rejection and keeping raw conversion separate from escaping.
- Use string `+` for renderer/source composition and ordered `switch` for value,
  directive, validation, and token dispatch without changing template syntax.
- Use multi-search replacement for one-pass HTML escaping, source-literal quoting,
  and directive whitespace normalization; never rescan inserted escape sequences.
- Add a pure Terrane template package with public namespace `streaky/template`,
  strict lookup, conditionals, loops, includes, widgets, and trusted filesystem roots.
- Generate native Terrane render functions at build time from explicit entries and
  their literal include closure; default to compiled lookup with engine/per-call dynamic
  overrides. Expose reusable `parse-template`/`parsed-template`/`render-parsed` for
  interpreted source; includes follow the selected mode in both paths.
  Complete-unit generation rejects duplicate program names rather than silently overwriting
  registrations.
- Select autoescaping by filename: HTML/HTM/XML on, other files off, strings on.
  Support forced on/off, a string default, and explicit `safe`/`escape` filters.
- Preserve literal Unicode/control bytes and strictly validate file names, UTF-8,
  file size, parsed-program syntax/structure, and include/control depth.
- Diagnose template failures with names and UTF-8 byte offsets, including build-time
  include provenance. Keep internal helpers private and document generator support.
- Separate build roots from optional cwd-relative `--runtime-root` configuration.
  Generate only required imports and skip unused loop contexts in empty/literal bodies.
- Accept negation separated by tabs/newlines and quoted pipes in conditions; reserve
  `loop` as an iterator name, diagnose unknown value kinds, and support throwing widgets.
- Add package documentation, a runnable demo, behavioral/consumer regressions, and an
  equal-work native benchmark for CPU and bounded allocation profiling.
