# Changelog

## Unreleased

- Add a pure Terrane template engine with configurable interpolation escaping, strict value lookup, loops, includes, widgets, and trusted filesystem search roots.
- Add package documentation and a runnable demo.
- Select autoescaping by filename following Jinja's recommended policy: HTML/HTM/XML on, other files off, and strings on by default. Add forced on/off and string-default configuration; includes select by their own filename and explicit `escape` remains effective when autoescaping is off.
