#!/usr/bin/env python3

"""Test harness for examining the behaviour of CloudFlare caches"""

from __future__ import annotations

from typing import Dict, Generator, List, Mapping, Union

import itertools
import sqlite3
import time

import requests
import yaml

# The set of headers we want to extract from the response.
HEADERS = [
    "age",
    "date",
    "cache_control",
    "cf_ray",
    "cf_cache_status",
    "cf_request_id",
    "cache_control",
]

CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS requests ("
    "url TEXT NOT NULL,"
    "status INT NOT NULL,"
    "age INT NOT NULL,"
    "date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
    "cache_header TEXT NOT NULL,"
    "cache_status TEXT NOT NULL,"
    "request_id TEXT NOT NULL,"
    "ray_id TEXT NOT NULL"
    ")"
)

INSERT_DATUM = (
    "INSERT INTO requests"
    "(url, status, age, cache_header, cache_status, request_id, ray_id) "
    "VALUES "
    "(:url, :status, :age, :cache_control, "
    ":cf_cache_status, :cf_request_id, :cf_ray)"
)

Config = Dict[str, str]


def main() -> None:
    """Make requests to cloudflare and record the responses until stopped"""

    configurations = load_config()

    connection = sqlite3.connect("cf-cache-test.db")
    cursor = connection.cursor()

    cursor.execute(CREATE_TABLE)

    while True:
        try:
            cursor.executemany(
                INSERT_DATUM, do_tick([k.copy() for k in configurations])
            )

        except KeyboardInterrupt:
            break

        connection.commit()
        print(".", end="")
        time.sleep(2)

    connection.commit()
    cursor.close()
    connection.close()


def do_tick(configurations) -> Generator[Mapping[str, Union[int, str]], None, None]:
    """Request each of the URLs in the configuration state"""

    for query in configurations:
        if "url" not in query:
            print(query)
            continue

        url = query["url"]
        del query["url"]

        response = requests.get(url, {k: query[k] for k in query if query[k]})

        received: Dict[str, Union[int, str]] = {
            k.lower().replace("-", "_"): response.headers[k]
            for k in response.headers
            if k.lower().replace("-", "_") in HEADERS
        }

        for header in HEADERS:
            if header not in received:
                received[header] = 0

        received["url"] = response.url
        received["status"] = response.status_code

        yield received


def load_config() -> List[Config]:
    """Load the YAML config.

    Each top level element in the config is taken as a query parameter,
    and a list of values is expected.

    These are then permuted into all combinations of the config, and each is
    treated as a separated URL
    """

    with open("config.yaml") as yaml_handler:
        config = yaml.safe_load(yaml_handler)

    params = list(product_dict(**config))

    return params


def product_dict(
    **kwargs: Dict[str, List[str]]
) -> Generator[Dict[str, str], None, None]:
    """
    Converts the cross product of a number of lists
    From https://stackoverflow.com/a/5228294

    Input:  {foo: [1, 2], bar: ["a", "b"]}
    Output: [
      {foo: 1, bar: "a"},
      {foo: 1, bar: "b"},
      {foo: 2, bar: "a"},
      {foo: 2, bar: "b"}
    ]
    """

    keys = kwargs.keys()
    values = kwargs.values()

    for instance in itertools.product(*values):
        yield dict(zip(keys, instance))


if __name__ == "__main__":
    main()
