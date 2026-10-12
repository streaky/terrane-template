# Changelog

## Unreleased

- Add a pure Terrane template engine with configurable interpolation escaping, strict value lookup, loops, includes, widgets, and trusted filesystem search roots.
- Add package documentation and a runnable demo.
- Select autoescaping by filename following Jinja's recommended policy: HTML/HTM/XML on, other files off, and strings on by default. Add forced on/off and string-default configuration; includes select by their own filename and explicit `escape` remains effective when autoescaping is off.
- Rename the package to `template` with manifest identity and public namespace `streaky/template`; migrate the demo, tests, and documentation without old-namespace aliases.

- Replace the old compiled-token names with `parse-template`, `parsed-template`, and
  `render-parsed`; parsed tokens are reusable interpreted representation, distinct from
  ahead-of-time generation.
- Add a native Terrane build consumer for ahead-of-time rendering from explicit template entries and their literal include closure. Every engine defaults to compiled mode and supports per-engine and per-call dynamic overrides; generated render functions contain native control flow rather than a token interpreter.
- Preserve literal Unicode/control bytes across generated and dynamic modes, and distinguish actual NUL characters from digits in template path validation.
- Add an equal-work native benchmark for compiled/dynamic CPU and bounded allocation comparisons using Terrane's built-in profiler.
