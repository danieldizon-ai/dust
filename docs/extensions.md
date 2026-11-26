# Confession extensions: stacking a church's confession on top

The Nicene boundary is a minimum. A denomination, network, school or church may add its own
confession as a further layer, under its own name, without changing the default for anyone
else. Dust supports this with extension files.

```python
from dust import Layer
layer = Layer(extensions=["chalcedon-451"])          # bundled example
layer = Layer(extensions=["/path/to/our-statement.json"])
```

```bash
dust check --extension chalcedon-451 "Christ was two separate persons."
```

## Rules

* An extension can only **add** propositions, errors, rules, latitude topics and patterns.
  It cannot remove or redefine a Nicene proposition (loading fails if it tries).
* An extension is never loaded by default.
* Say in the extension's `note` exactly what it excludes and what it deliberately does not.

## Format

```json
{
  "id": "our-church-2027",
  "title": "...",
  "attribution": "...",
  "note": "What this adds and what it deliberately leaves open.",
  "propositions": [{"id": "X01", "group": "...", "severity": "core|ecclesial", "text": "...",
                    "greek": "", "literals": ["predicate(ENTITY)"], "scripture": ["John 1:14"]}],
  "excluded_errors": [{"id": "XE01", "name": "...", "summary": "...", "contradicts": ["X01"], "condemned": "..."}],
  "rules": [{"id": "XR01", "if": "a(SON)", "then": ["-b(SON)"], "why": "..."}],
  "error_signatures": {"XE01": ["a(SON)"]},
  "latitude": [],
  "patterns": [{"literal": "a(SON)", "regex": "\\bSON is ...\\b"}]
}
```

Patterns run on normalised text: lower case, with the persons of the Trinity replaced by
`SON`, `FATHER`, `SPIRIT`, `GOD` and `TRINITY` (see `dust.symbolic.normalise`). A pattern
literal starting with `-` asserts a negation. Use ids that cannot clash with the Nicene
`P`, `E`, `R` and `L` series. Scripture references outside the bundled verses are allowed;
the system prompt simply omits their text.

## The bundled example: Ephesus (431) and Chalcedon (451)

`chalcedon-451` adds three propositions (Christ is one person; his humanity is not absorbed;
Mary is Theotokos) and excludes Nestorianism and Eutychianism. It does **not** exclude the
Miaphysite formula "one incarnate nature of God the Word", which the Oriental Orthodox
churches confess and themselves distinguish from Eutychianism. That is the kind of care an
extension needs: Chalcedonian churches can opt in without the layer declaring the Oriental
Orthodox outside it. Tests in `tests/test_v02.py` cover both.
