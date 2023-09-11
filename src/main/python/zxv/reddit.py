#!/usr/bin/env python3

from datetime import datetime
import json
import os
import pandas
import praw
import sqlite3

class Authentication:
    def __init__(self, fn="secrets.txt"):
        secrets = json.load(open(fn, "r"))
        self.username = secrets["username"]
        self.password = secrets["password"]
        self.client_id = secrets["client_id"]
        self.secret = secrets["secret"]

    def read_only_reddit(self):
        return praw.Reddit(
                client_id="0tnk3CjMygJTjoqRFJJZfA",
                client_secret="S0qUVNDQxc1Wo0a7KOH3zi71NMtgJA",
                user_agent="Python/urllib"
               )

class Token:
    def __init__(self, fn="token.txt"):
        self.token_response = json.load(fn)


class ActivityDb:
    def __init__(self, db_fn, readonly=True):
        self._db_fn = db_fn
        self._readonly = readonly
        self._conn = None
        self._subreddits_table = SubredditsTable()
        self._submissions_table = SubmissionsTable()
        self._redditors_table = RedditorsTable()

    def __enter__(self):
        if self._readonly:
            self._conn = sqlite3.connect(f"file:{self._db_fn}?mode=ro", uri=True)
        else:
            existed = os.path.exists(self._db_fn)
            self._conn = sqlite3.connect(self._db_fn)
            if not existed:
                self._create_tables()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._conn.close()
        self._conn = None

    def execute_statement(self, stmt, values=None):
        if values is None:
            return self._conn.execute(stmt)
        else:
            return self._conn.execute(stmt, values)

    def commit(self):
        self._conn.commit()

    def get_subreddit_id(self, name):
        return self._subreddits_table.get_subreddit_id(name, self._conn)

    def get_redditor_id(self, redditor):
        return self._redditors_table.get_redditor_id(redditor, self._conn)

    def subreddit_posts_per_hour(self, subreddit, begin_date, end_date):
        stmt = str(
                "WITH RECURSIVE "
                "dates(date) as ( "
                    f"values('{begin_date}') "
                    "union all "
                    "SELECT date(date, '+1 day') FROM dates "
                    f"WHERE date < '{end_date}' "
                "), "
                "hours(hour) as ( "
                     "values(0) "
                     "UNION all "
                     "SELECT hour + 1 FROM hours WHERE hour < 23 "
                "), "
                "counts(date, hour, count) as ( "
                    "SELECT "
                        "strftime('%Y-%m-%d', DATE(DATETIME(created, 'unixepoch'))) counts_date, "
                        "CAST (strftime('%H', DATETIME(created, 'unixepoch')) AS INTEGER) counts_hour, "
                        "COUNT(*) "
                    "FROM submissions "
                    f"WHERE subreddit_id = (SELECT id FROM subreddits WHERE name = '{subreddit}') "
                    "GROUP BY counts_date, counts_hour "
                ") "
                "SELECT "
                    "dates.date, hours.hour, counts.count "
                "FROM dates, hours "
                "LEFT JOIN counts ON dates.date = counts.date AND hours.hour = counts.hour "
                "ORDER BY dates.date, hours.hour "
        )

        timeseries = []
        for row in self._conn.execute(stmt).fetchall():
            (date, hour, count) = row
            if count is None:
                count = 0
            timeseries.append(
                [datetime.strptime(f"{date} {hour}:00", "%Y-%m-%d %H:%M"), count]
            )
        df = pandas.DataFrame(timeseries, columns=["tm", "count"])
        df.set_index("tm")
        return df

    def _create_tables(self):
        self._subreddits_table.create(self._conn)
        self._submissions_table.create(self._conn)
        self._redditors_table.create(self._conn)
        self._conn.commit()

class DbTable:
    def __init__(self, name):
        self._name = name
        self._columns = []

    def create(self, conn):
        stmt = f"CREATE TABLE {self._name} ("
        stmt += ", ".join(self._columns)
        stmt += ")"
        conn.execute(stmt)

class SubmissionsTable(DbTable):
    def __init__(self):
        super().__init__("submissions")
        self._columns.extend([
            "id INTEGER PRIMARY KEY",
            "subreddit_id INTEGER NOT NULL",
            "author_id INTEGER NOT NULL",
            "permalink TEXT NOT NULL",
            "created INTEGER",
            "num_comments INTEGER",
            "score INTEGER",
            "upvote_ratio NUMERIC",
        ])

class RedditorsTable(DbTable):
    def __init__(self):
        super().__init__("redditors")
        self._columns.extend([
            "id INTEGER PRIMARY KEY",
            "name TEXT NOT NULL",
            "created INTEGER"
        ])
        self._id_by_name = {}

    def get_redditor_id(self, redditor, conn):
        if redditor.name not in self._id_by_name:
            stmt = f"SELECT id FROM {self._name} WHERE name = '{redditor.name}'"
            results = conn.execute(stmt).fetchone()
            if results is not None:
                redditor_id = results[0]
            else:
                stmt = str(f"INSERT INTO {self._name} (name, created) VALUES "
                            f"('{redditor.name}', {redditor.created}) RETURNING id")
                redditor_id = conn.execute(stmt).fetchone()[0]
            self._id_by_name[redditor.name] = redditor_id
        return self._id_by_name[redditor.name]

class SubredditsTable(DbTable):
    def __init__(self):
        super().__init__("subreddits")
        self._columns.extend([
           "id INTEGER PRIMARY KEY",
           "name TEXT NOT NULL",
        ])
        self._id_by_name = {}

    def get_subreddit_id(self, name, conn):
        if name not in self._id_by_name:
            stmt = f"SELECT id FROM subreddits WHERE name = '{name}'"
            results = conn.execute(stmt).fetchone()
            if results is not None:
                subreddit_id = results[0]
            else:
                stmt = f"INSERT INTO subreddits (name) VALUES ('{name}') RETURNING id"
                subreddit_id = conn.execute(stmt).fetchone()[0]
            self._id_by_name[name] = subreddit_id
        return self._id_by_name[name]
