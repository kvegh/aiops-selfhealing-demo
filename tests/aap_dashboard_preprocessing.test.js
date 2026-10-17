const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function processValue(script, data) {
    const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'aap_dashboard', script), 'utf8');
    return vm.runInNewContext('(function(value) {' + source + '\n})(input)', {
        input: JSON.stringify(data)
    });
}

const stream = JSON.parse(processValue('stream_summary.js', {
    events_received: 12, last_event_received_at: '2026-01-01T12:00:00Z',
    test_headers: {authorization: 'secret'}, test_content: 'private payload'
}));
assert.deepEqual(Object.keys(stream).sort(), ['events_received', 'last_event_received_at']);
assert.equal(stream.events_received, 12);
assert.throws(() => processValue('stream_summary.js', {events_received: 'invalid'}));

const jobs = JSON.parse(processValue('jobs_summary.js', {
    count: 1, results: [{id: 1, name: '<script>alert("demo")</script>', status: 'running',
        started: '2026-01-01T12:00:00Z', extra_vars: {password: 'secret'}, credentials: [123]}]
}));
assert.equal(jobs.jobs[0].status, 'running');
assert.equal(JSON.stringify(jobs).includes('secret'), false);
assert.equal(Object.hasOwn(jobs.jobs[0], 'extra_vars'), false);
const table = processValue('jobs_table.js', jobs);
assert.equal(table.includes('<script>'), false);
assert.equal(table.includes('&lt;script&gt;'), true);
assert.equal(table.includes('12:00:00'), true);
assert.equal(processValue('jobs_table.js', {count: 0, jobs: []}).includes('No jobs currently running'), true);
assert.throws(() => processValue('jobs_summary.js', {count: 0}));
console.log('AAP dashboard preprocessing: secret minimization, invalid responses, HTML escaping, and empty jobs passed');
