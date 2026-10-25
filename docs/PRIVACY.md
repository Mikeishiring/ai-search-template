# Keep evidence separate

```text
work/
  career-context-ai/     reusable code and fictional examples
  my-private-evidence/   your records, claims and DASHBOARD.html
```

The personal CLI refuses workspace creation inside its own checkout. It cannot tell whether another folder is cloud-synced or belongs to another public repository. Choose the destination deliberately. This is a local safeguard, not an OS sandbox.

| Action | Where content goes |
|---|---|
| Personal CLI commands | Local files only; no network, model, Git or subprocess calls |
| Open the HTML | Browser reads embedded local text; no background requests or external assets |
| Click an original-source link | Browser contacts that service |
| Supply evidence to an AI host | Host and potentially its model provider, under their settings |
| Push a private repository | GitHub receives the committed files |
| Send or publish the dashboard | Recipient gets embedded evidence, including full imported text |

This CLI does not encrypt files. Local backups, browser extensions and cloud-synced folders remain part of your privacy boundary. It does not create Git repositories or inherit the template's remotes.

## Optional remote backup

Create an empty **private** repository in your own account. Initialize Git in the personal workspace and select the intended files. Confirm visibility in GitHub and inspect the staged diff before pushing. Keep credentials in a credential store/environment, outside captures.

Keep its remote distinct from the template. Do not merge private history into the public template, add a data submodule or enable Pages for the archive. Review collaborators and integrations. `.gitignore` neither removes committed secrets nor makes uploaded files private.

The generated ignore file excludes common environment/key filenames. It does not inspect arbitrary source text for secrets. This template cannot determine whether you are authorized to retain employer or third-party records. Inspect selected material before remote backup or AI sharing.

## Public reuse

Create a separate reviewed export. Renaming people is insufficient: quotes, dates, compensation, URLs and unusual events can still identify them. Do not assume an AI rewrite is anonymized. Never change the archive to public to publish a resume; publish a separately selected resume without raw supporting evidence.

If a secret was committed, deleting the current text does not remove it from history or other copies. Revoke it and address those copies deliberately.
