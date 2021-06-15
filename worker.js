// Where to proxy the requests to.
const upstreamTarget = "https://example.com/";

async function addRequest(event) {
	/** @var {Cache} cache */
	const cache = caches.default;

    // Check if we already have this in the cache.
	const matched = await cache.match(event.request);

	if (matched) {
	    // Extract the date at which we stored this in the cache.
	    const ageBase = new Date(matched.headers.get("x-date"));

        // Calculate the age
		const age = (new Date()) - ageBase;

		// Update the headers we are returning with a HIT status and the age.
		const headers = new Headers(matched.headers);
		headers.set("age", Math.floor(age / 1000).toString());
		headers.set("cf-cache-status", "HIT");

        // Return the response
		return new Response(
			matched.body,
			{
				status: matched.status,
				statusText: matched.statusText,
				headers: headers
			}
		);
	}

    // Take our query params, and add them to the upstream target
    const url = new URL(event.request.url);
    const upstreamUrl = new URL(upstreamTarget);
	upstreamUrl.search = url.search;

    // Fetch the resources
	const data = await fetch(upstreamUrl);

    // Update the headers.
	const headers = new Headers(data.headers);

	// Age is 0 as we have got this from the origin.
	// We override any proxy age header here to stop confusing the results
	headers.set("age", 0);
	// This was a Cache Miss from the point of view of the Worker test
	headers.set("cf-cache-status", "MISS");
	// This the header we will use to calcuate the age in future requests to the worker
	headers.set("x-date", (new Date()).toString());
	// Remove the CF ID headers to prevent duplication
	headers.delete("cf-request-id");
	headers.delete("cf-ray");

    // Create our new response object
	const response = new Response(
		data.body,
		{
			status: data.status,
			statusText: data.statusText,
			headers: headers
		}
	);

    // Store it in the cache and also return it!
	await cache.put(event.request, response.clone());

	return response;
}

// noinspection JSCheckFunctionSignatures
addEventListener("fetch", event => event.respondWith(addRequest(event)));
