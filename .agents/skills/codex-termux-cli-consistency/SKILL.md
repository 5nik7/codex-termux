---
name: codex-termux-cli-consistency
description: "Implement or review codex-termux CLI changes while keeping behavior, terminal styling, usage/help, manual, completion, and docs aligned. Use when changing commands, flags, defaults, configuration, output, or retiring obsolete interfaces in this repository."
---

# Codex Termux CLI Consistency

Read the repository's [development rules](../../../AGENTS.md) and
[CLI maintenance guide](../../../docs/CLI_MAINTENANCE.md). The guide owns the
style preferences and review procedure; follow current source behavior and the
user's task when reconciling documentation. Do not duplicate the command catalog
inside this skill.

Identify the actual checkout and preserve existing changes. Compare the source
wrapper with the installed command before treating installed help as current;
the same VERSION can describe different local candidates. Use root help as the
visual reference, and the checkout's parser/runtime as the behavior reference.

For each relevant change:

1. Follow the affected command and its related flags, defaults, backends,
   configuration, errors, output streams, and forwarding boundaries. Review
   neighboring controls for functionality invalidated by the change.
2. Decide which controls to retain, update, deprecate, or remove using the guide's
   compatibility policy. Preserve useful published behavior and identify a
   working migration before retiring a public interface.
3. Reconcile every affected surface in the guide's change matrix in the same
   change. Reuse the existing help renderers and semantic color roles. Keep
   machine output, explicit raw logs/service output, and Codex streams intact.
   Human service views may format native results; preserve unknown details and
   producer exit codes. Reconcile the guide's linked output coverage matrix.
4. Exercise observable behavior and actual shell completion, including rejected
   combinations and plain-output modes. Regenerate with the existing builder;
   validate the package manifest, docs/skill links, and source archives.
5. Record the compatibility decisions, checks, skips, and remaining gaps in the
   current validation record. Preserve earlier evidence and distinguish fixtures
   from native service execution and real-account acceptance.

Read the guide again when changing these conventions. Keep this skill and its
linked guide portable in source archives. This workflow does not authorize
installation, live service changes, publication, or a new runtime dependency.
