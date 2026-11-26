# Installation

schemify needs **Python 3.12 or newer**. Install it as a tool, so the `schemify`
command is available everywhere:

=== "uv"

    ```text
    uv tool install schemify-cli
    ```

=== "pipx"

    ```text
    pipx install schemify-cli
    ```

=== "pip"

    ```text
    pip install schemify-cli
    ```

The package is called `schemify-cli`, and the command it installs is `schemify`.

Check that it works:

```text
schemify --help
```

## In a project

To use schemify from Python ([Python API](python.md)), add it as a dependency:

=== "uv"

    ```text
    uv add schemify-cli
    ```

=== "pip"

    ```text
    pip install schemify-cli
    ```

and import it as `schemify`.

## Shell completion

```text
schemify --install-completion
```

Restart the shell after installing it.

## Upgrade and uninstall

=== "uv"

    ```text
    uv tool upgrade schemify-cli
    uv tool uninstall schemify-cli
    ```

=== "pipx"

    ```text
    pipx upgrade schemify-cli
    pipx uninstall schemify-cli
    ```

## Terminals

schemify draws its questions with [questionary](https://questionary.readthedocs.io), so
it needs an interactive terminal: Windows Terminal, PowerShell, cmd, or any Linux or
macOS terminal. Arrow keys pick choices, ++enter++ confirms, and ++ctrl+c++ stops
without saving anything.

## The example files

The schemas and data in this documentation are in the
[`examples/`](https://github.com/aaltatan/schemify-cli/tree/main/examples) folder of the
repository:

```text
git clone https://github.com/aaltatan/schemify-cli
cd schemify-cli/examples
```
