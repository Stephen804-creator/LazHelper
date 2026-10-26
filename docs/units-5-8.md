# Laz Helper implementation units 5–8

This follow-up is intentionally a separate, dependent pull request. It builds on the connector and device Ask/voice work in PR #15; it should be merged after PR #15, not directly into the older integration base.

## Unit 5 — Device workflow regression coverage

Added `tests/test_device_flow.py` to exercise the connector's important user journeys through its HTTP API:

- Pair a browser origin and use the returned token.
- List a granted Downloads folder as metadata only; directory listings must not contain file contents.
- Revoke a grant and verify the next request is denied.
- Preview a create operation, verify it does not change files, verify execution is blocked before approval, then approve and verify the file and activity record.
- Attempt to move a file outside the granted destination and verify that approval does not bypass permissions.
- Feed the planner a create path outside the selected folder and verify that the unsafe proposal is discarded.
- Reject a remote model endpoint so local file content is not sent to an arbitrary remote model URL.

## Unit 6 — Permission and data-boundary regression checks

The tests above protect against accidental permission widening, execution before confirmation, content leaking into metadata listings, and local AI configuration drifting to a non-loopback endpoint. They complement existing tests for one-time pairing, symlinks, protected paths, duplicate scans, quarantine deletion, and ask-every-time behavior.

These tests exercise the connector API, not the actual browser's private-network permission prompt. Browser behavior still varies by browser version and security policy.

## Unit 7 — Connector package verification

The release workflow now runs for pull requests as well as release tags. Each Windows, macOS, and Linux build attempts to launch its standalone executable with `--version` before packaging. Each package contains the executable, connector README, and a SHA-256 checksum manifest.

The CLI version option is intentionally non-interactive; normal startup continues to run the local connector. A successful build confirms packaging and process startup, but it does not prove that every target operating system's native folder picker works.

## Unit 8 — Browser acceptance checklist

Before merging or publishing installers, perform the following on a real desktop browser and connector process:

1. Open the hosted Laz Helper site in a supported browser and verify first-visit onboarding appears.
2. Start Laz Connector locally. Pair only after verifying the website origin in the confirmation dialog.
3. Grant read-only access to a test Downloads folder and verify filenames, sizes, and modification times appear.
4. Verify the listing does not display file contents and that changing/revoking the grant prevents further reads.
5. Add a new test file and verify the page notices it on the next permitted refresh. In `ask_every_time` mode, verify background refresh is disabled and manual refresh asks for approval.
6. Ask a question about a small UTF-8 text file with the local model running. Verify the answer uses local evidence and the connector remains the request target.
7. Request a file operation. Verify the plan itself changes nothing; decline one operation and approve another. Confirm only the approved, authorized operation runs.
8. Stop the connector and verify the UI reports disconnection; restart it and verify reconnection behavior.
9. Repeat the essential flow in each browser/OS combination you intend to support. Browser local-network access prompts, native dialogs, and OS security policies may differ.

## Release gate

Do not publish a public `connector-v*` release until CI passes, the generated package artifacts have been inspected, and the browser acceptance checklist has been completed on supported platforms. The hosted website cannot silently install the connector or bypass OS/browser permissions.
