# Documentation Workflow

**File:** `.github/workflows/docs.yml`

This workflow automatically builds and deploys the project documentation to
GitHub Pages.

## Trigger

The workflow runs:

- **On pull requests** to `main` - Validates documentation builds correctly
- **On pushes** to `main` - Builds and deploys to GitHub Pages

## Jobs

### Build Job

Runs on `ubuntu-latest` and builds the documentation.

#### Steps

1. **Checkout** - Clone repository with full history (`fetch-depth: 0`)
   - Full history needed for git-revision-date plugin
2. **Setup pixi** - Configure pixi with `docs` environment
3. **Check documentation** - Run `pixi run -e docs build-check`
   - Builds documentation using MkDocs
   - Validates all internal and external links using linkchecker
   - Fails on broken links or build errors
4. **Upload artifact** - Store built site for deployment

### Deploy Job

Runs only on pushes to `main` from the `usatlas/af-benchmarking` repository.

#### Conditions

- Event type is `push` (not pull request)
- Branch is `main`
- Repository is `usatlas/af-benchmarking` (not forks)

#### Steps

1. **Deploy to GitHub Pages** - Publishes the built documentation
   - Uses GitHub Pages deployment action
   - Updates the live documentation site

#### Deployed Site

The documentation is available at:
[https://usatlas.github.io/af-benchmarking/](https://usatlas.github.io/af-benchmarking/)

## Pixi Environment

The workflow uses the `docs` pixi environment:

**Python:** 3.14 **Dependencies:**

- mkdocs
- mkdocs-material theme
- mkdocs plugins (git-revision-date, glightbox, etc.)
- linkchecker
- beautifulsoup4, pillow, pygments

**Configuration:** See `pixi.toml` for full dependency list

## Documentation Stack

### MkDocs

Static site generator for project documentation:

- **Configuration:** `mkdocs.yml`
- **Source:** `docs/` directory
- **Output:** `site/` directory

### Material Theme

Modern, responsive theme with features:

- Dark/light mode toggle
- Navigation tabs
- Search functionality
- Code highlighting
- Content tabs and admonitions

### Plugins

- **search** - Full-text search
- **macros** - Jinja2 templating in markdown
- **table-reader** - Include CSV/Excel as tables
- **glightbox** - Image lightbox
- **git-revision-date-localized** - Last updated dates
- **section-index** - Section index pages
- **minify** - Minify HTML output

### Extensions

- **pymdownx** - Advanced markdown extensions
  - Code highlighting
  - Tabbed content
  - Admonitions
  - Task lists
  - Emoji support
  - Mathematical expressions (MathJax)

## Validation

### Link Checking

The workflow validates all links using linkchecker:

**Configuration:** `.linkcheckerrc`

Checks:

- Internal links between documentation pages
- External links to documentation and resources
- Anchor links within pages
- Image and asset references

### Build Validation

MkDocs builds with strict mode:

- Fails on warnings
- Validates all references
- Checks for missing files
- Ensures consistent structure

## Common Issues

### Documentation build failures

**Broken links:**

- Check the link validation step output
- Fix broken internal links (file paths)
- Update or remove broken external links
- Verify anchor links match headers

**Markdown syntax errors:**

- Ensure proper markdown formatting
- Check code block syntax
- Validate YAML frontmatter

**Missing files:**

- Verify all referenced images exist
- Check included snippets are available
- Ensure navigation references valid files

**Jinja2 template errors:**

- Escape GitHub Actions syntax with `{% raw %}...{% endraw %}`
- Check macro definitions
- Verify variable references

### Deployment failures

**Permissions:**

- Verify GitHub Pages is enabled
- Check workflow has `pages: write` permission
- Ensure `id-token: write` is set

**Branch protection:**

- Check `main` branch allows Pages deployment
- Verify required status checks pass

## Local Development

### Building Documentation

```bash
# Build documentation
pixi run -e docs build

# Serve with live reload
pixi run -e docs serve

# Build and validate links
pixi run -e docs build-check
```

### Previewing Changes

After running `pixi run -e docs serve`:

1. Open http://127.0.0.1:8000 in browser
2. Edit markdown files in `docs/`
3. Browser auto-reloads on save
4. Review changes immediately

### Testing Link Validation

```bash
# Build without directory URLs (required for linkchecker)
pixi run -e docs build-no-dir-urls

# Validate all links
pixi run -e docs validate
```

## Adding New Pages

1. **Create markdown file** in `docs/` directory
2. **Add to navigation** in `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - New Section:
      - Page 1: section/page1.md
      - Page 2: section/page2.md
```

3. **Build and test** locally:

```bash
pixi run -e docs serve
```

4. **Validate links** before committing:

```bash
pixi run -e docs build-check
```

## Configuration Files

### `mkdocs.yml`

Main MkDocs configuration:

- Site metadata (name, URL, author)
- Theme settings
- Navigation structure
- Plugin configuration
- Markdown extensions

### `pixi.toml`

Environment configuration:

- Python version (3.14 for docs)
- Dependencies (mkdocs, plugins, etc.)
- Tasks (build, serve, build-check, validate)

### `.linkcheckerrc`

Link validation configuration:

- URL patterns to ignore
- Timeout settings
- Check options

## Workflow Permissions

The deploy job requires specific permissions:

```yaml
permissions:
  pages: write # Deploy to Pages
  id-token: write # Verify deployment source
```

Set in the workflow at the job level.
