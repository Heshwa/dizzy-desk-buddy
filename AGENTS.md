# Instructions for agents working on Dizzy

- Read `HANDOVER.md`, `v2/README.md`, and `v2/reports/TEST-REPORT.md` before changing the project.
- Treat V2 as the active design. Keep V1 runnable and avoid replacing its assets or behavior while working on V2.
- Preserve the distinction between Webots/Wokwi/model checks and physical hardware validation. Do not describe simulated results as physical passes.
- Update `v2/reports/TEST-REPORT.md` whenever a check is rerun or a new limitation is found. Record the test setup and any failures.
- Keep API keys, Wi-Fi credentials, MQTT passwords, Wokwi tokens, local voice models, runtime files, and toolchain downloads out of commits. Use `.env.example` for blank configuration templates.
- Verify the published project tree stays clean with `git status`; do not commit generated build caches from `v2/.work/`.
- For reproducible commands, deliverable paths, hardware risks, and remaining priorities, follow `HANDOVER.md`.
