# Registry

A registry is a folder of skills plus a generated `registry/index.json`. It is static, so GitHub is all you need to
host one. This repository is the community registry. Its skills are listed on the website at
<https://lethe044.github.io/agentskill-kit/>.

## Search and install

```bash
askit search "git release"
askit install changelog-generator                       # into ./.claude/skills
askit install changelog-generator --target cursor
askit install changelog-generator --target claude --global
askit install github:owner/repo/skills/my-skill@main    # any public GitHub folder
askit install ./path/to/skill                           # a local folder
askit list --installed
askit uninstall changelog-generator
```

Registry installs verify checksums, then run lint and scan on the download before anything is written.
Set `GITHUB_TOKEN` to avoid GitHub API rate limits when installing from `github:` sources.

## Use another registry

```bash
askit search docker --registry https://example.com/registry/index.json
askit config set registry https://example.com/registry/index.json
```

## Host your own

1. Put skills in `skills/` in a repository.
2. Build the index with your raw file URL as the base:

   ```bash
   askit registry build skills --base-url https://raw.githubusercontent.com/OWNER/REPO/main/
   ```

3. Commit `registry/index.json` and publish the website with `askit registry site skills --out site`
   (the included `pages.yml` workflow does this for GitHub Pages).

`askit registry build --check` exits with 1 when the committed index is stale, which is handy in CI.

## Contribute a skill

```bash
askit init my-skill --script
# edit, then:
askit lint skills/my-skill --strict
askit scan skills/my-skill
askit test skills/my-skill
askit score skills/my-skill
```

If you have a fork of this repository checked out:

```bash
askit publish skills/my-skill --registry-dir ../agentskill-kit --open-pr
```

`publish` runs the quality gate, copies the skill into the checkout, rebuilds the index and, with `--open-pr`,
creates the branch, commit and pull request using `git` and the GitHub CLI. Without `--registry-dir` it packs the
skill into a zip with a manifest (`askit pack`) and prints sharing options. See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Index format

```json
{
  "schema": 1,
  "base_url": "https://raw.githubusercontent.com/OWNER/REPO/main/",
  "skills": [{
    "name": "log-analyzer", "description": "...", "version": "1.0.0", "tags": ["logs"],
    "path": "skills/log-analyzer",
    "files": [{"path": "SKILL.md", "sha256": "...", "size": 1234}],
    "score": 1.0, "grade": "A", "safety": 100, "tested": true, "tests_passed": 4, "tests_total": 4
  }]
}
```
