// A native Item history widget displays this escaped HTML value.
var summary = JSON.parse(value);
if (!Array.isArray(summary.jobs)) {
    throw new Error('Job summary has no job list');
}
function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, function(character) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character];
    });
}
if (!summary.jobs.length) {
    return '<p style="font-size:22px;padding:12px">No jobs currently running</p>';
}
var colors = {running: '#1565c0', successful: '#229954', failed: '#cc0000',
    error: '#cc0000', canceled: '#70777e', pending: '#a65f00', waiting: '#a65f00', new: '#a65f00'};
var html = '<table style="width:100%;border-collapse:collapse;font-size:15px">' +
    '<thead><tr><th>Job</th><th>Status</th><th>Template</th><th>Started (UTC)</th></tr></thead><tbody>';
summary.jobs.forEach(function(job) {
    var started = job.started ? job.started.slice(11, 19) : 'Queued';
    var color = colors[job.status] || '#444444';
    html += '<tr><td style="padding:7px">' + escapeHtml(job.id) + '</td>' +
        '<td style="padding:7px;color:' + color + ';font-weight:bold">' + escapeHtml(job.status) + '</td>' +
        '<td style="padding:7px">' + escapeHtml(job.name) + '</td>' +
        '<td style="padding:7px">' + escapeHtml(started) + '</td></tr>';
});
html += '</tbody></table>';
if (summary.count > summary.jobs.length) {
    html += '<p>Showing ' + summary.jobs.length + ' of ' + escapeHtml(summary.count) + ' jobs.</p>';
}
return html;
