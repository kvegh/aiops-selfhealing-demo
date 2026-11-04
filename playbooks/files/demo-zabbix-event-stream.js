// The deployment validates this endpoint against its selected AAP allocation.
// Credentials are used only in the HTTP header, never event data or logging.
var parameters = JSON.parse(value);
var request = new HttpRequest();
request.addHeader('Authorization: Basic ' + btoa(parameters.username + ':' + parameters.password));
request.addHeader('Content-Type: application/json');
var payload = {
    event_id: parameters.event_id,
    event_name: parameters.event_name,
    event_value: Number(parameters.event_value),
    trigger_id: parameters.trigger_id,
    host_host: parameters.host_host,
    monitoring_source: 'Zabbix'
};
request.post(parameters.endpoint, JSON.stringify(payload));
var status = request.getStatus();
if (status < 200 || status >= 300) {
    throw 'Target event stream rejected delivery with HTTP status ' + status;
}
return 'Delivered to the selected AAP event stream';
