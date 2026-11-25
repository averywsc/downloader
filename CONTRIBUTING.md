# Contributing to Dodown

Thanks for your interest in contributing to **Dodown**!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/averywsc/downloader.git
   cd downloader
   ```
2. Install dependencies with Python 3.13+ (`uv` recommended):
   ```bash
   uv sync --dev
   ```
3. Run the app locally:
   ```bash
   uv run python Dodown.py
   ```
4. Run the test suite:
   ```bash
   uv run pytest
   ```

## Guidelines

- Keep all user-facing strings, comments, docs, and commit messages in **English**.
- Follow the **Totone Studio UI** design tokens defined in `app/view/totone_theme.py` (`#050c1f` background, `#091534` panels, `#f4f7ff` text, `#8d9cc4` muted text, `#16254d` dividers, `#34477e` borders, `#ffffff` accent).
- Keep protocol-specific logic isolated inside `features/<pack_name>/`.
- Include tests for bug fixes and new features where applicable.

## Links

- Portfolio: [averybeuth.xyz](https://averybeuth.xyz)
- Issues: [github.com/averywsc/downloader/issues](https://github.com/averywsc/downloader/issues)
