# Changelog

## Unreleased

- Add a pure Terrane template package with public namespace `streaky/template`,
  strict lookup, conditionals, loops, includes, widgets, and trusted filesystem roots.
- Generate native Terrane render functions at build time from explicit entries and
  their literal include closure; default to compiled lookup with engine/per-call dynamic
  overrides. Expose reusable `parse-template`/`parsed-template`/`render-parsed` for
  interpreted source; includes follow the selected mode in both paths.
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
