# Contributing

Issues and pull requests are welcome. This is a small project, so the bar is
simple: keep each change focused on one thing, and say why in the description.

## Getting set up

```sh
pip install -e .
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Before opening a pull request

- Run the tests: `PYTHONPATH=src python -m unittest discover -s tests -v`
- The code targets Python 3.9 and up, and CI runs 3.9 and 3.12. Avoid syntax
  newer than 3.9.
- Do not weaken the safety model described in the README without saying so
  plainly. A sync that writes when it should have skipped is the worst bug this
  tool can have, so any new write path needs a test that proves the skip.

Please open an issue first for anything that changes behaviour or widens scope,
so the approach can be agreed before you spend time on it. Issues labelled
`good first issue` are self contained and a good place to start.
