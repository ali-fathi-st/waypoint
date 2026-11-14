# 1. Getting started

This guide gets the site running on your computer. It takes about two
minutes, and you don't need to install any packages.

## What you need

- **Git**, to download the code: https://git-scm.com/downloads
- **One** of these, to serve the files:
  - Python 3 (already on most Macs and Linux; on Windows install it from
    https://www.python.org/downloads/ and tick "Add python.exe to PATH")
  - Node.js 18 or newer: https://nodejs.org/
  - VS Code with the **Live Server** extension
- A modern browser (Chrome, Edge, Firefox or Safari)

## 1. Download the code

```bash
git clone https://github.com/ali-fathi-st/waypoint.git
cd waypoint
```

## 2. Start a local web server

Pick one:

**Python** (Mac / Linux):

```bash
python3 -m http.server 8080 --directory frontend
```

**Python** (Windows, PowerShell):

```powershell
py -m http.server 8080 --directory frontend
```

**Node.js:**

```bash
npx serve frontend
```

**VS Code:** open the `waypoint` folder, right-click `frontend/index.html`, and
choose **Open with Live Server**.

## 3. Open the site

Go to **http://localhost:8080** (or the address your server printed).

You'll see the dashboard with sample data. Everything works: shortlist jobs,
start an application, record it as applied, add interviews, edit your profile.

To stop the server, press `Ctrl + C` in the terminal.

## Why not just double-click index.html?

The site's JavaScript is split into modules (`import` / `export`). Browsers
refuse to load modules from a `file://` address for security reasons, so the
page would load without any data. A local server serves the files over
`http://`, the same way GitHub Pages does.

## A quick tour

1. **Dashboard**: the guide at the top explains the four steps. Hide it once
   you've read it.
2. **Jobs**: type "analyst" in Title, or set Match score to "70 or higher".
   The address bar updates, so you can bookmark a filtered view.
3. **Open a job**: the "Match score" panel shows how every point is earned.
4. **Start application**, then **Record as applied**. You'll be asked to
   confirm you applied on the employer's site. Waypoint never applies for you.
5. **Applications**: switch between Board and Table.
6. **Settings → Developer**: switch to "Empty", "Slow" or "Error" to see how
   every page handles those situations. Switch back to "Normal" afterwards.

## Your changes and the sample data

Your clicks change the sample data, and the changes are saved in your browser
(localStorage), so they survive a refresh. They never leave your computer.
To start over: **Settings → Developer → Reset sample data**.

## Something's wrong?

| Problem | Fix |
| --- | --- |
| Page loads but stays empty | You opened the file directly. Use a local server (step 2). |
| `python3: command not found` | On Windows use `py`. Otherwise install Python. |
| `Address already in use` | Another program uses port 8080. Try `8081`. |
| Old version after editing a file | Hard refresh: `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac). |
| Something else | Open the browser's developer tools (`F12`) → Console tab. Errors there name the file and line. |

Next: [02 Project structure](02-project-structure.md)
