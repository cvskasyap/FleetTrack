# Google Antigravity setup

The repository includes two layers of agent context:

- `AGENTS.md` at the repository root: architecture, invariants, safety and development commands.
- `.agents/rules/fleettrack.md`: concise workspace rules for the data model, DB-API, triggers, MongoDB and test workflow.

## Open the project

1. Install Google Antigravity from [antigravity.google/download](https://antigravity.google/download), or install the supported Google Antigravity extension in your editor using the [official getting-started guide](https://antigravity.google/docs/getting-started).
2. Launch Antigravity and create a Project.
3. Add the extracted `FleetTrack` directory (or the cloned GitHub repository) as the project folder.
4. Trust the workspace when prompted so the agent can index its project files.
5. Start a conversation in the Agent panel and use the prompt in `prompts/antigravity-bootstrap.md`.

Antigravity's repository rules are designed to steer code changes without repeatedly pasting the entire assignment brief. Review suggested diffs, run tests, and commit only changes you understand.

## Suggested follow-up tasks

- Add filters for shipment status, priority and booking date to the dashboard.
- Add pagination/export to the shipment register.
- Add an audit page to compare current status with the most recent history event.
- Improve the MongoDB pipelines with a time-window filter and status-specific dwell percentiles.
- Add database integration tests using disposable PostgreSQL and MongoDB services in CI.

Do not provide Antigravity with database passwords or GitHub access tokens. Keep secrets in the local `.env` file or a secure credential manager.
