# Whitburn Panthers FC kit order portal 2026

A browser-based kit ordering portal for coaches and club officials. The application
is contained in `index.html`; `IMG_4899.png` supplies the club crest.

## Run locally

Open `index.html` in a modern browser, or serve this directory with a static web
server, for example:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000/`. There is no build or installation step.
Tailwind CSS and the Inter font are loaded from external services, so an internet
connection is needed for those assets.

## Using the portal

1. Enter the coach name and team or age group.
2. Select kit items, sizes and quantities, then add any squad numbers or initials.
3. Review the order and share it with the club. The portal can download a
   printable HTML order sheet or an Excel-compatible CSV. If the device cannot
   share the HTML file directly, attach the downloaded file to the opened email.
   Send the email to the club, then confirm this in the portal to see what
   happens next. The portal cannot verify that an email was sent or received.
4. Club officials can open the verification portal using the link on the page
   (or `#official`), import coach order HTML or CSV files, review and approve
   orders, and export or share a consolidated Total Sport order. The fallback
   email requires the recipient and downloaded attachment to be added manually.

## Data and access

Orders recorded in the official portal are saved in the browser's local storage,
not sent to a central database. They are only available in the same browser and
device unless exported and imported, and may be lost if browser data is cleared.
The official session uses session storage. The official passcode is checked in
client-side code and is not secure authentication; do not rely on it to protect
sensitive information.

## Maintenance

The site is a static application; update `index.html` and the crest directly.
Review this README when functionality changes. The recent changes section below
is generated from the five latest first-parent commits on `main` that change
files other than `README.md`. The GitHub Actions workflow refreshes it after
pushes to `main`, daily, and on manual dispatch. It commits only when the section
changes and requires Actions to have permission to write repository contents.
The generated list is a change summary, not a substitute for reviewing the
hand-written documentation.

## Recent changes on main

<!-- recent-changes:start -->
- `07c3ef7` Merge pull request \#20 from willhayward\-364/copilot/willhayward\-364\-submission\-notification
- `f757546` Merge pull request \#17 from willhayward\-364/copilot/create\-readme\-file
- `58708eb` Merge pull request \#15 from willhayward\-364/copilot/willhayward\-364\-remove\-text\-email
- `a14f7c9` Merge pull request \#13 from willhayward\-364/copilot/willhayward\-364\-consistent\-club\-official\-link
- `ba91f60` Merge pull request \#11 from willhayward\-364/copilot/club\-crest\-added
<!-- recent-changes:end -->
