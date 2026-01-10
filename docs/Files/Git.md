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
git status # just to see changed files
git add . # stage all changes for M1
git commit -m "M1: Core FIG engine (in-memory)"
git tag v0.1.0-M1 # tag this commit as the M1 milestone

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

Store Host Path Container Path
Postgres /var/lib/docker/volumes/faim_postgres_data/\_data /var/lib/postgresql/data
Qdrant /var/lib/docker/volumes/faim_qdrant_data/\_data /qdrant/storage
Redis /var/lib/docker/volumes/faim_redis_data/\_data /data

To completely wipe everything (nuclear option):
bash
docker compose -f docker-compose.dev.yml down -v
The -v flag removes all named volumes.

To see volume sizes:
bash
docker system df -v | grep faim

first we make a plan-- how it work ? what is bets to use -- WebAuthn/Passkeys (FIDO2) — Biometric/hardware key login (best security)
Magic Links — Email-based one-time login links
OAuth/OIDC — "Login with Google/GitHub" (you already have Keycloak!)
Device Trust + MFA — Certificate-based with push notifications-- ? and how it will work how user use this--where is start and end point--- when user login-,, where this data will save how information will save, how it is so secure and why? where data will store, auth is only for login, is has not contribution in app for other work?? ,, if user use passward less login how it will work? how user will entre the app,,? there should not any option to bypass? if hacker or anyone try to bypass, hack or do try another tick to use , immidiately hacker should block, app will unable to open, without login and verification, it should imposbie to login,,,,user will do passward less, user data will save inside postgres, user will have own isolated environment, user id -- one user permanaent ID, this user id will create after login automatically and and this user id will use all over appwide.., and this is is the identity of user, everyuser will have own different different id,,, by ID I can search the user information if user do something wrong and delete the dta or back on my admin app, so , right now i need proper architecture plan,
