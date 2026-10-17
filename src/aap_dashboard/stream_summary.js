// Zabbix preprocessing: retain only the presentation metrics.
var stream = JSON.parse(value);
if (typeof stream.events_received !== 'number' || stream.events_received < 0) {
    throw new Error('Event Stream response has no valid received count');
}
return JSON.stringify({
    events_received: stream.events_received,
    last_event_received_at: stream.last_event_received_at || null
});
