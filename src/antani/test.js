// test calls

var baseUrl = "http://localhost/antani/";
var resq = null;
function start_long_task() {
    div = $('<div class="progress"><div></div><div>0%</div><div>...</div><div>&nbsp;</div></div><hr>');
    $('#progress').append(div);
    var nanobar = new Nanobar({bg: '#44f',target: div[0].childNodes[0] });
    $.ajax({
        type: 'POST',
	contentType:"application/json; charset=utf-8;",
        url: baseUrl + 'longtask',
        success: function(data, status, request) {
            status_url = request.getResponseHeader('Location');
	    resq = request;
	    console.log(resq);
	    console.log(resq.status);
	    console.log(status_url);
            update_progress(status_url, nanobar, div[0]);
        },
        error: function() {
            console.log('Unexpected error');
        }
    });
}
function update_progress(status_url, nanobar, status_div) {
    // send GET request to status URL
    $.getJSON(status_url, function(data) {
        // update UI
        percent = parseInt(data['current'] * 100 / data['total']);
        nanobar.go(percent);
        $(status_div.childNodes[1]).text(percent + '%');
        $(status_div.childNodes[2]).text(data['status']);
        if (data['state'] != 'PENDING' && data['state'] != 'PROGRESS') {
            if ('result' in data) {
                // show result
                $(status_div.childNodes[3]).text('Result: ' + data['result']);
            }
            else {
                // something unexpected happened
                $(status_div.childNodes[3]).text('Result: ' + data['state']);
            }
        }
        else {
            // rerun in 2 seconds
            setTimeout(function() {
                update_progress(status_url, nanobar, status_div);
            }, 2000);
        }
    });
}
$(function() {
    $('#start-bg-job').click(start_long_task);
});
