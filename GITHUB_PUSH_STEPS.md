# GitHub Push Steps

## 1) Create a new GitHub repo
Suggested repo name:

- `satellite-project-successor-tool`

## 2) Open terminal in project folder

```bash
cd /path/to/this/project
```

## 3) Initialize git

```bash
git init
git add .
git commit -m "Initial commit: satellite successor tool"
```

## 4) Connect your GitHub repo

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

## 5) Important
Do **not** push:

- real service account JSON files
- `.streamlit/secrets.toml`
- downloaded private data

These are already ignored in `.gitignore`.
