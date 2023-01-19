# How to contribute to this project

![Docstrings](https://img.shields.io/badge/docstrings-google-lightgrey)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)
![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)
![Lint CI](https://github.com/aplietexe/udemy-autocoupons/actions/workflows/lint.yaml/badge.svg?style=for-the-badge)

Did you find a bug, or have a feature request?

- Ensure there isn't already a similar issue open by searching on GitHub under
  [Issues](https://github.com/Aplietexe/udemy-autocoupons/issues).
- Open a GitHub issue using the appropriate template.

Do you want to contribute directly?

- Make sure you understand the [architecture](../README.md#architecture).
- Ensure you installed `dev-requirements.txt`.
- Ensure pre-commit hooks are installed by running `pre-commit install
  --install-hooks`.
- Ensure there are no conflicts with the `main` branch.
- Update [README](/README.md) if needed.
- Make sure the code is well documented, using [Google Style Python
  Docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).
- A series of linters are present to help with code quality and run as
  pre-commit hooks. Most of them integrate with the editor, especially if you're
  using VS Code with the recommended extensions. You can always run them
  manually.
  - On staged files using `pre-commit run`.
  - On all files using `pre-commit run --all-files`.
- Code should be formatted with `black`. If you are using VSCode, this is
  automatically set up.
- Don't ignore the pre-commit hooks errors. If they fail, CI will fail too.
  However, they correct whatever caused them to fail when possible, so simply
  staging the new changes fixes it.
- Rebase merging is used for pull requests, so use a linear history.
