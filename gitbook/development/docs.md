# Editing this book

The book's source is the `gitbook/` folder of the repository: plain Markdown, one file per page,
the table of contents in `gitbook/SUMMARY.md`. The same source works in two places.

## GitHub Pages (built by CI)

[`.github/workflows/pages.yml`](https://github.com/pmixay/ReSense/blob/main/.github/workflows/pages.yml)
builds the book with [HonKit](https://github.com/honkit/honkit) (the open-source continuation of the
GitBook toolchain), adds the web dashboard under `dashboard/` with two sample status streams, and
publishes the result to `https://pmixay.github.io/ReSense/` on every push to `main` that touches
`gitbook/`, `web/` or the workflow. Other branches only build it (the artifact is attached to the
run), so a broken page fails before it reaches `main`.

One-time repository setting: *Settings → Pages → Build and deployment → Source: GitHub Actions*.
Until that is set, the workflow builds the site and skips the deployment with a notice.

## Build locally

```bash
cd gitbook
npm ci                      # HonKit, pinned in package-lock.json
npx honkit serve            # http://localhost:4000, rebuilds on save
npx honkit build . ../_site # the static site, as CI builds it
```

## GitBook.com (optional)

`.gitbook.yaml` at the repository root points GitBook's Git Sync at `gitbook/`. To host the same
pages on gitbook.com: create a space → *Configure* → *GitHub Sync* → this repository, branch
`main`, direction "GitHub → GitBook". Edits made in GitBook's editor are then committed back to
`gitbook/`.

## Writing rules

* Instructions here, evidence in `docs/`. Do not copy measured numbers into the book; link to
  `docs/EXPERIMENTS.md` or the README summary, where each number has its date and data.
* Link repository files with full GitHub URLs (`https://github.com/pmixay/ReSense/blob/main/…`):
  relative links outside `gitbook/` do not exist in the built site.
* Plain Markdown only (tables, code blocks, block quotes), so HonKit and GitBook.com render the
  same page.
* Commands must be the ones the scripts and README use; when a script changes, update its page.
