# Editing this book

The book's source is the `gitbook/` folder of the repository: plain Markdown, one file per page,
the table of contents in `gitbook/SUMMARY.md`. `.gitbook.yaml` at the repository root points
GitBook at that folder.

## Where it is published

The book is published on GitBook.com from this folder. Until Git Sync is connected, the published
copy does not follow the repository by itself: change the pages here, then bring the change into
GitBook (a change request, or a new import of the folder). With Git Sync (the space's *Configure* →
*GitHub Sync* → this repository and branch, direction "GitHub → GitBook"), every push updates the
site and edits made in GitBook's editor are committed back to `gitbook/`.

## Writing rules

* Instructions here, evidence in `docs/`. Do not copy measured numbers into the book; link to
  `docs/EXPERIMENTS.md` or the README summary, where each number has its date and data.
* Link repository files with full GitHub URLs (`https://github.com/pmixay/ReSense/blob/main/…`):
  relative links outside `gitbook/` do not exist on GitBook.
* Plain Markdown only (tables, code blocks, block quotes), so a page reads the same on GitHub and
  on GitBook.
* Commands must be the ones the scripts and README use; when a script changes, update its page.
