# Story 14: PyPI + npm Publish

**Batch:** 9 | **Dependencies:** Story 13

## Description
Publish both SDKs to their respective registries. Set up GitHub Actions for CI and future releases.

## Acceptance Criteria

1. `pip install lore-sdk` installs from PyPI successfully
2. `npm install lore-sdk` installs from npm successfully
3. Both packages have correct metadata (description, author, license, homepage, repo URL)
4. GitHub Actions CI runs tests on push (Python: 3.9, 3.11, 3.12; Node: 18, 20)
5. Version is `0.1.0` for both packages
6. LICENSE file (MIT) present in both packages
7. `.gitignore` is clean — no build artifacts in repo
8. `pip install lore-sdk` total download < 50MB (excluding model)

## Technical Notes
- PyPI: use `python -m build` + `twine upload`
- npm: `npm publish` with `prepublishOnly` script running build
- GitHub Actions: two workflows (python-ci.yml, ts-ci.yml) or one matrix workflow
- Test PyPI first before real PyPI
