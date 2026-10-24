# data-broker-removal

An agent skill that helps you remove your own data from data brokers, people-search sites, B2B contact databases and search results, keeps a log of every request, and builds a private HTML progress report.

It is written for agents that can drive a browser (for example Claude Code with Claude in Chrome), and the tracker works without an agent too.

## What is in the box

| path | what it is | committed? |
|---|---|---|
| `SKILL.md` | the instructions an agent follows, with the rules learned from a real run | yes |
| `brokers/*.json` | broker lists by region: `canada`, `usa`, `b2b`, `marketing-search`, each with opt-out URL, how automatic it is, steps and notes | yes |
| `scripts/removal.py` | `init`, `fastpath`, `mark`, `status`, `report` (Python 3, standard library only) | yes |
| `templates/report.html` | the dashboard template | yes |
| `profile/` | your name, emails, phone and address | **no** (git-ignored, only the example is public) |
| `state/` | which brokers you contacted, status and recheck dates | **no** |
| `reports/` | the generated HTML dashboard for you | **no** |

## Quick start

```sh
python3 scripts/removal.py init          # creates profile/profile.json and state/requests.json
$EDITOR profile/profile.json             # fill in your details
python3 scripts/removal.py fastpath      # the easiest brokers first
python3 scripts/removal.py mark apollo pending-email --email you@example.com --note "link sent"
python3 scripts/removal.py status
python3 scripts/removal.py report        # writes reports/<your-name>.html
```

Open the HTML file in a browser. It shows request counts, coverage, a bar per region, your next actions, rechecks that are due, and a filterable table of every site.

To use it as a Claude Code skill, copy or symlink this folder to `~/.claude/skills/data-broker-removal/`.

## How the fast path works

Each broker has an `automation` level. The ones that need no human step except clicking an emailed link (Apollo, RocketReach, Cognism, Kaspr) are listed first by `fastpath`, then ones with a single bot check, then ones with a single CAPTCHA tick. When you learn that another broker is easy, edit its entry in `brokers/*.json`; the next person starts from your improvement.

## Honest expectations

- This reduces exposure; it does not undo leaks that already happened.
- Brokers re-list people every 3 to 6 months. Re-run every quarter; the report shows what is due.
- Most large US people-search sites block automated browsers. Expect to solve some CAPTCHAs yourself. The skill never solves them for you.
- Where you live matters. A person who never lived in the US is rarely listed there. Start with your own country and with B2B databases if you work in sales-adjacent or founder roles.
- Public registries (company registers, court records) are not data brokers and cannot be removed with an opt-out.

## Safety rules the skill follows

- It acts only on your own data, with your explicit go-ahead.
- It never solves CAPTCHAs, creates accounts or types passwords for you.
- It runs one browser session at a time.
- It never sends your data anywhere except the opt-out form of the site you asked about.

## Contributing

Pull requests that improve `brokers/*.json` (verified URLs, steps, automation levels, defunct sites) are welcome. Never include anything from `profile/`, `state/` or `reports/`.

## Disclaimer

This is a personal-privacy tool, not legal advice. Opt-out pages change often, so check each link before relying on it. You are responsible for submitting requests only about yourself. Nothing here guarantees that a broker will delete your data or that it will not be listed again.

## Privacy of your own data

Your profile, request history and report never leave your machine unless you move them. They live in `profile/`, `state/` and `reports/`, which `.gitignore` excludes. Before pushing a fork, run `git ls-files` and confirm that only the `*.example.*` files and `.gitkeep` appear from those three folders.

## License

MIT. See `LICENSE`.
