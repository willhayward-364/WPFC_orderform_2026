# Whitburn Panthers FC kit order portal 2026

A browser-based kit ordering portal for coaches and club officials. `index.html`
contains the interface, `server.py` provides shared storage, and `IMG_4899.png`
supplies the club crest.

## Run locally

Python 3 is required; no third-party packages or build step are needed. Create
an individual official account and start the server:

```sh
python3 server.py --add-user "Club Kit Secretary"
python3 server.py
```

Enter a unique password when prompted. Repeat `--add-user` for each official;
using an existing name resets its password and signs out its sessions. Visit
`http://localhost:8000/` on the server machine. Tailwind CSS and the Inter font
are loaded from external services, so an internet connection is needed for
those assets. Opening the file directly or using a static server does not
provide official login or shared storage.

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
   Coaches still need to send their order file; an official must import it before
   it appears in the shared history. Downloading or emailing a file does not
   automatically submit it to the database.
5. Officials can use **Refresh shared orders** to see changes by other officials
   and expand **Order audit history** to see who changed an order and its saved
   snapshot. A conflicting edit is rejected and the latest orders are reloaded;
   review and reapply the rejected change.

## Data and access

The server saves orders, status changes, and audit snapshots in SQLite. All
official accounts on the same server see the same data. The audit includes
snapshots of deleted orders. Official sessions expire after 12 hours.

Existing browser-local orders are not migrated automatically. On each browser
that has old orders, sign in and use **Import orders from this browser**, then
refresh and verify the shared orders. Orders with IDs already in the database
are left unchanged. This does not erase the old browser copy; clear it only
after verifying the migration. Legacy orders already cleared from a browser
cannot be recovered by this feature.

For access from multiple devices, an administrator must deploy one continuously
running server on a host reachable by those devices. Set `WPFC_DATABASE` to an
absolute path on persistent, private storage for both account creation and
server startup. The default is `~/.wpfc-orders.sqlite3`. Back up the database
regularly using SQLite's backup API or an equivalent consistent backup, and
test restores. Do not put the database or backups in a public directory.
SQLite is intended here for one server instance sharing one database, not
multiple independent deployments.

For any access beyond the local machine, place the server behind a properly
configured HTTPS reverse proxy, keep the Python server bound to localhost, set
`WPFC_SECURE_COOKIE=1`, and restrict access to club officials and coaches as
appropriate. Configure proxy request-size limits and login rate limiting.
Protect the host and backups, and issue individual strong passwords; the
previous client-side passcodes no longer grant access. Static hosting alone
(including GitHub Pages) cannot run this server. Shared history is available
only once this service is deployed and reachable.

## Maintenance

Run `python3 -m unittest -v test_server` for the shared-storage tests.
Update `index.html`, `server.py` and the crest directly.
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
