# Publish Native Boot Studio on GitHub

The prepared packages do not upload anything to GitHub automatically. This guide covers the source repository and the Windows release.

## 1. Create the repository

Extract `NativeBootStudio-4.2.2-source.zip` into a new folder. Create a public GitHub repository, for example `NativeBootStudio`. For the Git command route below, create an empty repository without an automatically generated README/license.

Upload the **contents** of the extracted source folder, preserving the subfolders. `README.md` must be at the repository root, alongside `README.de.md`, `LICENSE`, `src/`, `tests/`, `docs/`, `scripts/`, `licenses/`, and `.github/`. Include `.gitignore` and `.gitattributes`; they may be hidden in Explorer. Do not simply upload the source ZIP as the repository's only file.

Check that there are no Xbox/XEX/NAND files, XexTool, Xenia, local `settings.json`, private projects, `UserPresets`, or build caches. The source archive is designed to exclude them. Do not upload the old private 4.2 bundle.

Alternatively, with Git installed, open PowerShell in the extracted source root:

```powershell
git init -b main
git add .
git status --short
git commit -m "Initial public release of Native Boot Studio"
git remote add origin YOUR-REPOSITORY-URL
git push -u origin main
```

Replace `YOUR-REPOSITORY-URL` with your repository's HTTPS URL. Authenticate using GitHub's normal login mechanism; never paste access tokens into the source or documentation. Inspect `git status` before committing.

The README displays the English overview with a German link. The MIT license applies to the project's own source; dependency notices remain in `licenses/`.

## 2. Create release v4.2.2

On GitHub, open **Releases → Draft a new release**:

1. Create tag `v4.2.2` targeting the tested commit on `main`.
2. Use the title **Native Boot Studio 4.2.2**.
3. Copy the ready-to-use [English notes](releases/v4.2.2.en.md). Append the [German notes](releases/v4.2.2.de.md) if you want both languages on the release page.
4. Attach `NativeBootStudio-4.2.2-Windows-x64.zip` and `SHA256SUMS.txt`. The clean source ZIP is optional; GitHub also offers source archives from the tag.
5. Save as a draft, review the archive contents and notes, then publish.

Use only the newly generated public archives. The Windows ZIP contains the program, English/German user and installation guides, a CRC-32 helper, and runtime license notices. Users provide their own original boot animation, XexTool, optional Xenia, and the remap if using the HDD route.

GitHub Actions builds and attaches workflow artifacts after relevant pushes. It does not create or publish a release by itself. Wait for checks to pass before publishing a build produced by that workflow.

## 3. Future updates

Update `VERSION` in `src/studio.py`, the changelog, guides/versioned filenames as needed, and the release notes. Run formatting checks, tests, and `python scripts/build_release.py --build`. Review the new ZIPs, tag the tested commit, and publish a new release. Preserve users' preset libraries when documenting updates.

Official references: [GitHub release management](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository), [licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository), and this project's [distribution notes](DISTRIBUTION.en.md).
