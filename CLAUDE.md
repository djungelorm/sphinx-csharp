# CLAUDE.md

## Overview

sphinx-csharp is a Sphinx extension that adds a `cs` domain for C# APIs. You enable it with `extensions = ['sphinx_csharp']` in `conf.py`, and it supports a subset of C#.

The `cs` directives are written by hand, or generated from Doxygen XML by [Breathe](https://github.com/breathe-doc/breathe).

- Breathe imports `sphinx_csharp.csharp` and subclasses its directives, such as `CSharpNamespacePlain`. Keep that module and those class names.
- Supported: Python 3.11 and later, Sphinx 7.2 and later.
- Tested: Python 3.11 to 3.15, each Sphinx minor version from 7.2 to 9.1, Breathe 4.35, 4.36, 5.0 and 5.1, and Doxygen 1.15.0 and 1.9.8 (Ubuntu 24.04).

## Commands

```bash
hatch run lint:check                         # ruff, and dotnet build on the Breathe sources
hatch run types:check                        # mypy in strict mode on sphinx_csharp
hatch run matrix:all                         # pytest with coverage in every test environment, in parallel
hatch run matrix:all --python 3.14           # every test environment for one Python
hatch run test.py3.14-9.1-5.1:all -k parse   # selected tests in one environment
hatch run test.py3.14-9.1-5.1:corpus         # the corpus test
hatch run docs:build                         # the docs in nitpicky mode, into docs/_build/html
hatch run docs:serve                         # serve the docs, and rebuild them on each change
hatch run package:check                      # build dist/, check it with twine, and build with the wheel
```

## Tests

The tests use pytest. Any warning fails them, except the deprecation warnings that Breathe raises.

- `test_parse.py`: table-driven tests of the `parse_*_signature` functions.
- `test_render.py`: builds small projects with Sphinx's test fixtures, and checks signature text and cross-reference targets.
- `test_extrefs.py`, `test_intersphinx.py`: external links and intersphinx lookups.
- `test_projects.py`: builds `tests/roots/test-basic` and `tests/roots/test-breathe` in nitpicky mode. It also builds the basic project with the text, LaTeX, man and singlehtml builders, and the Breathe project in parallel.
- `test_corpus.py`: builds large C# libraries through Doxygen and Breathe. pytest skips it unless you pass `-m corpus`.

Snapshots:

- Each test project compares the ids and text of every signature with its `signatures.txt`. A rendering change updates those files in the same commit, with `pytest tests/test_projects.py --update-snapshots`.
- The Breathe snapshot must match Doxygen 1.15.0 and 1.9.8. Keep a C# construct that the two describe differently out of `tests/roots/test-breathe/cs`.
- Breathe 4 writes a `set` accessor for every property, and the test allows for it.
- `test-breathe` is skipped without `doxygen` on the PATH. `lint:check` compiles its sources with `dotnet build`, with `stubs/Unity.cs` for the Unity types.

Known bugs have tests marked `xfail`, with `xfail_strict` on. A fix fails the run until you remove the marker.

A new feature needs:

1. Parser cases in `tests/test_parse.py`.
2. Rendering checks in `tests/test_render.py`.
3. A directive in `tests/roots/test-basic/index.rst`, and its signatures in the snapshot.
4. Documentation in `docs/`, when the feature is user-facing.

## Architecture

| Module | Contents |
| --- | --- |
| `__init__.py` | `setup()`: registers the domain, the config values and the event handlers. Declares parallel read and write safety. |
| `config.py` | The `sphinx_csharp_*` config values, and the old names that forks used. |
| `lexer.py` | `tokenize`: splits a signature into words, literals and punctuation, each with its span. |
| `parser.py` | `Parser` and the `parse_*_signature` functions. |
| `render.py` | `TypeRenderer` and the signature node helpers. |
| `csharp.py` | The directives, `CSharpXRefRole` and `CSharpDomain`. |
| `extrefs.py`, `extrefs_data.py` | Links to external documentation, such as the Microsoft .NET docs. |
| `debug.py` | `CSDebug`: the `parse`, `xref` and `external` debug log categories. |
| `static/` | The stylesheet for `sphinx_csharp_compact_layout`. |

### Parsing

- `Parser` is a recursive descent parser over the tokens, with a method for each production, such as `type`, `param` and `method`.
- A production raises `ParseError` on a mismatch. A method with alternatives resets `pos` and tries the next.
- Results are slices of the signature, so they keep the spacing that Doxygen writes.
- Default values, attribute arguments and expression bodies are skipped as balanced spans.
- Doxygen quirks have productions of their own: `templates` for the `template<...>` prefix, `misplaced_nullable`, and `name_part` for arity names such as `Box-1-g`.
- On a failed parse, a `parse_*_signature` function logs a warning and raises the `ValueError` from `invalid_signature`. Sphinx catches it in `handle_signature` and shows the signature as written.

### Directives and Scoping

- `CSharpObject`, an `ObjectDescription`, is the base of every object directive. Each subclass implements `handle_signature`, which builds the signature nodes and returns the fully qualified name.
- `TypeRenderer.append_type` emits a `pending_xref` for each type, recursing into generic arguments, and writes built-in types as plain text. It stores the arity on the node as `cs:arity`.
- `env.ref_context['cs:parent']` holds the current namespace or type, and `get_fullname` prefixes names with it.
- `.. cs:namespace::` sets the parent, and `.. cs:namespace:: None` clears it. `namespace-push` and `namespace-pop` keep a stack in `cs:namespaces`.
- `cs:namespace` holds the current namespace for the TOC entries.
- A directive with content makes its name the parent in `before_content`, and restores the old parent in `after_content`. It also adds its generic parameters to `cs:generic_names`, which stay unlinked.

### Domain Data

- `domaindata['cs']['objects']` is keyed by `(objtype, fullname)`. Node ids are `objtype + '-' + fullname`.
- Methods, indexers and delegates also get an overload id with their parameter types, such as `function-N.C.M(ref-int,string)`.
- `add_object` keeps every description of an object. `objects` holds the one in the first document by name, and `duplicates` the others, so `clear_doc` can restore one.
- `merge_domaindata` merges the objects from parallel reads.

### Reference Resolution

`CSharpXRefRole` stores the current parent on the reference node. A reference then resolves in this order:

1. `CSharpDomain.find_objects` matches local names that end with the target. It prefers the target qualified by the closest enclosing namespace, then any match inside that namespace.
2. A target with parameters links to the overload id. A target with generic arguments, such as `Box<T>.Put`, matches names without the arguments when nothing else matches.
3. `ExternalRefs.get_external_ref` looks the type up in `external_type_map`, and builds a URL from `external_search_pages`. Built-in keywords such as `int` map to their `System` types through `builtin_types`. Any other `System` type links to the Microsoft docs, with an arity suffix such as `List-1`.
4. `CSharpDomain.missing_reference` runs before intersphinx, and looks a generic target up with its arity.

An unresolved reference returns `None`, so Sphinx reports it in nitpicky mode only.

Roles: `object_types` maps object types to roles, so `:cs:type:` finds classes, structs, interfaces and enums. `:cs:obj:` searches every object type, and `resolve_any_xref` serves `:any:`. `ignore_xref_types` lists the strings that are never linked, such as `void`.

`apply_config` merges the user's config values with copies of the `ExternalRefsData` defaults on every build.

## Conventions

- Use `_()` from `sphinx.locale` for translatable strings.
- Annotate every function in `sphinx_csharp`, which ships `py.typed`. The ruff and mypy settings are in `pyproject.toml`.
- Every warning has `type='cs'` and a subtype, such as `duplicate` or `parse`, so `suppress_warnings` can silence it. List a new subtype in the docs.
- Keep the old config names working. `RENAMED` and `DEBUG_FLAGS` in `config.py` map them to the new names, and `apply_deprecated_names` copies them with a `cs.config` warning.
- A release bumps the version in `pyproject.toml` and adds an entry to `CHANGES.txt`.

## Writing

Applies to anything a person reads: commit messages, PR descriptions, code comments, docs.

General guidance:

 * Write concisely. When trimming, keep facts and trim the framing.
 * Keep descriptions high level. The code is the detail, and should be self-documenting.
 * One person writes it and many may read it. You, the writer, should do the compression.
 * Avoid emdashes. Use a comma or a hyphen instead.
 * Avoid AI tells: "emojis", greetings etc.
 * American English everywhere ("meters", "color", "normalized").
 * No "Authored by" / `Co-Authored-By` lines.

### Sentences

Average 14 words per sentence and under half a comma. Long comma-chained sentences are the main
way writing here goes wrong.

 * **One idea per sentence, two clauses at most.** A fact and its consequence make a sentence.
   Never chain with `, so ..., and ...` or `, which ..., so ...`.
 * **Say what a thing is, not what it is not.** Negate only to correct a misreading the reader is
   likely to arrive with, and only attached to a positive statement. "rather than", "no longer",
   "nothing" and "not a" are the tells.
 * **Name the thing.** No "the thing", "nothing", "whatever", "anything". The subject of a
   sentence is a definite noun.
 * **No anthropomorphism.** Sphinx, Breathe and the parser do not say, ask, see, hear or refuse,
   and are never finished with anything. State the mechanism.
 * **No setup and payoff, and no editorializing.** A sentence that only frames the next one is cut.
 * **Paragraphs run one to three sentences**, about 30 words. Past four it is two paragraphs, or a
   list.

### Documentation

 * **Lead with the example.** The unit of explanation is one or two sentences of setup ending in a
   colon, then the code, then any explanation of it. A section that explains a feature without
   showing it is the wrong shape.
 * **Address the reader** as "you". Do not write about an abstract "a user" or "a project".
 * Reuse the stock forms already in the docs.
 * Headings are short Title Case noun phrases, not clauses with verbs.
 * `.. note::` in block form with a one or two sentence body for a caveat, `.. seealso::` for a
   cross-reference. Never hang a paragraph off an inline `.. note::`.
 * Say what something does. Why it is implemented that way belongs in the code.

### Code comments

Comments carry the constraint the code itself cannot.

 * **Size the comment to the code it describes.** A line or two of code gets a fragment naming the
   step, a method a sentence, a file or a mechanism not recoverable from the code a paragraph. A
   paragraph over a one-line statement is the usual failure.
 * **The default form is a label**: a fragment above the lines it covers, sentence case, no
   trailing period. A long method is often a run of these.
 * **Comment the surprise**: a Sphinx or Doxygen quirk, a workaround, an ordering constraint, a unit, a sign
   convention. Code that reads plainly gets no comment, and never one that restates the line below.
 * **State the constraint, do not argue the alternative.** A comment that proves a case, or names
   what would break, is arguing.
 * **Never reference what a change replaced.** A comment explains the code as it stands, to someone
   who never saw the old version. How a value was arrived at belongs in the commit message and the
   PR, though a measurement that sizes a constant is part of what it means.
 * **Name the thing, and use "we".** Openers are "The ...", "Whether ..." and a verb, as in the
   docstrings. Do not nominalize to avoid the first person.
 * **Write what the code names.** ASCII only, and no symbol that appears nowhere in the source.
   `--` is an emdash by another spelling. American English, as everywhere else.
 * **One comment per place.** Do not clone a comment across sibling files with the noun swapped.
 * `# Note:` prefixes a one-sentence caveat attached to the line below. It is the only marker in
   use, and an open question is a GitHub issue.
 * Trailing comments are rare and short, and are not padded into aligned columns. Do not split a
   comment into paragraphs, or mark up `*emphasis*`.
 * The **Sentences** rules apply in full. Anthropomorphism is the one comments break most.

## Commits

 * One logical thing per commit.
 * Concise message, sized to the diff. Tiny commits just need a single-line summary, larger commits needs
   a single-line summary then short paragraph(s).

## Before pushing

Run the full suite locally before pushing a branch:

```bash
hatch run lint:check
hatch run types:check
hatch run matrix:all
```

Push only when all three pass.

- `matrix:all` runs the environments several at once, and writes a log for each to `test-output`.
- It needs `doxygen` on the PATH, or the Breathe tests skip. `lint:check` needs `dotnet`.
- Hatch fetches any Python it cannot find. If a Python version is unavailable, say so.

## Pull requests

 * Concise technical prose, proportional to the diff; bullets only for discrete items. Multi-part
   change → lead paragraphs with a short bold phrase (`**Root cause.**`, `**Fix.**`, `**Testing.**`).
 * State the problem, the change, and for a fix how it was verified.
 * Do not state that tests CI covers would pass (like `bazel test //:test`).
 * Do not repeat implementation details that are clear from the commit messages.
 * After drafting, cut: any sentence that restates the diff, the weaker of two sections that say the
   same thing, any paragraph over four lines. If it will not compress further, that is a sign the
   change is not understood well enough yet; re-read the diff rather than add words.
 * End with one or more `Fixes #NNN` when open issues are fixed by the PR; omit otherwise.
 * End with one or more `Related to #NNN` when open issues are related to but not fixed by the PR;
   omit otherwise.
 * **No AI-attribution or "Generated with" footer**, in PR bodies and commit messages alike.
 * One paragraph per line; GitHub renders single newlines literally. Reflow wrapped text.
