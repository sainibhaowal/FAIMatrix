1️⃣ Init git in FAIM
cd /home/ravi_saini/FAIM
git init


If this is the first time you use git on this machine, set your name/email once:

git config --global user.name "Ravi Saini"
git config --global user.email "you@example.com"


(Use whatever email you want for commits.)






🔹 After you finish M1 (tests all green)

When M1 is fully done (code + tests + mypy + ruff all pass), run:

cd /home/ravi_saini/FAIM
git status                   # just to see changed files
git add .                    # stage all changes for M1
git commit -m "M1: Core FIG engine (in-memory)"
git tag v0.1.0-M1            # tag this commit as the M1 milestone


You can then check:
git log --oneline --decorate --max-count=5
git tag


You should see something like:
v0.0.0-M0
v0.1.0-M1






cd /home/ravi_saini/FAIM
git status
git add .
git commit -m "M2: <short description of M2 work>"
git tag v0.2.0-M2




🔹 General pattern for all future milestones

Just remember this template:

# After finishing Mn (code + tests + checks)
git status
git add .
git commit -m "Mn: <milestone name>"
git tag v0.n.0-Mn


Where:
n = milestone number (1, 2, 3, …)
Mn in the message = e.g. M3: API surface, M4: UI dashboard, etc.