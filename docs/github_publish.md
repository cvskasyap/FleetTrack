# Publish FleetTrack to GitHub

The project folder is structured as a Git repository. To publish it, use an authenticated GitHub session on your own machine.

## Create the remote repository

1. Open [GitHub — New repository](https://github.com/new) and sign in.
2. Repository name: `FleetTrack`.
3. Choose Public or Private according to the course submission instructions.
4. Create it as an empty repository. Do not initialise it with a README, licence or `.gitignore` because these are already in the project.

## Push the project

Open a terminal in the extracted project folder:

```bash
git init -b main
git add .
git status --short
git commit -m "Build FleetTrack logistics analytics project"
git remote add origin https://github.com/YOUR_USERNAME/FleetTrack.git
git push -u origin main
```

Replace `YOUR_USERNAME` with the GitHub username that owns the new repository. When prompted, authenticate using Git Credential Manager or GitHub CLI. Do not place access tokens in commands, source files, `.env`, notebooks or screenshots.

If Git asks for author identity, set it for this repository and retry the commit:

```bash
git config user.name "Your Name"
git config user.email "your-verified-github-email@example.com"
```

## Verify the submission

- Open the GitHub repository URL and confirm source, SQL, docs, notebook and tests are visible.
- Confirm `.env` is absent. The `.gitignore` excludes it.
- Open the Actions tab and confirm the `FleetTrack checks` workflow passes.
- Submit the repository URL (not the ZIP attachment URL) to the course portal.
