
### Building

Running `make` will build the virtual environment in `./venv`. Scripts can
then be run like `venv/bin/python3 scripts/daily_activity`.

### Usage

Create a secrets.txt file containing the values from Reddit:
```
{
"username": "...",
"password": "...",
"client_id": "...",
"secret": "..."
}
```

Build database of subreddit activity with `venv/bin/python3 scripts/daily_activity <subreddit>`.
Plot subreddit activity with `venv/bin/python3 scripts/posts_per_hour <subreddit>...`.

With a secrets.txt file in the current directory, the following commands should show a plot:
```
% venv/bin/python3 scripts/daily_activity wallstreetbets
% venv/bin/python3 scripts/posts_per_hour $(date -v -15d "+%Y-%m-%d") $(date "+%Y-%m-%d") wallstreetbets
```
