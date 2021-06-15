# CloudFlare Cache Tester

When working with CloudFlare, it became apparent to me that the cache behaviour
did not match the implications in the documentation. This codebase was thrown
together to test the actual behaviours.

### Methodology

The methodology of the test is very simple -- have a request/URL which is
guaranteed to return a known HTTP status code, content type, and cache header,
and then request it every couple of seconds. Observe the value in the `Age`
header over time, and see what the maximum value becomes. This is then taken
to be the effective TTL of the CLoudFlare cache for that combination of status
and headers.

This test framework uses a PHP script on a server to provide the consistent
headers and status (specifically, they are set using query parameters), and
a simple python script which requests each URL and stores the status, headers,
age, and cloudflare request ID metadata in an SQLite database.

For testing the Worker cache, a worker script is provided. This worker uses the
same PHP responder as before to generate status and header data (to ensure
complete consistency), but the Age value is calculated by storing the time the
Worker cached the response as part of that response. 

### Components

| File            | Language    | Description
| --------------- | ----------- | ------------------------------- |
| `responder.php` | PHP 7.4+    | CGI-Style script that sets HTTP response headers based on query params
| `cache_test.py` | Python 3.7+ | Test harness for examining the cache
| `worker.js`     | CF Worker   | Worker to perform the same tests for a worker

### Notes & Gotchas

 - Due to the quick development cycle, and the requirement that the optional 
   `Age` header be a number for the database, all blank headers are stored as
   `0`. This is most notable when using a black `Cache-Control` header.
   Manual data clear up is needed for this
 - The worker can only respond with 'HIT' and 'MISS', and does not include
   the 'BYPASS', 'STALE', or 'EXPIRED' states.

## Results

These results were values as of 2021-06-15.
A number of configurations were run for several hours, totally 168,000 
data points.

### With 'Cache-Origin-Control' On

Global Settings:
- Browser Cache TTL: Respect existing headers
- Always Online: On (but not upgraded to Internet Archive)
  
Page Rule Settings:
- Cache-Origin-Control: On
- Cache-Level: Everything

Not Set:
- Edge Cache TTL

Notes: `stale-while-revalidate` shorten to `swr` for smaller columns.
The more interesting rows have been sorted to the top.

| Cache Header                     | 200      | 201      | 302      | 404      | 503      |
| -------------------------------- | -------- | -------- | -------- | -------- | -------- |
| [Not Set]                        | HIT/2hrs | BYPASS   | BYPASS   | HIT/180s | BYPASS   |
| public                           | HIT/2hrs | BYPASS   | HIT/20m  | HIT/180s | BYPASS   |
| public, max-age=80               | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours |
| private                          | BYPASS   | BYPASS   | BYPASS   | BYPASS   | BYPASS   |
| max-age=333, s-maxage=80         | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| max-age=333, s-maxage=80, swr    | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| max-age=333, s-maxage=80, swr=30 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| public, max-age=333, s-maxage=80 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| public, s-maxage=80              | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| s-maxage=80                      | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| s-maxage=80, swr                 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| s-maxage=80, swr=30              | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |

#### Findings and Conclusion

With `Cache-Origin-Control` on, the cache mostly behaves as on expects.
The exceptions are:
 - 2 hour default TTL for 200s when a `max-age` or `s-maxage` are not specified.
 - A 180s default TTL for 404s when a `max-age` or `s-maxage` are not specified.
 - 20 minute TTL on redirects when `public` is specified, but a `max-age` or 
   `s-maxage` are not specified.
 - When a `max-age`, but not an `s-maxage` is specified, 503s are returned from
   the cache as STALE apparently indefinitely.

### With 'Cache-Origin-Control' Off

Global Settings:
- Browser Cache TTL: Respect existing headers
- Always Online: On (but not upgraded to Internet Archive)
  
Page Rule Settings:
- Cache-Origin-Control: Off
- Cache-Level: Everything

Not Set:
- Edge Cache TTL

Notes: `stale-while-revalidate` shorten to `swr` for smaller columns.
The more interesting rows have been sorted to the top.

| Cache Header                     | 200      | 201      | 302      | 404      | 503      |
| -------------------------------- | -------- | -------- | -------- | -------- | -------- |
| [Not Set]                        | HIT/2hrs | BYPASS   | HIT/20m  | HIT/180s | BYPASS   |
| public                           | HIT/2hrs | BYPASS   | HIT/20m  | HIT/180s | BYPASS   |
| public, max-age=80               | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours |
| private                          | MISS     | MISS     | MISS     | MISS     | MISS     |
| max-age=333, s-maxage=80         | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |
| max-age=333, s-maxage=80, swr    | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |
| max-age=333, s-maxage=80, swr=30 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |
| public, max-age=333, s-maxage=80 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |
| public, s-maxage=80              | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |
| s-maxage=80                      | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |
| s-maxage=80, swr                 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |
| s-maxage=80, swr=30              | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s then STALE/more than 5 hours  |

#### Findings and Conclusion

With `Cache-Origin-Control` on, the cache mostly behaves as on expects except
for with 503 errors. This may be related to the Always-Online setting.

The exceptions are:
 - 2 hour default TTL for 200s when a `max-age` or `s-maxage` are not specified.
 - 180s default TTL for 404s when a `max-age` or `s-maxage` are not specified.
 - 20 minute TTL for 302s when a `max-age` or `s-maxage` are not specified.
 - MISS rather than BYPASS for the `private` cache.

### Via a Worker

This worker was invoked via the worker dev endpoint, and thus did not have
and configurable CloudFlare settings.

Notes: `stale-while-revalidate` shorten to `swr` for smaller columns.
The more interesting rows have been sorted to the top.

| Cache Header                     | 200      | 201      | 302      | 404      | 503      |
| -------------------------------- | -------- | -------- | -------- | -------- | -------- |
| [Not Set]                        | HIT/2hrs | HIT/2hrs | HIT/2hrs | HIT/2hrs | HIT/2hrs |
| public                           | HIT/2hrs | HIT/60s  | HIT/20m  | HIT/180s | HIT/60s  |
| private                          | MISS     | MISS     | MISS     | MISS     | MISS     |
| max-age=333, s-maxage=80         | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| max-age=333, s-maxage=80, swr    | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| max-age=333, s-maxage=80, swr=30 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| public, max-age=80               | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| public, s-maxage=80              | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| public, max-age=333, s-maxage=80 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| s-maxage=80                      | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| s-maxage=80, swr                 | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |
| s-maxage=80, swr=30              | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  | HIT/80s  |

#### Findings and Conclusion

 Worker caches function exact as expected for a shared cache that does not 
 support `stale-while-revliadate`, unless the TTL is not set. At that point,
 the behaviour gets exceptionally weird.
 
 - If no header is set at all, then all resources are cached for 2 hrs
 - If the `public` header is set, then the 2hrs for 200s, 3 minutes 
   for 404s, and 20minutes for 302s as seen in othe parts of the CloudFlare 
   cache are applied. Additionally, a new default TTL of 60s exists for other
   response codes like 201 and 503.
