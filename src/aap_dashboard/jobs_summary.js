// Exclude extra variables, credentials, and other unrelated job metadata.
var response = JSON.parse(value);
if (typeof response.count !== 'number' || !Array.isArray(response.results)) {
    throw new Error('Controller response has no valid job list');
}
return JSON.stringify({
    count: response.count,
    jobs: response.results.map(function(job) {
        return {
            id: job.id,
            name: job.name,
            status: job.status,
            started: job.started || null,
            finished: job.finished || null
        };
    })
});
