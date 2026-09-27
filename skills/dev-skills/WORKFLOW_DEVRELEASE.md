# Dev releases and image signing

Loaded on demand by the dev-skills skill, alongside `WORKFLOW_REFERENCE.md`,
**only when the user wants a pre-release build from a feature branch (a
`v1.2.3-dev.1` tag) or wants a container image signed with Cosign**. The
workflow selection and audit procedures, the review checklist and the template
best practices stay in `WORKFLOW_REFERENCE.md`.

---

## Dev releases

A dev release (pre-release) lets you build and test from a feature branch
without going through the full release process. The user pushes a tag like
`v1.0.0-dev.1` from their working branch, CI builds the artifact, and GitHub
marks the release as a pre-release so it won't be mistaken for a production
release.

This applies to **any** environment template (`WORKFLOW_<ENVIRONMENT>.md`) — not just Android.

**When to use dev releases:**
- Testing a build artifact (APK, binary, Docker image) before merging
- Sharing a work-in-progress build with testers
- Running the full release pipeline as a dry run on a feature branch

**Who pushes the tag.** Same rule as any other tag (`SKILL.md` Section 5.8):
the user pushes it, in both modes, because Claude's credentials are denied on
tag refs. And either way it is a release sequence — a pre-release still builds
and publishes an artifact, so all six gates apply before the tag goes anywhere.

**How it works:**
1. The user pushes a pre-release tag from their feature branch:
   ```bash
   git tag v1.0.0-dev.1
   git push origin v1.0.0-dev.1
   ```
2. The release workflow triggers (it matches `v*`)
3. The tag-on-default-branch check **skips** for pre-release tags
4. The build runs and creates a GitHub release marked as **pre-release**
5. When the feature branch merges and is ready for production, the user
   tags the merge commit with the final version (`v1.0.0`) — that tag
   IS on the default branch and creates a full release

**Tag naming convention:**

| Tag | Meaning | Branch check |
|---|---|---|
| `v1.0.0` | Production release | Must be on default branch |
| `v1.0.0-dev.1` | Development build | Any branch |
| `v1.0.0-alpha.1` | Early testing | Any branch |
| `v1.0.0-beta.1` | Feature-complete testing | Any branch |
| `v1.0.0-rc.1` | Release candidate | Any branch |

**To add dev release support to any template,** modify two places in the
release workflow:

1. **Tag-on-default-branch check** — skip for pre-release tags:
   ```yaml
   - name: Verify tag is on default branch
     env:
       DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
     run: |
       set -euo pipefail
       case "$GITHUB_REF_NAME" in
         *-dev.*|*-alpha.*|*-beta.*|*-rc.*) echo "Pre-release tag — skipping branch check."; exit 0 ;;
       esac
       if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
         echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
         echo "Releases come from the default branch only."
         echo "Use a pre-release tag (e.g., v1.0.0-dev.1) for feature branch builds."
         exit 1
       fi
   ```

2. **Release creation** — mark pre-releases:
   ```yaml
   - name: Create GitHub release
     env:
       GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
     run: |
       set -euo pipefail
       prerelease_flag=""
       case "$GITHUB_REF_NAME" in
         *-dev.*|*-alpha.*|*-beta.*|*-rc.*) prerelease_flag="--prerelease" ;;
       esac
       gh release create "$GITHUB_REF_NAME" \
         --title "$GITHUB_REF_NAME" \
         --notes-file release-notes.md \
         $prerelease_flag
   ```

**When suggesting workflows to the user,** ask whether they want dev release
support as part of the [Step 3 questions](#step-3--ask-all-questions-in-one-turn).
If yes, include the pre-release modifications in the generated workflow.

---

## Advanced: container image signing with Cosign

**What this does:** Cosign signs your Docker image with a cryptographic
signature that proves it came from your CI pipeline. Anyone pulling the image
can verify it was built by GitHub Actions, not tampered with, and came from
your repository. Think of it like a wax seal on a letter — it doesn't change
the contents, but it proves who sent it.

**When to use it:**
- You publish Docker images that others depend on
- Your organization requires supply-chain provenance
- You want to follow SLSA (Supply-chain Levels for Software Artifacts) best
  practices

**Not needed when:**
- The image is only used internally by your own team
- You're just getting started and want to keep things simple (you can always
  add signing later)

To add signing to a Docker release workflow, add these steps after the
`Build and push` step:

```yaml
      # --- Optional: sign the container image with Cosign ---
      # This uses keyless signing via GitHub's OIDC identity — no keys to
      # manage. The signature is recorded in a public transparency log
      # (Rekor) that anyone can verify.

      - name: Install Cosign
        uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2

      - name: Sign the container image
        env:
          DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          set -euo pipefail
          cosign sign --yes "ghcr.io/${GITHUB_REPOSITORY}@${DIGEST}"
```

**Required changes when adding signing:**
1. Add `id: build` to the `Build and push` step so the digest is accessible
2. Add `id-token: write` to the `permissions:` block (needed for OIDC)
3. Add `attestations: write` and `packages: write` if using attestation

**How users verify the signature:**
```bash
cosign verify \
  --certificate-identity-regexp "https://github.com/OWNER/REPO" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/OWNER/REPO:TAG
```
