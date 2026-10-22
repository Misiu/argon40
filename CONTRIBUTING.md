# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `develop`.
2. If you've changed something, update the documentation.
3. Run the Ruff linter, formatter, and repository hooks described below.
4. Test you contribution.
5. Open a pull request targeting `develop`.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

We use [Ruff](https://docs.astral.sh/ruff/) for Python linting, import sorting, and
formatting, [uv](https://docs.astral.sh/uv/) for development dependencies, and
[prek](https://prek.j178.dev/) for Git hooks, following the workflow used by Spook.
Install the uv version required by `[tool.uv]` in `pyproject.toml`, then run:

```shell
uv sync --frozen --dev
uv run --frozen prek install
```

Apply safe lint fixes before formatting:

```shell
uv run --frozen ruff check --fix .
uv run --frozen ruff format .
```

Run the same checks as CI before opening a pull request:

```shell
uv lock --check
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen prek run --all-files --show-diff-on-failure
```

Commit `uv.lock` with dependency changes. Renovate maintains development tool
versions, the lockfile, and GitHub Actions pinned to full commit SHAs. Keep the
version or branch comment next to each action SHA so updates remain readable.

Ruff targets Python 3.12 because the integration supports Home Assistant 2025.1
and newer. CI also checks syntax on Python 3.13 and 3.14. These checks do not
replace testing against Home Assistant or testing the hardware on a Raspberry Pi.
Runtime dependencies remain in `custom_components/argon40/manifest.json`; the uv
environment contains development tools and does not install Home Assistant or
the Raspberry Pi libraries.

## Test your code modification

This custom component is based on [blueprint template](https://github.com/custom-components/blueprint).

It comes with development environement in a container, easy to launch
if you use Visual Studio Code. With this container you will have a stand alone
Home Assistant instance running and already configured with the included
[`.devcontainer/configuration.yaml`](.devcontainer/configuration.yaml)
file.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
